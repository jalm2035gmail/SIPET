import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand
from django.db.models import Avg, Count
from django.utils import timezone as dj_timezone

from apps.analitica.models import (
    AlertaMonitoreo,
    EjecucionPipeline,
    ReglaAsociacionProducto,
    ResultadoMoraTemprana,
    ResultadoScoring,
    ResultadoSegmentacionSocio,
)
from apps.socios.models import Socio


def _hours_since(dt):
    if not dt:
        return 9999.0
    return max((dj_timezone.now() - dt).total_seconds() / 3600.0, 0.0)


class Command(MAINCommand):
    help = "Monitorea salud tecnica/datos/modelo y emite alertas con severidad y escalamiento."

    def add_arguments(self, parser):
        parser.add_argument("--min-availability", type=float, default=95.0)
        parser.add_argument("--max-error-rate", type=float, default=5.0)
        parser.add_argument("--max-freshness-hours", type=float, default=48.0)
        parser.add_argument("--max-drift-score", type=float, default=0.15)
        parser.add_argument("--report-csv", default="docs/mineria/fase5/05_monitoreo_alertamiento.csv")
        parser.add_argument("--report-md", default="docs/mineria/fase5/05_monitoreo_alertamiento.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        min_availability = float(options["min_availability"])
        max_error_rate = float(options["max_error_rate"])
        max_freshness_hours = float(options["max_freshness_hours"])
        max_drift_score = float(options["max_drift_score"])

        since_24h = dj_timezone.now() - timedelta(hours=24)
        pipelines_24h = EjecucionPipeline.objects.filter(fecha_inicio__gte=since_24h)
        total_runs = pipelines_24h.count()
        ok_runs = pipelines_24h.filter(estado=EjecucionPipeline.ESTADO_OK).count()
        error_runs = total_runs - ok_runs
        availability = 0.0 if total_runs == 0 else (ok_runs / total_runs) * 100.0
        error_rate = 0.0 if total_runs == 0 else (error_runs / total_runs) * 100.0
        avg_duration = float(pipelines_24h.aggregate(v=Avg("duracion_ms"))["v"] or 0.0)

        last_mora = ResultadoMoraTemprana.objects.order_by("-fecha_creacion").values_list("fecha_creacion", flat=True).first()
        last_seg = ResultadoSegmentacionSocio.objects.order_by("-fecha_creacion").values_list("fecha_creacion", flat=True).first()
        last_reglas = ReglaAsociacionProducto.objects.order_by("-fecha_creacion").values_list("fecha_creacion", flat=True).first()
        freshness_mora_h = _hours_since(last_mora)
        freshness_seg_h = _hours_since(last_seg)
        freshness_reglas_h = _hours_since(last_reglas)

        total_socios = Socio.objects.count()
        latest_seg_date = ResultadoSegmentacionSocio.objects.order_by("-fecha_ejecucion").values_list("fecha_ejecucion", flat=True).first()
        segmentados = 0
        if latest_seg_date:
            segmentados = ResultadoSegmentacionSocio.objects.filter(fecha_ejecucion=latest_seg_date).count()
        cobertura_segmentacion = 0.0 if total_socios == 0 else (segmentados / total_socios) * 100.0

        recent_since = dj_timezone.now() - timedelta(days=7)
        recent_avg = float(ResultadoScoring.objects.filter(fecha_creacion__gte=recent_since).aggregate(v=Avg("score"))["v"] or 0.0)
        global_avg = float(ResultadoScoring.objects.aggregate(v=Avg("score"))["v"] or 0.0)
        drift_score = abs(recent_avg - global_avg)

        metrics = [
            ("tecnico", "availability_pct", availability, f">={min_availability}", availability >= min_availability, "equipo_plataforma"),
            ("tecnico", "error_rate_pct", error_rate, f"<={max_error_rate}", error_rate <= max_error_rate, "equipo_plataforma"),
            ("tecnico", "avg_duration_ms", avg_duration, "observacional", True, "equipo_plataforma"),
            ("datos", "freshness_mora_h", freshness_mora_h, f"<={max_freshness_hours}", freshness_mora_h <= max_freshness_hours, "equipo_datos"),
            ("datos", "freshness_segmentacion_h", freshness_seg_h, f"<={max_freshness_hours}", freshness_seg_h <= max_freshness_hours, "equipo_datos"),
            ("datos", "freshness_reglas_h", freshness_reglas_h, f"<={max_freshness_hours}", freshness_reglas_h <= max_freshness_hours, "equipo_datos"),
            ("datos", "cobertura_segmentacion_pct", cobertura_segmentacion, ">=60.0", cobertura_segmentacion >= 60.0, "equipo_comercial"),
            ("modelo", "drift_score_promedio", drift_score, f"<={max_drift_score}", drift_score <= max_drift_score, "equipo_modelo"),
        ]

        alertas_creadas = 0
        rows = []
        for ambito, metrica, valor, umbral, cumple, escalamiento in metrics:
            estado = "cumple" if cumple else "alerta"
            rows.append(
                {
                    "ambito": ambito,
                    "metrica": metrica,
                    "valor": f"{valor:.4f}",
                    "umbral": umbral,
                    "estado": estado,
                    "escalamiento": escalamiento,
                }
            )
            if not cumple:
                severidad = AlertaMonitoreo.SEVERIDAD_WARN
                if metrica in {"availability_pct", "error_rate_pct"}:
                    severidad = AlertaMonitoreo.SEVERIDAD_CRITICAL
                AlertaMonitoreo.objects.create(
                    ambito=ambito,
                    metrica=metrica,
                    valor=valor,
                    umbral=umbral,
                    severidad=severidad,
                    escalamiento=escalamiento,
                    estado=AlertaMonitoreo.ESTADO_ACTIVA,
                    detalle=f"Incumplimiento de umbral en {metrica}",
                )
                alertas_creadas += 1

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["ambito", "metrica", "valor", "umbral", "estado", "escalamiento"])
            writer.writeheader()
            writer.writerows(rows)

        lines = [
            "# Monitoreo y Alertamiento - Punto 5 de 8 (Fase 5)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Salud tecnica (24h)",
            f"- Corridas pipeline: {total_runs}",
            f"- Disponibilidad: {availability:.2f}% (umbral>={min_availability:.2f}%)",
            f"- Error rate: {error_rate:.2f}% (umbral<={max_error_rate:.2f}%)",
            f"- Duracion promedio: {avg_duration:.2f} ms",
            "",
            "## Salud de datos",
            f"- Frescura mora (h): {freshness_mora_h:.2f}",
            f"- Frescura segmentacion (h): {freshness_seg_h:.2f}",
            f"- Frescura reglas (h): {freshness_reglas_h:.2f}",
            f"- Cobertura segmentacion: {cobertura_segmentacion:.2f}%",
            "",
            "## Salud de modelo",
            f"- Drift abs(score promedio): {drift_score:.4f} (umbral<={max_drift_score:.4f})",
            "",
            "## Alertas",
            f"- Alertas nuevas generadas: {alertas_creadas}",
            "- Escalamiento configurado por ambito: plataforma/datos/modelo/comercial.",
            "",
            "## Estado",
            "- Punto 5 de 8 completado tecnicamente.",
            "- Monitoreo tecnico/datos/modelo y alertamiento automatico implementados.",
            "",
            "## Artefactos",
            f"- Reporte CSV: `{report_csv}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[monitorear_alertamiento_fase5] monitoreo completado"))
        self.stdout.write(f"metricas={len(rows)} alertas_nuevas={alertas_creadas}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")

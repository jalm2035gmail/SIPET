import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import Avg
from django.utils import timezone as dj_timezone

from apps.analitica.models import EjecucionPipeline, Prospecto, ResultadoMoraTemprana, ResultadoScoring


def _estado(valor: float, umbral: float, mayor_mejor: bool = True) -> str:
    if mayor_mejor:
        return "Cumple" if valor >= umbral else "En revision"
    return "Cumple" if valor <= umbral else "En revision"


class Command(BaseCommand):
    help = "Monitorea continuamente KPIs tecnicos, de modelo y de negocio para Fase 7."

    def add_arguments(self, parser):
        parser.add_argument("--report-csv", default="docs/mineria/fase7/01_monitoreo_continuo_desempeno.csv")
        parser.add_argument("--report-md", default="docs/mineria/fase7/01_monitoreo_continuo_desempeno.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        now = dj_timezone.now()
        since_24h = now - timedelta(hours=24)
        since_30d = now - timedelta(days=30)
        since_7d = now - timedelta(days=7)

        # KPIs tecnicos (diarios)
        pipelines_24h = EjecucionPipeline.objects.filter(fecha_inicio__gte=since_24h)
        total_runs = pipelines_24h.count()
        ok_runs = pipelines_24h.filter(estado=EjecucionPipeline.ESTADO_OK).count()
        error_runs = total_runs - ok_runs
        availability_pct = 100.0 if total_runs == 0 else (ok_runs / total_runs) * 100.0
        error_rate_pct = 0.0 if total_runs == 0 else (error_runs / total_runs) * 100.0
        avg_duration_ms = float(pipelines_24h.aggregate(v=Avg("duracion_ms"))["v"] or 0.0)

        # KPIs de modelo (periodicos)
        scoring_30d = ResultadoScoring.objects.filter(fecha_creacion__gte=since_30d)
        scoring_7d = ResultadoScoring.objects.filter(fecha_creacion__gte=since_7d)
        total_scoring_30d = scoring_30d.count()
        total_scoring_7d = scoring_7d.count()

        avg_score_30d = float(scoring_30d.aggregate(v=Avg("score"))["v"] or 0.0)
        avg_score_7d = float(scoring_7d.aggregate(v=Avg("score"))["v"] or 0.0)
        drift_score_abs = abs(avg_score_7d - avg_score_30d)

        riesgo_alto_30d = scoring_30d.filter(riesgo=ResultadoScoring.RIESGO_ALTO).count()
        riesgo_alto_pct = 0.0 if total_scoring_30d == 0 else (riesgo_alto_30d / total_scoring_30d) * 100.0

        # KPIs de negocio (periodicos)
        mora_30d = ResultadoMoraTemprana.objects.filter(fecha_creacion__gte=since_30d)
        total_mora_30d = mora_30d.count()
        alertas_altas = mora_30d.filter(alerta=ResultadoMoraTemprana.ALERTA_ALTA).count()
        mora_alta_pct = 0.0 if total_mora_30d == 0 else (alertas_altas / total_mora_30d) * 100.0

        recuperacion_potencial = mora_30d.filter(ratio_pago_90d__gte=0.6).count()
        recuperacion_potencial_pct = 0.0 if total_mora_30d == 0 else (recuperacion_potencial / total_mora_30d) * 100.0

        total_prospectos = Prospecto.objects.count()
        prospectos_alta_propension = Prospecto.objects.filter(score_propension__gte=0.70).count()
        conversion_comercial_potencial_pct = (
            0.0 if total_prospectos == 0 else (prospectos_alta_propension / total_prospectos) * 100.0
        )

        aprobados_30d = scoring_30d.filter(recomendacion="aprobar").count()
        aprobacion_scoring_pct = 0.0 if total_scoring_30d == 0 else (aprobados_30d / total_scoring_30d) * 100.0
        aprobacion_balanceada = 15.0 <= aprobacion_scoring_pct <= 85.0

        rows = [
            {
                "dimension": "tecnico",
                "metrica": "availability_24h_pct",
                "valor": f"{availability_pct:.2f}",
                "umbral": ">=95.00",
                "periodicidad": "diaria",
                "estado": _estado(availability_pct, 95.0, mayor_mejor=True),
            },
            {
                "dimension": "tecnico",
                "metrica": "error_rate_24h_pct",
                "valor": f"{error_rate_pct:.2f}",
                "umbral": "<=5.00",
                "periodicidad": "diaria",
                "estado": _estado(error_rate_pct, 5.0, mayor_mejor=False),
            },
            {
                "dimension": "tecnico",
                "metrica": "duracion_promedio_24h_ms",
                "valor": f"{avg_duration_ms:.2f}",
                "umbral": "observacional",
                "periodicidad": "diaria",
                "estado": "Cumple",
            },
            {
                "dimension": "modelo",
                "metrica": "drift_score_abs_7d_vs_30d",
                "valor": f"{drift_score_abs:.4f}",
                "umbral": "<=0.1500",
                "periodicidad": "semanal",
                "estado": _estado(drift_score_abs, 0.15, mayor_mejor=False),
            },
            {
                "dimension": "modelo",
                "metrica": "riesgo_alto_30d_pct",
                "valor": f"{riesgo_alto_pct:.2f}",
                "umbral": "<=40.00",
                "periodicidad": "semanal",
                "estado": _estado(riesgo_alto_pct, 40.0, mayor_mejor=False),
            },
            {
                "dimension": "negocio",
                "metrica": "mora_alta_30d_pct",
                "valor": f"{mora_alta_pct:.2f}",
                "umbral": "<=35.00",
                "periodicidad": "mensual",
                "estado": _estado(mora_alta_pct, 35.0, mayor_mejor=False),
            },
            {
                "dimension": "negocio",
                "metrica": "recuperacion_potencial_30d_pct",
                "valor": f"{recuperacion_potencial_pct:.2f}",
                "umbral": ">=60.00",
                "periodicidad": "mensual",
                "estado": _estado(recuperacion_potencial_pct, 60.0, mayor_mejor=True),
            },
            {
                "dimension": "negocio",
                "metrica": "conversion_comercial_potencial_pct",
                "valor": f"{conversion_comercial_potencial_pct:.2f}",
                "umbral": ">=20.00",
                "periodicidad": "mensual",
                "estado": _estado(conversion_comercial_potencial_pct, 20.0, mayor_mejor=True),
            },
            {
                "dimension": "negocio",
                "metrica": "aprobacion_scoring_30d_pct",
                "valor": f"{aprobacion_scoring_pct:.2f}",
                "umbral": "15.00-85.00",
                "periodicidad": "mensual",
                "estado": "Cumple" if aprobacion_balanceada else "En revision",
            },
        ]

        cumple = sum(1 for row in rows if row["estado"] == "Cumple")
        total = len(rows)
        estado_global = "Monitoreo operativo" if cumple >= (total - 2) else "Monitoreo con brechas"

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["dimension", "metrica", "valor", "umbral", "periodicidad", "estado"],
            )
            writer.writeheader()
            writer.writerows(rows)

        lines = [
            "# Monitoreo Continuo del Desempeno - Punto 1 de 8 (Fase 7)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Cobertura de monitoreo",
            "- KPIs tecnicos: latencia/duracion, errores y disponibilidad.",
            "- KPIs de modelo: drift y composicion de riesgo.",
            "- KPIs de negocio: mora, recuperacion potencial, conversion comercial y aprobacion.",
            "",
            "## Resumen de ejecucion",
            f"- Registros scoring 7d: {total_scoring_7d}",
            f"- Registros scoring 30d: {total_scoring_30d}",
            f"- Registros mora 30d: {total_mora_30d}",
            f"- Prospectos totales: {total_prospectos}",
            f"- KPIs en cumple: {cumple}/{total}",
            f"- Estado global: {estado_global}",
            "",
            "## Estado",
            "- Punto 1 de 8 completado tecnicamente.",
            "- Monitoreo continuo del desempeno implementado con evidencia reproducible.",
            "",
            "## Artefactos",
            f"- Reporte CSV: `{report_csv}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[monitorear_desempeno_continuo_fase7] monitoreo generado"))
        self.stdout.write(f"kpis_cumple={cumple}/{total} estado_global={estado_global}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")

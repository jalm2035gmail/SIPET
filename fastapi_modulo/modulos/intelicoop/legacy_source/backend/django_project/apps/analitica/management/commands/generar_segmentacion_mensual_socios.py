import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand
from django.db.models import Avg, Count
from django.utils import timezone as dj_timezone

from apps.analitica.models import ResultadoSegmentacionSocio
from apps.creditos.models import Credito
from apps.socios.models import Socio


class Command(MAINCommand):
    help = "Ejecuta segmentacion mensual de socios, publica historico y genera perfiles descriptivos."

    def add_arguments(self, parser):
        parser.add_argument("--fecha-ejecucion", help="Fecha de ejecucion YYYY-MM-DD. Default: hoy.")
        parser.add_argument("--engine", choices=("auto", "orm", "pyspark"), default="auto")
        parser.add_argument("--model-version", default="segmentacion_socios_v1")
        parser.add_argument("--report-csv", default="docs/mineria/fase4/03_segmentacion_socios_perfiles.csv")
        parser.add_argument("--report-md", default="docs/mineria/fase4/03_segmentacion_socios_perfiles.md")

    def handle(self, *args, **options):
        project_root = Path(__file__).resolve().parents[6]
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        from data_pipelines.spark_jobs.segmentacion_socios import ejecutar_segmentacion, extraer_features

        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (project_root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (project_root / report_md_opt)

        fecha_ejecucion = options["fecha_ejecucion"] or str(dj_timezone.localdate())
        model_version = options["model_version"] or "segmentacion_socios_v1"
        engine = options["engine"]

        conteo_segmentos = ejecutar_segmentacion(dry_run=False, engine=engine)
        features = {item.socio_id: item for item in extraer_features()}
        creditos_por_socio = {
            row["socio_id"]: int(row["total"])
            for row in Credito.objects.values("socio_id").annotate(total=Count("id"))
        }
        socios = {item.id: item for item in Socio.objects.all()}

        upserts = 0
        for socio_id, socio in socios.items():
            feat = features.get(socio_id)
            if not feat:
                continue
            defaults = {
                "segmento": socio.segmento,
                "saldo_total": feat.saldo_total,
                "total_movimientos": feat.total_movimientos,
                "cantidad_movimientos": feat.cantidad_movimientos,
                "dias_desde_ultimo_movimiento": feat.dias_desde_ultimo_movimiento,
                "total_creditos": creditos_por_socio.get(socio_id, 0),
            }
            ResultadoSegmentacionSocio.objects.update_or_create(
                socio=socio,
                fecha_ejecucion=fecha_ejecucion,
                model_version=model_version,
                defaults=defaults,
            )
            upserts += 1

        MAIN = ResultadoSegmentacionSocio.objects.filter(
            fecha_ejecucion=fecha_ejecucion,
            model_version=model_version,
        )
        total = MAIN.count()
        perfiles = []
        for segmento in (Socio.SEGMENTO_HORMIGA, Socio.SEGMENTO_GRAN_AHORRADOR, Socio.SEGMENTO_INACTIVO):
            agg = MAIN.filter(segmento=segmento).aggregate(
                socios=Count("id"),
                saldo_promedio=Avg("saldo_total"),
                mov_total_promedio=Avg("total_movimientos"),
                mov_count_promedio=Avg("cantidad_movimientos"),
                dias_promedio=Avg("dias_desde_ultimo_movimiento"),
                creditos_promedio=Avg("total_creditos"),
            )
            perfiles.append(
                {
                    "segmento": segmento,
                    "socios": int(agg["socios"] or 0),
                    "cobertura_pct": 0.0 if total == 0 else (((agg["socios"] or 0) / total) * 100.0),
                    "saldo_promedio": float(agg["saldo_promedio"] or 0),
                    "mov_total_promedio": float(agg["mov_total_promedio"] or 0),
                    "mov_count_promedio": float(agg["mov_count_promedio"] or 0),
                    "dias_promedio": float(agg["dias_promedio"] or 0),
                    "creditos_promedio": float(agg["creditos_promedio"] or 0),
                }
            )

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "fecha_ejecucion",
                    "model_version",
                    "segmento",
                    "socios",
                    "cobertura_pct",
                    "saldo_promedio",
                    "mov_total_promedio",
                    "mov_count_promedio",
                    "dias_promedio",
                    "creditos_promedio",
                ],
            )
            writer.writeheader()
            for row in perfiles:
                writer.writerow(
                    {
                        "fecha_ejecucion": fecha_ejecucion,
                        "model_version": model_version,
                        "segmento": row["segmento"],
                        "socios": row["socios"],
                        "cobertura_pct": f"{row['cobertura_pct']:.2f}",
                        "saldo_promedio": f"{row['saldo_promedio']:.2f}",
                        "mov_total_promedio": f"{row['mov_total_promedio']:.2f}",
                        "mov_count_promedio": f"{row['mov_count_promedio']:.2f}",
                        "dias_promedio": f"{row['dias_promedio']:.2f}",
                        "creditos_promedio": f"{row['creditos_promedio']:.2f}",
                    }
                )

        lines = [
            "# Segmentacion de Socios - Punto 3 de 7 (Fase 4)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            f"Fecha de segmentacion: {fecha_ejecucion}",
            f"Version modelo: {model_version}",
            f"Motor: {engine}",
            "",
            "## Resultado de corrida",
            f"- Socios segmentados: {total}",
            f"- Upserts historicos: {upserts}",
            f"- Conteo hormiga: {conteo_segmentos.get('hormiga', 0)}",
            f"- Conteo gran_ahorrador: {conteo_segmentos.get('gran_ahorrador', 0)}",
            f"- Conteo inactivo: {conteo_segmentos.get('inactivo', 0)}",
            "",
            "## Estado",
            "- Punto 3 de 7 completado tecnicamente.",
            "- Tabla historica de segmentacion publicada por socio y fecha de ejecucion.",
            "",
            "## Artefactos",
            f"- Reporte CSV: `{report_csv}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[generar_segmentacion_mensual_socios] corrida completada"))
        self.stdout.write(f"fecha_ejecucion={fecha_ejecucion} model_version={model_version} engine={engine}")
        self.stdout.write(f"segmentados={total} upserts={upserts}")
        self.stdout.write(
            f"conteo=hormiga:{conteo_segmentos.get('hormiga', 0)},"
            f"gran_ahorrador:{conteo_segmentos.get('gran_ahorrador', 0)},"
            f"inactivo:{conteo_segmentos.get('inactivo', 0)}"
        )
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")

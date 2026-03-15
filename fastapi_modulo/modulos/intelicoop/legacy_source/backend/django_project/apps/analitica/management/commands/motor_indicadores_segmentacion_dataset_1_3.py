import csv
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand
from django.db.models import Avg, Count, Sum
from django.utils import timezone as dj_timezone

from apps.ahorros.models import Cuenta
from apps.analitica.models import ResultadoMoraTemprana, ResultadoScoring, ResultadoSegmentacionSocio
from apps.creditos.models import Credito
from apps.socios.models import Socio


class Command(MAINCommand):
    help = "Elemento 4/4 de 1.3: segmentacion de socios y dataset listo para decisiones."

    def add_arguments(self, parser):
        parser.add_argument("--report-csv", default="docs/mineria/engine/04_indicadores_segmentacion_socios.csv")
        parser.add_argument("--dataset-csv", default="docs/mineria/engine/04_dataset_decisiones_socios.csv")
        parser.add_argument("--report-md", default="docs/mineria/engine/04_indicadores_segmentacion_socios.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        dataset_csv_opt = Path(options["dataset_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        dataset_csv = dataset_csv_opt if dataset_csv_opt.is_absolute() else (root / dataset_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        fecha_corte = dj_timezone.localdate()

        segmentos_MAIN = (
            ResultadoSegmentacionSocio.objects.filter(fecha_ejecucion=fecha_corte)
            .values("segmento")
            .annotate(total=Count("id"))
        )
        total_segmentados = sum(int(row["total"]) for row in segmentos_MAIN)
        if total_segmentados == 0:
            segmentos_MAIN = Socio.objects.values("segmento").annotate(total=Count("id"))
            total_segmentados = sum(int(row["total"]) for row in segmentos_MAIN)

        cobertura_segmentacion_pct = (
            0.0 if Socio.objects.count() == 0 else float((total_segmentados / Socio.objects.count()) * 100.0)
        )
        segmentos_activos = sum(1 for row in segmentos_MAIN if int(row["total"]) > 0)
        segmento_dominante_pct = (
            0.0
            if total_segmentados == 0
            else float((max(int(row["total"]) for row in segmentos_MAIN) / total_segmentados) * 100.0)
        )
        socio_objetivo = (
            ResultadoSegmentacionSocio.objects.filter(fecha_ejecucion=fecha_corte, segmento=Socio.SEGMENTO_HORMIGA).count()
            + ResultadoSegmentacionSocio.objects.filter(
                fecha_ejecucion=fecha_corte, segmento=Socio.SEGMENTO_GRAN_AHORRADOR
            ).count()
        )
        if total_segmentados > 0:
            socios_objetivo_pct = float((socio_objetivo / total_segmentados) * 100.0)
        else:
            socio_objetivo = Socio.objects.filter(
                segmento__in=[Socio.SEGMENTO_HORMIGA, Socio.SEGMENTO_GRAN_AHORRADOR]
            ).count()
            socios_objetivo_pct = 0.0 if Socio.objects.count() == 0 else float((socio_objetivo / Socio.objects.count()) * 100.0)

        kpis = [
            {
                "kpi": "cobertura_segmentacion_pct",
                "valor": f"{cobertura_segmentacion_pct:.2f}",
                "formula": "socios_segmentados / socios_totales * 100",
                "estado": "Cumple" if cobertura_segmentacion_pct >= 70.0 else "En revision",
            },
            {
                "kpi": "segmentos_activos",
                "valor": str(segmentos_activos),
                "formula": "conteo_segmentos_con_socios",
                "estado": "Cumple" if segmentos_activos >= 2 else "En revision",
            },
            {
                "kpi": "segmento_dominante_pct",
                "valor": f"{segmento_dominante_pct:.2f}",
                "formula": "max(socios_segmento) / socios_segmentados * 100",
                "estado": "Cumple" if segmento_dominante_pct <= 80.0 else "En revision",
            },
            {
                "kpi": "socios_objetivo_pct",
                "valor": f"{socios_objetivo_pct:.2f}",
                "formula": "(socios_hormiga + socios_gran_ahorrador) / socios_MAIN * 100",
                "estado": "Cumple" if socios_objetivo_pct >= 40.0 else "En revision",
            },
        ]

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["kpi", "valor", "formula", "estado"])
            writer.writeheader()
            writer.writerows(kpis)

        saldos_por_socio = {
            row["socio_id"]: float(row["saldo_total"] or 0.0)
            for row in Cuenta.objects.values("socio_id").annotate(saldo_total=Sum("saldo"))
        }
        creditos_por_socio = {
            row["socio_id"]: int(row["total"] or 0)
            for row in Credito.objects.values("socio_id").annotate(total=Count("id"))
        }
        deuda_por_socio = {
            row["socio_id"]: float(row["deuda_total"] or 0.0)
            for row in Credito.objects.values("socio_id").annotate(deuda_total=Sum("deuda_actual"))
        }
        mora_por_socio = {
            row["socio_id"]: float(row["promedio"] or 0.0)
            for row in ResultadoMoraTemprana.objects.values("socio_id").annotate(promedio=Avg("prob_mora_90d"))
        }
        score_por_socio = {
            row["socio_id"]: float(row["promedio"] or 0.0)
            for row in ResultadoScoring.objects.values("socio_id").annotate(promedio=Avg("score"))
        }
        segmento_actual_por_socio = {}
        for row in ResultadoSegmentacionSocio.objects.filter(fecha_ejecucion=fecha_corte).select_related("socio"):
            segmento_actual_por_socio[row.socio_id] = row.segmento

        rows_dataset = []
        for socio in Socio.objects.all().order_by("id"):
            segmento = segmento_actual_por_socio.get(socio.id, socio.segmento)
            saldo_total = saldos_por_socio.get(socio.id, 0.0)
            deuda_total = deuda_por_socio.get(socio.id, 0.0)
            score_promedio = score_por_socio.get(socio.id, 0.0)
            prob_mora_90d_prom = mora_por_socio.get(socio.id, 0.0)
            relacion_ahorro_deuda = 0.0 if deuda_total <= 0 else (saldo_total / deuda_total)
            if prob_mora_90d_prom >= 0.60:
                accion = "alerta_cobranza"
            elif score_promedio >= 0.70 and relacion_ahorro_deuda >= 0.80:
                accion = "preaprobacion_credito"
            elif segmento in [Socio.SEGMENTO_HORMIGA, Socio.SEGMENTO_GRAN_AHORRADOR]:
                accion = "campania_cross_sell"
            else:
                accion = "seguimiento_regular"
            rows_dataset.append(
                {
                    "fecha_corte": fecha_corte.isoformat(),
                    "socio_id": socio.id,
                    "segmento": segmento,
                    "saldo_total": f"{saldo_total:.2f}",
                    "deuda_total": f"{deuda_total:.2f}",
                    "total_creditos": creditos_por_socio.get(socio.id, 0),
                    "score_promedio": f"{score_promedio:.4f}",
                    "prob_mora_90d_promedio": f"{prob_mora_90d_prom:.4f}",
                    "relacion_ahorro_deuda": f"{relacion_ahorro_deuda:.4f}",
                    "accion_sugerida": accion,
                }
            )

        dataset_csv.parent.mkdir(parents=True, exist_ok=True)
        with dataset_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "fecha_corte",
                    "socio_id",
                    "segmento",
                    "saldo_total",
                    "deuda_total",
                    "total_creditos",
                    "score_promedio",
                    "prob_mora_90d_promedio",
                    "relacion_ahorro_deuda",
                    "accion_sugerida",
                ],
            )
            writer.writeheader()
            writer.writerows(rows_dataset)

        cumple = sum(1 for row in kpis if row["estado"] == "Cumple")
        total = len(kpis)
        lines = [
            "# Motor de Indicadores 1.3 - Elemento 4 de 4 (Segmentacion y Dataset de Decision)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            f"Fecha de corte: {fecha_corte.isoformat()}",
            "",
            "## MAIN de calculo",
            f"- Socios totales: {Socio.objects.count()}",
            f"- Socios segmentados: {total_segmentados}",
            f"- Segmentos activos: {segmentos_activos}",
            f"- Registros dataset decision: {len(rows_dataset)}",
            "",
            "## Estado",
            "- Elemento 4 de 4 completado tecnicamente.",
            "- Segmentacion por perfil/comportamiento y acciones sugeridas publicadas.",
            "- Dataset listo para decisiones generado.",
            f"- KPIs en cumple: {cumple}/{total}",
            "",
            "## Artefactos",
            f"- KPI segmentacion: `{report_csv}`",
            f"- Dataset listo para decisiones: `{dataset_csv}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[motor_indicadores_segmentacion_dataset_1_3] indicadores generados"))
        self.stdout.write(f"kpis_cumple={cumple}/{total}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"dataset_csv={dataset_csv}")
        self.stdout.write(f"report_md={report_md}")

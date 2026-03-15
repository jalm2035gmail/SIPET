import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand
from django.db.models import Sum
from django.utils import timezone as dj_timezone

from apps.analitica.models import ResultadoMoraTemprana
from apps.creditos.models import Credito, HistorialPago


class Command(MAINCommand):
    help = "Elemento 1/4 de 1.3: calcula indicadores de mora y riesgo (IMOR, mora temprana, mora maxima y cobertura)."

    def add_arguments(self, parser):
        parser.add_argument("--report-csv", default="docs/mineria/engine/01_indicadores_mora_riesgo.csv")
        parser.add_argument("--report-md", default="docs/mineria/engine/01_indicadores_mora_riesgo.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        cartera_total = float(Credito.objects.aggregate(v=Sum("monto"))["v"] or 0.0)

        mora_qs = ResultadoMoraTemprana.objects.select_related("credito")
        total_alertas = mora_qs.count()
        alertas_media_alta = mora_qs.filter(alerta__in=[ResultadoMoraTemprana.ALERTA_MEDIA, ResultadoMoraTemprana.ALERTA_ALTA]).count()
        mora_temprana_pct = 0.0 if total_alertas == 0 else (alertas_media_alta / total_alertas) * 100.0

        mora_max_historica_pct = float((mora_qs.aggregate(v=Sum("prob_mora_90d"))["v"] or 0.0))
        if total_alertas > 0:
            mora_max_historica_pct = float(mora_qs.order_by("-prob_mora_90d").values_list("prob_mora_90d", flat=True).first() or 0.0) * 100.0
        else:
            mora_max_historica_pct = 0.0

        creditos_riesgo_alto = []
        for row in mora_qs.filter(alerta=ResultadoMoraTemprana.ALERTA_ALTA):
            if row.credito_id and row.credito:
                creditos_riesgo_alto.append(float(row.credito.deuda_actual or 0.0))
        cartera_vencida_estimada = sum(creditos_riesgo_alto)
        imor_pct = 0.0 if cartera_total <= 0 else (cartera_vencida_estimada / cartera_total) * 100.0

        pagos_90d = float(
            HistorialPago.objects.filter(fecha__gte=(dj_timezone.localdate() - timedelta(days=90))).aggregate(v=Sum("monto"))["v"]
            or 0.0
        )
        cobertura_pct = 0.0 if cartera_vencida_estimada <= 0 else (pagos_90d / cartera_vencida_estimada) * 100.0

        dataset = [
            {
                "kpi": "imor_pct",
                "valor": f"{imor_pct:.2f}",
                "formula": "cartera_vencida_estimada / cartera_total * 100",
                "estado": "Cumple" if imor_pct <= 15.0 else "En revision",
            },
            {
                "kpi": "mora_temprana_pct",
                "valor": f"{mora_temprana_pct:.2f}",
                "formula": "alertas_media_alta / total_alertas * 100",
                "estado": "Cumple" if mora_temprana_pct <= 60.0 else "En revision",
            },
            {
                "kpi": "mora_max_historica_pct",
                "valor": f"{mora_max_historica_pct:.2f}",
                "formula": "max(prob_mora_90d) * 100",
                "estado": "Cumple" if mora_max_historica_pct <= 95.0 else "En revision",
            },
            {
                "kpi": "cobertura_pct",
                "valor": f"{cobertura_pct:.2f}",
                "formula": "pagos_90d / cartera_vencida_estimada * 100",
                "estado": "Cumple" if cobertura_pct >= 50.0 else "En revision",
            },
        ]

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["kpi", "valor", "formula", "estado"])
            writer.writeheader()
            writer.writerows(dataset)

        cumple = sum(1 for row in dataset if row["estado"] == "Cumple")
        total = len(dataset)
        lines = [
            "# Motor de Indicadores 1.3 - Elemento 1 de 4 (Mora y Riesgo)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## MAIN de calculo",
            f"- Cartera total: {cartera_total:.2f}",
            f"- Cartera vencida estimada: {cartera_vencida_estimada:.2f}",
            f"- Pagos ultimos 90 dias: {pagos_90d:.2f}",
            f"- Alertas de mora: {total_alertas}",
            "",
            "## Estado",
            "- Elemento 1 de 4 completado tecnicamente.",
            "- KPIs de mora y riesgo calculados automaticamente.",
            f"- KPIs en cumple: {cumple}/{total}",
            "",
            "## Artefactos",
            f"- Dataset KPI listo para decisiones: `{report_csv}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[motor_indicadores_mora_riesgo_1_3] indicadores generados"))
        self.stdout.write(f"kpis_cumple={cumple}/{total}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")

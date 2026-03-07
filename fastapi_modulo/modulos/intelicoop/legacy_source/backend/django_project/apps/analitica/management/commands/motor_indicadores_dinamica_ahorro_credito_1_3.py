import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import pstdev

from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone as dj_timezone

from apps.ahorros.models import Cuenta
from apps.creditos.models import Credito


class Command(BaseCommand):
    help = "Elemento 2/4 de 1.3: calcula indicadores de dinamica de creditos y ahorro."

    def add_arguments(self, parser):
        parser.add_argument("--report-csv", default="docs/mineria/engine/02_indicadores_dinamica_ahorro_credito.csv")
        parser.add_argument("--report-md", default="docs/mineria/engine/02_indicadores_dinamica_ahorro_credito.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        hoy = dj_timezone.localdate()
        ventana_180d = hoy - timedelta(days=180)

        creditos_qs = Credito.objects.all()
        cartera_total = float(creditos_qs.aggregate(v=Sum("monto"))["v"] or 0.0)

        socios_con_credito = set(creditos_qs.values_list("socio_id", flat=True))
        total_socios_con_credito = len(socios_con_credito)
        total_creditos_180d = creditos_qs.filter(fecha_creacion__date__gte=ventana_180d).count()
        rotacion_creditos = (
            0.0 if total_socios_con_credito == 0 else float(total_creditos_180d / total_socios_con_credito)
        )

        socios_con_renovacion = 0
        for socio_id in socios_con_credito:
            if creditos_qs.filter(socio_id=socio_id).count() >= 2:
                socios_con_renovacion += 1
        frecuencia_renovacion_pct = (
            0.0
            if total_socios_con_credito == 0
            else float((socios_con_renovacion / total_socios_con_credito) * 100.0)
        )

        ahorro_total = float(Cuenta.objects.aggregate(v=Sum("saldo"))["v"] or 0.0)
        relacion_ahorro_credito_pct = 0.0 if cartera_total <= 0 else float((ahorro_total / cartera_total) * 100.0)

        saldos = [float(v) for v in Cuenta.objects.values_list("saldo", flat=True)]
        if not saldos:
            estabilidad_ahorro_pct = 0.0
            coef_variacion = 0.0
        else:
            media = sum(saldos) / len(saldos)
            if media <= 0:
                coef_variacion = 1.0
                estabilidad_ahorro_pct = 0.0
            else:
                desviacion = pstdev(saldos)
                coef_variacion = desviacion / media
                estabilidad_ahorro_pct = max(0.0, min(100.0, (1.0 - coef_variacion) * 100.0))

        dataset = [
            {
                "kpi": "rotacion_creditos_180d",
                "valor": f"{rotacion_creditos:.2f}",
                "formula": "creditos_ult_180d / socios_con_credito",
                "estado": "Cumple" if rotacion_creditos >= 0.30 else "En revision",
            },
            {
                "kpi": "frecuencia_renovacion_pct",
                "valor": f"{frecuencia_renovacion_pct:.2f}",
                "formula": "socios_con_2omas_creditos / socios_con_credito * 100",
                "estado": "Cumple" if frecuencia_renovacion_pct >= 20.0 else "En revision",
            },
            {
                "kpi": "relacion_ahorro_credito_pct",
                "valor": f"{relacion_ahorro_credito_pct:.2f}",
                "formula": "ahorro_total / cartera_total * 100",
                "estado": "Cumple" if relacion_ahorro_credito_pct >= 15.0 else "En revision",
            },
            {
                "kpi": "estabilidad_ahorro_pct",
                "valor": f"{estabilidad_ahorro_pct:.2f}",
                "formula": "(1 - coef_variacion_saldos) * 100",
                "estado": "Cumple" if estabilidad_ahorro_pct >= 50.0 else "En revision",
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
            "# Motor de Indicadores 1.3 - Elemento 2 de 4 (Dinamica Ahorro-Credito)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Base de calculo",
            f"- Fecha de corte: {hoy.isoformat()}",
            f"- Cartera total: {cartera_total:.2f}",
            f"- Ahorro total: {ahorro_total:.2f}",
            f"- Socios con credito: {total_socios_con_credito}",
            f"- Coeficiente variacion saldos: {coef_variacion:.4f}",
            "",
            "## Estado",
            "- Elemento 2 de 4 completado tecnicamente.",
            "- KPIs de rotacion, renovacion, relacion ahorro-credito y estabilidad calculados automaticamente.",
            f"- KPIs en cumple: {cumple}/{total}",
            "",
            "## Artefactos",
            f"- Dataset KPI listo para decisiones: `{report_csv}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[motor_indicadores_dinamica_ahorro_credito_1_3] indicadores generados"))
        self.stdout.write(f"kpis_cumple={cumple}/{total}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")

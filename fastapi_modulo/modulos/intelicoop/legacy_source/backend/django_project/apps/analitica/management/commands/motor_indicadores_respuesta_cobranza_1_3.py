import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone as dj_timezone

from apps.analitica.models import ResultadoMoraTemprana, ResultadoScoring
from apps.creditos.models import HistorialPago


class Command(BaseCommand):
    help = "Elemento 3/4 de 1.3: calcula tiempo de respuesta de credito y eficiencia de cobranza."

    def add_arguments(self, parser):
        parser.add_argument("--report-csv", default="docs/mineria/engine/03_indicadores_respuesta_cobranza.csv")
        parser.add_argument("--report-md", default="docs/mineria/engine/03_indicadores_respuesta_cobranza.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        hoy = dj_timezone.localdate()
        ventana_90d = hoy - timedelta(days=90)

        # Proxy de tiempo de respuesta: diferencia entre creacion de credito y primer scoring ligado al credito.
        scores = ResultadoScoring.objects.select_related("credito").filter(credito__isnull=False)
        diffs_horas = []
        for score in scores:
            credito = score.credito
            if not credito or not credito.fecha_creacion or not score.fecha_creacion:
                continue
            delta_horas = (score.fecha_creacion - credito.fecha_creacion).total_seconds() / 3600.0
            if delta_horas >= 0:
                diffs_horas.append(delta_horas)
        tiempo_respuesta_horas = 0.0 if not diffs_horas else (sum(diffs_horas) / len(diffs_horas))

        gestiones_qs = ResultadoMoraTemprana.objects.filter(alerta__in=[ResultadoMoraTemprana.ALERTA_MEDIA, ResultadoMoraTemprana.ALERTA_ALTA])
        gestiones_total = gestiones_qs.count()
        gestiones_recuperacion = gestiones_qs.filter(ratio_pago_90d__gte=0.60).count()
        eficiencia_cobranza_pct = 0.0 if gestiones_total == 0 else (gestiones_recuperacion / gestiones_total) * 100.0

        pagos_90d = float(HistorialPago.objects.filter(fecha__gte=ventana_90d).aggregate(v=Sum("monto"))["v"] or 0.0)
        recuperacion_por_gestion = 0.0 if gestiones_total == 0 else (pagos_90d / gestiones_total)

        alertas_altas = gestiones_qs.filter(alerta=ResultadoMoraTemprana.ALERTA_ALTA).count()
        prioridad_alta_pct = 0.0 if gestiones_total == 0 else (alertas_altas / gestiones_total) * 100.0

        dataset = [
            {
                "kpi": "tiempo_respuesta_credito_horas",
                "valor": f"{tiempo_respuesta_horas:.2f}",
                "formula": "avg(fecha_scoring - fecha_creacion_credito) en horas",
                "estado": "Cumple" if tiempo_respuesta_horas <= 48.0 else "En revision",
            },
            {
                "kpi": "eficiencia_cobranza_pct",
                "valor": f"{eficiencia_cobranza_pct:.2f}",
                "formula": "gestiones_con_ratio_pago_90d>=0.60 / gestiones_total * 100",
                "estado": "Cumple" if eficiencia_cobranza_pct >= 45.0 else "En revision",
            },
            {
                "kpi": "recuperacion_por_gestion",
                "valor": f"{recuperacion_por_gestion:.2f}",
                "formula": "pagos_ult_90d / gestiones_total",
                "estado": "Cumple" if recuperacion_por_gestion >= 100.0 else "En revision",
            },
            {
                "kpi": "prioridad_alerta_alta_pct",
                "valor": f"{prioridad_alta_pct:.2f}",
                "formula": "alertas_alta / gestiones_total * 100",
                "estado": "Cumple" if prioridad_alta_pct <= 70.0 else "En revision",
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
            "# Motor de Indicadores 1.3 - Elemento 3 de 4 (Respuesta y Cobranza)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Base de calculo",
            f"- Fecha de corte: {hoy.isoformat()}",
            f"- Gestiones consideradas: {gestiones_total}",
            f"- Gestiones con recuperacion: {gestiones_recuperacion}",
            f"- Pagos ultimos 90 dias: {pagos_90d:.2f}",
            f"- Casos con tiempo de respuesta medible: {len(diffs_horas)}",
            "",
            "## Estado",
            "- Elemento 3 de 4 completado tecnicamente.",
            "- KPIs de tiempo de respuesta y eficiencia de cobranza calculados automaticamente.",
            f"- KPIs en cumple: {cumple}/{total}",
            "",
            "## Artefactos",
            f"- Dataset KPI listo para decisiones: `{report_csv}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[motor_indicadores_respuesta_cobranza_1_3] indicadores generados"))
        self.stdout.write(f"kpis_cumple={cumple}/{total}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")

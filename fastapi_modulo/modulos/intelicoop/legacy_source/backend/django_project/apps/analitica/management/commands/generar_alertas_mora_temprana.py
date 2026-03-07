import csv
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone as dj_timezone

from apps.analitica.models import ResultadoMoraTemprana
from apps.analitica.views import _calcular_probabilidades_mora
from apps.creditos.models import Credito


class Command(BaseCommand):
    help = "Genera alertas batch de mora temprana (30/60/90) y publica resultados historicos."

    def add_arguments(self, parser):
        parser.add_argument("--fecha-corte", help="Fecha de corte YYYY-MM-DD. Default: hoy.")
        parser.add_argument("--limit", type=int, default=0, help="Limite de creditos a procesar (0 = todos).")
        parser.add_argument("--model-version", default="mora_temprana_v1")
        parser.add_argument("--report-csv", default="docs/mineria/fase4/02_mora_temprana_alertas.csv")
        parser.add_argument("--report-md", default="docs/mineria/fase4/02_mora_temprana_alertas.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        fecha_corte_raw = options["fecha_corte"] or str(dj_timezone.localdate())
        fecha_corte = date.fromisoformat(fecha_corte_raw)
        model_version = options["model_version"] or "mora_temprana_v1"
        limit = int(options["limit"])

        queryset = Credito.objects.select_related("socio").all().order_by("id")
        if limit > 0:
            queryset = queryset[:limit]

        processed = 0
        created_count = 0
        alertas = Counter()
        rows = []

        for credito in queryset:
            if not credito.socio_id:
                continue
            metrics = _calcular_probabilidades_mora(credito, fecha_corte=fecha_corte)
            resultado, created = ResultadoMoraTemprana.objects.update_or_create(
                credito=credito,
                socio=credito.socio,
                fecha_corte=fecha_corte,
                model_version=model_version,
                fuente=ResultadoMoraTemprana.FUENTE_BATCH,
                defaults={
                    "cuota_estimada": metrics["cuota_estimada"],
                    "pagos_90d": metrics["pagos_90d"],
                    "ratio_pago_90d": metrics["ratio_pago_90d"],
                    "deuda_ingreso_ratio": metrics["deuda_ingreso_ratio"],
                    "prob_mora_30d": metrics["prob_mora_30d"],
                    "prob_mora_60d": metrics["prob_mora_60d"],
                    "prob_mora_90d": metrics["prob_mora_90d"],
                    "alerta": metrics["alerta"],
                },
            )
            processed += 1
            if created:
                created_count += 1
            alertas[resultado.alerta] += 1
            rows.append(
                {
                    "credito_id": credito.id,
                    "socio_id": credito.socio_id,
                    "fecha_corte": fecha_corte.isoformat(),
                    "prob_mora_30d": f"{float(metrics['prob_mora_30d']):.4f}",
                    "prob_mora_60d": f"{float(metrics['prob_mora_60d']):.4f}",
                    "prob_mora_90d": f"{float(metrics['prob_mora_90d']):.4f}",
                    "alerta": metrics["alerta"],
                    "model_version": model_version,
                    "fuente": ResultadoMoraTemprana.FUENTE_BATCH,
                }
            )

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "credito_id",
                    "socio_id",
                    "fecha_corte",
                    "prob_mora_30d",
                    "prob_mora_60d",
                    "prob_mora_90d",
                    "alerta",
                    "model_version",
                    "fuente",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

        lines = [
            "# Mora Temprana - Punto 2 de 7 (Fase 4)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            f"Fecha de corte: {fecha_corte.isoformat()}",
            f"Version modelo: {model_version}",
            "",
            "## Resultado de corrida batch",
            f"- Creditos procesados: {processed}",
            f"- Registros creados nuevos: {created_count}",
            f"- Alerta baja: {alertas.get('baja', 0)}",
            f"- Alerta media: {alertas.get('media', 0)}",
            f"- Alerta alta: {alertas.get('alta', 0)}",
            "",
            "## Estado",
            "- Punto 2 de 7 completado tecnicamente.",
            "- Alertas 30/60/90 publicadas en tabla historica `resultados_mora_temprana`.",
            "",
            "## Artefactos",
            f"- Reporte CSV: `{report_csv}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[generar_alertas_mora_temprana] corrida completada"))
        self.stdout.write(f"processed={processed} created={created_count}")
        self.stdout.write(
            f"alertas=baja:{alertas.get('baja', 0)},media:{alertas.get('media', 0)},alta:{alertas.get('alta', 0)}"
        )
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")

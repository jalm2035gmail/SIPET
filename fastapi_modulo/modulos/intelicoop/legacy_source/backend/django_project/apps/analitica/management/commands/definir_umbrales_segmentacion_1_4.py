import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand


DEFAULT_THRESHOLDS = {
    "listos_para_credito": {
        "min_score_promedio": 0.75,
        "max_prob_mora_90d": 0.30,
        "max_variabilidad_ahorro": 0.50,
        "min_ahorro_total": 300.0,
    },
    "renovacion_segura": {
        "min_total_creditos": 1,
        "min_pagos_180d": 1.0,
        "max_prob_mora_90d": 0.30,
    },
    "riesgo_alto": {
        "min_prob_mora_90d": 0.60,
        "min_alertas_altas": 1,
        "min_variabilidad_ahorro": 0.80,
    },
    "potencial_captacion": {
        "min_ahorro_total": 1000.0,
        "max_total_creditos": 0,
    },
    "jovenes_digitales": {
        "min_transacciones_180d": 6,
        "max_monto_promedio_transaccion": 250.0,
        "max_total_creditos": 1,
    },
}


class Command(BaseCommand):
    help = "Define y versiona umbrales oficiales de segmentacion inteligente 1.4."

    def add_arguments(self, parser):
        parser.add_argument("--thresholds-version", default="segmentacion_1_4_v1")
        parser.add_argument("--aprobado-por", default="comite_negocio")
        parser.add_argument(
            "--thresholds-json",
            default="docs/mineria/customer_intelligence/02_umbrales_segmentacion_oficial_v1.json",
        )
        parser.add_argument(
            "--report-csv",
            default="docs/mineria/customer_intelligence/02_umbrales_segmentacion_oficial.csv",
        )
        parser.add_argument(
            "--report-md",
            default="docs/mineria/customer_intelligence/02_umbrales_segmentacion_oficial.md",
        )

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        thresholds_json_opt = Path(options["thresholds_json"])
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        thresholds_json = thresholds_json_opt if thresholds_json_opt.is_absolute() else (root / thresholds_json_opt)
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        version = str(options["thresholds_version"] or "segmentacion_1_4_v1")
        aprobado_por = str(options["aprobado_por"] or "comite_negocio")
        payload = {
            "version": version,
            "approved_by": aprobado_por,
            "approved_at_utc": datetime.now(timezone.utc).isoformat(),
            "thresholds": DEFAULT_THRESHOLDS,
        }

        thresholds_json.parent.mkdir(parents=True, exist_ok=True)
        thresholds_json.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

        rows = []
        for segmento, values in DEFAULT_THRESHOLDS.items():
            for regla, valor in values.items():
                rows.append(
                    {
                        "version": version,
                        "segmento": segmento,
                        "regla": regla,
                        "valor": valor,
                        "aprobado_por": aprobado_por,
                    }
                )

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["version", "segmento", "regla", "valor", "aprobado_por"])
            writer.writeheader()
            writer.writerows(rows)

        lines = [
            "# Umbrales Oficiales Segmentacion 1.4 - Punto 2 de 3",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            f"Version umbrales: {version}",
            f"Aprobado por: {aprobado_por}",
            "",
            "## Estado",
            "- Punto 2 de 3 completado tecnicamente.",
            "- Umbrales oficiales de segmentacion versionados y trazables.",
            "",
            "## Artefactos",
            f"- Configuracion JSON: `{thresholds_json}`",
            f"- Matriz de reglas: `{report_csv}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[definir_umbrales_segmentacion_1_4] umbrales versionados"))
        self.stdout.write(f"version={version}")
        self.stdout.write(f"thresholds_json={thresholds_json}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")

import csv
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Disena arquitectura de ejecucion de Fase 5 (real-time vs batch) y define dependencias operativas."

    def add_arguments(self, parser):
        parser.add_argument("--report-csv", default="docs/mineria/fase5/01_arquitectura_ejecucion.csv")
        parser.add_argument("--report-md", default="docs/mineria/fase5/01_arquitectura_ejecucion.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        rows = [
            {
                "flujo": "scoring_originacion",
                "tipo_ejecucion": "tiempo_real",
                "ventana": "on-demand",
                "dependencias": "auth -> validacion -> fastapi_scoring -> persistencia_scoring",
                "salida": "resultado_scoring + recomendacion",
            },
            {
                "flujo": "mora_temprana",
                "tipo_ejecucion": "batch",
                "ventana": "diario_02:15",
                "dependencias": "creditos + historial_pagos -> features_mora -> alertas_30_60_90 -> publicacion",
                "salida": "resultados_mora_temprana",
            },
            {
                "flujo": "segmentacion_socios",
                "tipo_ejecucion": "batch",
                "ventana": "mensual_dia_1_02:30",
                "dependencias": "socios + cuentas + transacciones -> features_segmentacion -> segmentacion -> perfiles",
                "salida": "resultados_segmentacion_socios + perfiles",
            },
            {
                "flujo": "reglas_asociacion",
                "tipo_ejecucion": "batch",
                "ventana": "semanal_domingo_03:00",
                "dependencias": "cestas_productos -> reglas_apriori -> filtro_soporte_confianza_lift -> publicacion",
                "salida": "reglas_asociacion_productos",
            },
            {
                "flujo": "integracion_validacion",
                "tipo_ejecucion": "batch",
                "ventana": "diario_04:00",
                "dependencias": "resultados_submodulos -> resumen_integracion -> validacion_funcional_tecnica",
                "salida": "reportes_05_06_fase4",
            },
        ]

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["flujo", "tipo_ejecucion", "ventana", "dependencias", "salida"],
            )
            writer.writeheader()
            writer.writerows(rows)

        lines = [
            "# Arquitectura de Ejecucion - Punto 1 de 8 (Fase 5)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Definicion real-time vs batch",
            "- Tiempo real: scoring en originacion de credito.",
            "- Batch: mora temprana, segmentacion, reglas de asociacion e integracion de validaciones.",
            "",
            "## Cadena de dependencias",
            "- Carga de datos -> feature engineering -> ejecucion de modelo -> publicacion de resultados.",
            "- Ventanas recomendadas sin colision: 02:15 mora, 02:30 segmentacion (mensual), 03:00 reglas (semanal), 04:00 integracion/validacion.",
            "",
            "## Estado",
            "- Punto 1 de 8 completado tecnicamente.",
            "- Arquitectura base de ejecucion definida para orquestacion en Fase 5.",
            "",
            "## Artefactos",
            f"- Reporte CSV: `{report_csv}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[disenar_arquitectura_ejecucion_fase5] arquitectura generada"))
        self.stdout.write(f"flujos={len(rows)}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")

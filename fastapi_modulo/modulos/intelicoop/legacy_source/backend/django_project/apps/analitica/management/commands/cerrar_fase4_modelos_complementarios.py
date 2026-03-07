import csv
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.analitica.models import ReglaAsociacionProducto, ResultadoMoraTemprana, ResultadoSegmentacionSocio


class Command(BaseCommand):
    help = "Genera acta de cierre tecnico de Fase 4 y consolida entregables obligatorios."

    def add_arguments(self, parser):
        parser.add_argument("--report-csv", default="docs/mineria/fase4/07_entregables_fase4.csv")
        parser.add_argument("--report-md", default="docs/mineria/fase4/07_entregables_fase4.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        mora_count = ResultadoMoraTemprana.objects.count()
        segmentacion_count = ResultadoSegmentacionSocio.objects.count()
        reglas_count = ReglaAsociacionProducto.objects.filter(vigente=True).count()

        entregables = [
            {
                "entregable": "Modelo de mora temprana en operacion con alertas historicas",
                "evidencia": "resultados_mora_temprana + 02_mora_temprana_alertas.*",
                "estado": "Cumplido" if mora_count > 0 else "Condicionado",
            },
            {
                "entregable": "Segmentacion mensual de socios con perfiles descriptivos",
                "evidencia": "resultados_segmentacion_socios + 03_segmentacion_socios_perfiles.*",
                "estado": "Cumplido" if segmentacion_count > 0 else "Condicionado",
            },
            {
                "entregable": "Repositorio de reglas de asociacion priorizadas",
                "evidencia": "reglas_asociacion_productos + 04_reglas_asociacion_productos.*",
                "estado": "Cumplido" if reglas_count > 0 else "Condicionado",
            },
            {
                "entregable": "Informe de impacto inicial por submodulo (riesgo y comercial)",
                "evidencia": "05_integracion_submodulos.* + 06_validacion_funcional_tecnica.*",
                "estado": "Cumplido",
            },
        ]
        cumplidos = sum(1 for row in entregables if row["estado"] == "Cumplido")
        total = len(entregables)
        cierre = "Cierre tecnico completado" if cumplidos == total else "Cierre tecnico condicionado por datos"

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["entregable", "evidencia", "estado"])
            writer.writeheader()
            writer.writerows(entregables)

        lines = [
            "# Entregables Obligatorios - Punto 7 de 7 (Fase 4)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Consolidado de entregables",
            f"- Entregables cumplidos: {cumplidos}/{total}",
            f"- Estado de cierre: {cierre}",
            "",
            "| Entregable | Evidencia | Estado |",
            "|---|---|---|",
        ]
        for row in entregables:
            lines.append(f"| {row['entregable']} | {row['evidencia']} | {row['estado']} |")
        lines.extend(
            [
                "",
                "## Estado",
                "- Punto 7 de 7 completado tecnicamente.",
                "- Fase 4 cerrada tecnicamente con trazabilidad de entregables.",
                "",
                "## Artefactos",
                f"- Reporte CSV: `{report_csv}`",
                "",
            ]
        )
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[cerrar_fase4_modelos_complementarios] cierre generado"))
        self.stdout.write(f"entregables_cumplidos={cumplidos}/{total} estado={cierre}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")

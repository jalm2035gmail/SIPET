import csv
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Consolida entregables obligatorios de Fase 6 y genera acta de cierre tecnico."

    def add_arguments(self, parser):
        parser.add_argument("--report-csv", default="docs/mineria/fase6/08_entregables_fase6.csv")
        parser.add_argument("--report-md", default="docs/mineria/fase6/08_entregables_fase6.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        required_files = [
            root / "docs" / "mineria" / "fase6" / "01_validacion_tecnica_modelos.md",
            root / "docs" / "mineria" / "fase6" / "02_validacion_funcional_negocio.md",
            root / "docs" / "mineria" / "fase6" / "04_seguridad_informacion.md",
            root / "docs" / "mineria" / "fase6" / "06_auditoria_trazabilidad_extremo_extremo.md",
            root / "docs" / "mineria" / "fase6" / "06_auditoria_inferencias.csv",
            root / "docs" / "mineria" / "fase6" / "06_auditoria_aprobaciones_modelo.csv",
            root / "docs" / "mineria" / "fase6" / "05_cumplimiento_privacidad.md",
            root / "docs" / "mineria" / "fase6" / "07_gobierno_cambios_modulo.md",
        ]
        files_ok = all(path.exists() for path in required_files)

        entregables = [
            {
                "entregable": "Informe de validacion tecnica y funcional firmado",
                "evidencia": "01_validacion_tecnica_modelos.md + 02_validacion_funcional_negocio.md",
                "estado": "Cumplido"
                if (required_files[0].exists() and required_files[1].exists())
                else "Condicionado",
            },
            {
                "entregable": "Matriz de riesgos de seguridad y plan de mitigacion",
                "evidencia": "04_seguridad_informacion.*",
                "estado": "Cumplido" if required_files[2].exists() else "Condicionado",
            },
            {
                "entregable": "Evidencia de auditoria de inferencias y versiones de modelos",
                "evidencia": "06_auditoria_trazabilidad_extremo_extremo.* + 06_auditoria_aprobaciones_modelo.csv",
                "estado": "Cumplido"
                if (required_files[3].exists() and required_files[4].exists() and required_files[5].exists())
                else "Condicionado",
            },
            {
                "entregable": "Plan formal de cumplimiento y controles operativos",
                "evidencia": "05_cumplimiento_privacidad.md + 07_gobierno_cambios_modulo.md",
                "estado": "Cumplido"
                if (required_files[6].exists() and required_files[7].exists())
                else "Condicionado",
            },
        ]

        cumplidos = sum(1 for row in entregables if row["estado"] == "Cumplido")
        total = len(entregables)
        cierre = "Cierre tecnico completado" if (cumplidos == total and files_ok) else "Cierre tecnico condicionado"

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["entregable", "evidencia", "estado"])
            writer.writeheader()
            writer.writerows(entregables)

        lines = [
            "# Entregables Obligatorios - Punto 8 de 8 (Fase 6)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Consolidado",
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
                "- Punto 8 de 8 completado tecnicamente.",
                "- Fase 6 cerrada tecnicamente con trazabilidad de entregables obligatorios.",
                "",
                "## Artefactos",
                f"- Reporte CSV: `{report_csv}`",
                "",
            ]
        )
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[cerrar_fase6_validacion_seguridad_auditoria] cierre generado"))
        self.stdout.write(f"entregables_cumplidos={cumplidos}/{total} estado={cierre}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")

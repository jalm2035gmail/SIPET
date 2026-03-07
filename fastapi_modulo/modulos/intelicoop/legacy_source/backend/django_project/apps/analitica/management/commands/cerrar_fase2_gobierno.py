import csv
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Genera acta de cierre tecnico de Fase 2 a partir del checklist de aprobaciones."

    def add_arguments(self, parser):
        parser.add_argument(
            "--checklist-csv",
            default="docs/mineria/fase2/09_pendientes_aprobacion.csv",
            help="Ruta del checklist CSV de Fase 2.",
        )
        parser.add_argument(
            "--output-md",
            default="docs/mineria/fase2/18_cierre_fase2.md",
            help="Ruta de salida del acta de cierre.",
        )

    def handle(self, *args, **options):
        checklist_csv = Path(options["checklist_csv"]).resolve()
        output_md = Path(options["output_md"]).resolve()

        if not checklist_csv.exists():
            raise CommandError(f"No existe checklist CSV: {checklist_csv}")

        rows = []
        with checklist_csv.open("r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                rows.append(row)

        status_counter = Counter((row.get("Estado") or "").strip() for row in rows)
        total = len(rows)
        aprobados = status_counter.get("Aprobado", 0)
        en_revision = status_counter.get("En revision", 0)
        pendientes = status_counter.get("Pendiente", 0)

        cierre_tecnico = "Listo" if (en_revision + pendientes) == 0 else "Listo con pendientes de firma"
        fecha = datetime.now(timezone.utc).isoformat()

        lines = [
            "# Cierre Fase 2 - Gobierno y Preparacion de Datos",
            "",
            f"Fecha de generacion: {fecha}",
            "",
            "## Resumen de checklist",
            f"- Total items: {total}",
            f"- Aprobado: {aprobados}",
            f"- En revision: {en_revision}",
            f"- Pendiente: {pendientes}",
            f"- Estado de cierre tecnico: {cierre_tecnico}",
            "",
            "## Detalle de items",
            "",
            "| Estado | Entregable | Responsable | Fecha objetivo |",
            "|---|---|---|---|",
        ]

        for row in rows:
            lines.append(
                f"| {row.get('Estado','')} | {row.get('Entregable','')} | {row.get('Responsable','')} | {row.get('Fecha objetivo','')} |"
            )

        lines.extend(
            [
                "",
                "## Evidencias tecnicas generadas en Fase 2",
                "- `.run/mineria/perfilamiento_calidad_*.csv/.json`",
                "- `.run/mineria/diccionario_datos_*.csv/.json`",
                "- `docs/mineria/fase2/12_reporte_calidad_datos.md`",
                "- `docs/mineria/fase2/13_plan_remediacion_calidad.csv/.md`",
                "- `docs/mineria/fase2/14_homologacion_catalogos.csv/.md`",
                "- `docs/mineria/fase2/15_validacion_datos.csv/.md`",
                "- `.run/mineria/lineage_registry.jsonl` y `docs/mineria/fase2/16_lineage_cargas.csv/.md`",
                "- `docs/mineria/fase2/17_auditoria_seguridad.csv/.md`",
                "",
                "## Nota",
                "Este cierre representa culminacion tecnica del alcance de Fase 2. La aprobacion final de negocio depende de firmas pendientes.",
                "",
            ]
        )

        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[cerrar_fase2_gobierno] acta generada"))
        self.stdout.write(f"Checklist: {checklist_csv}")
        self.stdout.write(f"Acta: {output_md}")
        self.stdout.write(f"Estado cierre tecnico: {cierre_tecnico}")

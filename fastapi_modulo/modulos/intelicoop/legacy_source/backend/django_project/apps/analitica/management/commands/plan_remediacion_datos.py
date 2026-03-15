import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand, CommandError


def _latest_profile_json(output_dir: Path) -> Path | None:
    files = sorted(output_dir.glob("perfilamiento_calidad_*.json"))
    if not files:
        return None
    return files[-1]


def _severity(item: dict) -> str:
    semaforo = str(item.get("semaforo", "Verde"))
    if semaforo == "Rojo":
        return "Alta"
    if semaforo == "Amarillo":
        return "Media"
    return "Baja"


def _build_actions(item: dict) -> list[dict[str, str]]:
    tabla = str(item.get("tabla", ""))
    pct_nulos = float(item.get("pct_nulos_campos_criticos", 0.0))
    pct_dup = float(item.get("pct_duplicados_clave", 0.0))
    pct_out = float(item.get("pct_fuera_de_rango", 0.0))

    actions: list[dict[str, str]] = []
    MAIN_due = "2026-03-05"

    if pct_nulos > 0:
        actions.append(
            {
                "tabla": tabla,
                "hallazgo": "Nulos en campos criticos",
                "impacto": f"{pct_nulos:.2f}% de registros afectados",
                "accion": "Corregir origen y agregar validacion previa a carga",
                "responsable": "Data + Backend",
                "prioridad": _severity(item),
                "fecha_compromiso": MAIN_due,
                "estado": "Pendiente",
            }
        )
    if pct_dup > 0:
        actions.append(
            {
                "tabla": tabla,
                "hallazgo": "Duplicados de clave",
                "impacto": f"{pct_dup:.2f}% de registros afectados",
                "accion": "Aplicar deduplicacion y regla unica por llave de negocio",
                "responsable": "Data",
                "prioridad": _severity(item),
                "fecha_compromiso": MAIN_due,
                "estado": "Pendiente",
            }
        )
    if pct_out > 0:
        actions.append(
            {
                "tabla": tabla,
                "hallazgo": "Valores fuera de rango",
                "impacto": f"{pct_out:.2f}% de registros afectados",
                "accion": "Ajustar validaciones de rango y corregir registros historicos",
                "responsable": "Riesgo + Data",
                "prioridad": _severity(item),
                "fecha_compromiso": MAIN_due,
                "estado": "Pendiente",
            }
        )

    if not actions:
        actions.append(
            {
                "tabla": tabla,
                "hallazgo": "Sin hallazgos en la corrida",
                "impacto": "0.00% en nulos/duplicados/fuera de rango",
                "accion": "Mantener monitoreo y repetir corrida con datos productivos",
                "responsable": "Data",
                "prioridad": "Baja",
                "fecha_compromiso": MAIN_due,
                "estado": "Pendiente",
            }
        )
    return actions


class Command(MAINCommand):
    help = "Genera plan de remediacion de calidad de datos en CSV y Markdown."

    def add_arguments(self, parser):
        parser.add_argument(
            "--input-dir",
            default=".run/mineria",
            help="Directorio donde existe perfilamiento_calidad_*.json",
        )
        parser.add_argument(
            "--output-csv",
            default="docs/mineria/fase2/13_plan_remediacion_calidad.csv",
            help="Ruta de salida CSV.",
        )
        parser.add_argument(
            "--output-md",
            default="docs/mineria/fase2/13_plan_remediacion_calidad.md",
            help="Ruta de salida Markdown.",
        )

    def handle(self, *args, **options):
        input_dir = Path(options["input_dir"]).resolve()
        output_csv = Path(options["output_csv"]).resolve()
        output_md = Path(options["output_md"]).resolve()

        source = _latest_profile_json(input_dir)
        if source is None:
            raise CommandError(f"No se encontro perfilamiento_calidad_*.json en {input_dir}")

        with source.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        tablas = payload.get("tablas", [])
        rows: list[dict[str, str]] = []
        for item in tablas:
            rows.extend(_build_actions(item))

        output_csv.parent.mkdir(parents=True, exist_ok=True)
        with output_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "tabla",
                    "hallazgo",
                    "impacto",
                    "accion",
                    "responsable",
                    "prioridad",
                    "fecha_compromiso",
                    "estado",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

        md_lines = [
            "# Plan de Remediacion de Calidad de Datos - Fase 2",
            "",
            f"Fecha de generacion: {datetime.now(timezone.utc).isoformat()}",
            f"Fuente: `{source}`",
            "",
            "## Acciones",
            "",
            "| Tabla | Hallazgo | Impacto | Accion | Responsable | Prioridad | Fecha compromiso | Estado |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for row in rows:
            md_lines.append(
                "| {tabla} | {hallazgo} | {impacto} | {accion} | {responsable} | {prioridad} | {fecha_compromiso} | {estado} |".format(
                    **row
                )
            )
        md_lines.append("")
        md_lines.append("## Estado para checklist Fase 2 (Punto 3 de 8)")
        md_lines.append("- Estado sugerido: `En revision`.")
        md_lines.append("- Cierre requerido: asignar dueños por hallazgo y completar fechas reales de remediacion.")
        md_lines.append("")

        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[plan_remediacion_datos] plan generado"))
        self.stdout.write(f"Fuente: {source}")
        self.stdout.write(f"CSV: {output_csv}")
        self.stdout.write(f"MD: {output_md}")

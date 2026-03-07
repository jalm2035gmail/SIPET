import json
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


def _latest_profile_json(output_dir: Path) -> Path | None:
    files = sorted(output_dir.glob("perfilamiento_calidad_*.json"))
    if not files:
        return None
    return files[-1]


def _risk_level(item: dict) -> str:
    semaforo = str(item.get("semaforo", "Verde"))
    if semaforo == "Rojo":
        return "Alto"
    if semaforo == "Amarillo":
        return "Medio"
    return "Bajo"


class Command(BaseCommand):
    help = "Genera reporte markdown de calidad de datos desde el ultimo perfilamiento."

    def add_arguments(self, parser):
        parser.add_argument(
            "--input-dir",
            default=".run/mineria",
            help="Directorio donde existe perfilamiento_calidad_*.json",
        )
        parser.add_argument(
            "--output-md",
            default="docs/mineria/fase2/12_reporte_calidad_datos.md",
            help="Ruta de salida del reporte markdown.",
        )

    def handle(self, *args, **options):
        input_dir = Path(options["input_dir"]).resolve()
        output_md = Path(options["output_md"]).resolve()

        source = _latest_profile_json(input_dir)
        if source is None:
            raise CommandError(f"No se encontro perfilamiento_calidad_*.json en {input_dir}")

        with source.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        fecha_corte = payload.get("fecha_corte", "")
        tablas = payload.get("tablas", [])

        lines: list[str] = []
        lines.append("# Reporte de Calidad de Datos - Fase 2")
        lines.append("")
        lines.append(f"Fecha de generacion: {datetime.now(timezone.utc).isoformat()}")
        lines.append(f"Fuente: `{source}`")
        lines.append(f"Fecha de corte del perfilamiento: {fecha_corte}")
        lines.append("")
        lines.append("## Resumen por tabla")
        lines.append("")
        lines.append("| Tabla | Total | % Nulos criticos | % Duplicados | % Fuera de rango | Semaforo | Riesgo |")
        lines.append("|---|---:|---:|---:|---:|---|---|")

        for item in tablas:
            lines.append(
                "| {tabla} | {total} | {nulos:.2f}% | {dup:.2f}% | {rango:.2f}% | {semaforo} | {riesgo} |".format(
                    tabla=item.get("tabla", ""),
                    total=int(item.get("total_registros", 0)),
                    nulos=float(item.get("pct_nulos_campos_criticos", 0.0)),
                    dup=float(item.get("pct_duplicados_clave", 0.0)),
                    rango=float(item.get("pct_fuera_de_rango", 0.0)),
                    semaforo=item.get("semaforo", ""),
                    riesgo=_risk_level(item),
                )
            )

        lines.append("")
        lines.append("## Hallazgos")
        lines.append("")
        findings = []
        for item in tablas:
            if float(item.get("pct_nulos_campos_criticos", 0.0)) > 0:
                findings.append(
                    f"- `{item.get('tabla')}` presenta nulos criticos: {item.get('pct_nulos_campos_criticos')}%."
                )
            if float(item.get("pct_duplicados_clave", 0.0)) > 0:
                findings.append(
                    f"- `{item.get('tabla')}` presenta duplicados de clave: {item.get('pct_duplicados_clave')}%."
                )
            if float(item.get("pct_fuera_de_rango", 0.0)) > 0:
                findings.append(
                    f"- `{item.get('tabla')}` presenta valores fuera de rango: {item.get('pct_fuera_de_rango')}%."
                )

        if not findings:
            lines.append("- No se detectaron hallazgos en la corrida actual.")
            lines.append("- Nota: validar corrida con datos de mayor volumen para decision de aprobacion.")
        else:
            lines.extend(findings)

        lines.append("")
        lines.append("## Estado para checklist Fase 2 (Punto 2 de 8)")
        lines.append("- Estado sugerido: `En revision`.")
        lines.append("- Cierre requerido: validacion con datos de entorno productivo/representativo.")
        lines.append("")

        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[reporte_calidad_datos] reporte generado"))
        self.stdout.write(f"Fuente: {source}")
        self.stdout.write(f"Reporte: {output_md}")

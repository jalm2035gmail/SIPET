import csv
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ahorros.models import Cuenta, Transaccion
from apps.authentication.models import UserProfile
from apps.creditos.models import Credito
from apps.socios.models import Socio


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.strip().lower().replace("-", "_").replace(" ", "_")


@dataclass
class CatalogSpec:
    etiqueta: str
    model: object
    field: str
    valid_values: set[str]
    aliases: dict[str, str]


SPECS: list[CatalogSpec] = [
    CatalogSpec(
        etiqueta="creditos.estado",
        model=Credito,
        field="estado",
        valid_values={"solicitado", "aprobado", "rechazado"},
        aliases={
            "solicitud": "solicitado",
            "aprobada": "aprobado",
            "denegado": "rechazado",
        },
    ),
    CatalogSpec(
        etiqueta="socios.segmento",
        model=Socio,
        field="segmento",
        valid_values={"hormiga", "gran_ahorrador", "inactivo"},
        aliases={
            "ahorrador_hormiga": "hormiga",
            "gran_ahorrador": "gran_ahorrador",
            "gran__ahorrador": "gran_ahorrador",
            "granahorrador": "gran_ahorrador",
        },
    ),
    CatalogSpec(
        etiqueta="authentication.userprofile.rol",
        model=UserProfile,
        field="rol",
        valid_values={"superadmin", "administrador", "jefe_departamento", "auditor"},
        aliases={
            "superadministrador": "superadmin",
            "jefe_de_departamento": "jefe_departamento",
            "jefe_departamento": "jefe_departamento",
            "admin": "administrador",
            "oficial": "auditor",
            "gerente": "jefe_departamento",
        },
    ),
    CatalogSpec(
        etiqueta="ahorros.cuenta.tipo",
        model=Cuenta,
        field="tipo",
        valid_values={"ahorro", "aportacion"},
        aliases={
            "ahorros": "ahorro",
            "aportacion": "aportacion",
        },
    ),
    CatalogSpec(
        etiqueta="ahorros.transaccion.tipo",
        model=Transaccion,
        field="tipo",
        valid_values={"deposito", "retiro"},
        aliases={
            "extraccion": "retiro",
        },
    ),
]


def _map_value(raw: str, spec: CatalogSpec) -> tuple[str, bool]:
    normalized = _normalize(raw)
    normalized = spec.aliases.get(normalized, normalized)
    if normalized in spec.valid_values:
        return normalized, True
    return normalized, False


class Command(BaseCommand):
    help = "Homologa catálogos de dominio y genera reporte (dry-run por defecto)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplica cambios en base de datos. Por defecto solo analiza.",
        )
        parser.add_argument(
            "--output-csv",
            default="docs/mineria/fase2/14_homologacion_catalogos.csv",
            help="Ruta de salida CSV.",
        )
        parser.add_argument(
            "--output-md",
            default="docs/mineria/fase2/14_homologacion_catalogos.md",
            help="Ruta de salida Markdown.",
        )

    def handle(self, *args, **options):
        apply_changes = bool(options["apply"])
        output_csv = Path(options["output_csv"]).resolve()
        output_md = Path(options["output_md"]).resolve()
        timestamp = datetime.now(timezone.utc).isoformat()

        rows: list[dict[str, str]] = []

        with transaction.atomic():
            for spec in SPECS:
                total = 0
                planned_updates = 0
                applied_updates = 0
                invalid_values = 0

                queryset = spec.model.objects.all().only("id", spec.field)
                for obj in queryset.iterator():
                    total += 1
                    current = getattr(obj, spec.field, "")
                    mapped, is_valid = _map_value(current, spec)

                    if not is_valid:
                        invalid_values += 1
                        continue

                    if mapped != current:
                        planned_updates += 1
                        if apply_changes:
                            setattr(obj, spec.field, mapped)
                            obj.save(update_fields=[spec.field])
                            applied_updates += 1

                rows.append(
                    {
                        "catalogo": spec.etiqueta,
                        "total_registros": str(total),
                        "actualizaciones_planeadas": str(planned_updates),
                        "actualizaciones_aplicadas": str(applied_updates),
                        "valores_invalidos": str(invalid_values),
                        "modo": "apply" if apply_changes else "dry-run",
                    }
                )

            if not apply_changes:
                transaction.set_rollback(True)

        output_csv.parent.mkdir(parents=True, exist_ok=True)
        with output_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "catalogo",
                    "total_registros",
                    "actualizaciones_planeadas",
                    "actualizaciones_aplicadas",
                    "valores_invalidos",
                    "modo",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

        md_lines = [
            "# Homologacion de Catalogos - Fase 2",
            "",
            f"Fecha de generacion: {timestamp}",
            f"Modo: {'apply' if apply_changes else 'dry-run'}",
            "",
            "## Resumen",
            "",
            "| Catalogo | Total registros | Planeadas | Aplicadas | Invalidos | Modo |",
            "|---|---:|---:|---:|---:|---|",
        ]
        for row in rows:
            md_lines.append(
                "| {catalogo} | {total_registros} | {actualizaciones_planeadas} | {actualizaciones_aplicadas} | {valores_invalidos} | {modo} |".format(
                    **row
                )
            )
        md_lines.append("")
        md_lines.append("## Estado para checklist Fase 2 (Punto 4 de 8)")
        md_lines.append("- Estado sugerido: `En revision`.")
        md_lines.append("- Cierre requerido: ejecutar en entorno con datos productivos y aprobar resultados.")
        md_lines.append("")

        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[homologar_catalogos] proceso completado"))
        self.stdout.write(f"Modo: {'apply' if apply_changes else 'dry-run'}")
        for row in rows:
            self.stdout.write(
                f"- {row['catalogo']}: total={row['total_registros']} "
                f"planeadas={row['actualizaciones_planeadas']} "
                f"aplicadas={row['actualizaciones_aplicadas']} "
                f"invalidos={row['valores_invalidos']}"
            )
        self.stdout.write(f"CSV: {output_csv}")
        self.stdout.write(f"MD: {output_md}")

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from django.apps import apps
from django.core.management.MAIN import MAINCommand
from django.db.models import NOT_PROVIDED


ALLOWED_APPS = {"socios", "creditos", "ahorros", "authentication", "analitica"}


def _serialize_default(field) -> str:
    default = field.default
    if default is NOT_PROVIDED:
        return ""
    if callable(default):
        return getattr(default, "__name__", str(default))
    return str(default)


def _serialize_choices(field) -> str:
    if not field.choices:
        return ""
    return "|".join(f"{key}:{label}" for key, label in field.choices)


def _serialize_field(model, field) -> dict[str, str]:
    related_model = ""
    if getattr(field, "remote_field", None) and getattr(field.remote_field, "model", None):
        related_model = field.remote_field.model._meta.label

    return {
        "app": model._meta.app_label,
        "modelo": model.__name__,
        "tabla_db": model._meta.db_table,
        "campo": field.name,
        "tipo": field.get_internal_type(),
        "nulo": str(bool(getattr(field, "null", False))).lower(),
        "blank": str(bool(getattr(field, "blank", False))).lower(),
        "unico": str(bool(getattr(field, "unique", False))).lower(),
        "indice": str(bool(getattr(field, "db_index", False))).lower(),
        "pk": str(bool(getattr(field, "primary_key", False))).lower(),
        "max_length": str(getattr(field, "max_length", "") or ""),
        "max_digits": str(getattr(field, "max_digits", "") or ""),
        "decimal_places": str(getattr(field, "decimal_places", "") or ""),
        "default": _serialize_default(field),
        "choices": _serialize_choices(field),
        "related_model": related_model,
        "help_text": str(getattr(field, "help_text", "") or ""),
    }


def _collect_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for model in apps.get_models():
        app_label = model._meta.app_label
        if app_label not in ALLOWED_APPS:
            continue
        for field in model._meta.get_fields():
            if not getattr(field, "concrete", False):
                continue
            rows.append(_serialize_field(model, field))

    rows.sort(key=lambda item: (item["app"], item["modelo"], item["campo"]))
    return rows


class Command(MAINCommand):
    help = "Genera diccionario de datos tecnico desde modelos ORM (CSV/JSON)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            default=".run/mineria",
            help="Directorio de salida para reportes.",
        )
        parser.add_argument(
            "--format",
            choices=("csv", "json", "both"),
            default="both",
            help="Formato de salida.",
        )

    def handle(self, *args, **options):
        output_dir = Path(options["output_dir"]).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_format = options["format"]

        rows = _collect_rows()
        fecha_corte = datetime.now(timezone.utc).isoformat()
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        csv_path = output_dir / f"diccionario_datos_{ts}.csv"
        json_path = output_dir / f"diccionario_datos_{ts}.json"

        if output_format in ("csv", "both"):
            with csv_path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()) if rows else [])
                if rows:
                    writer.writeheader()
                    writer.writerows(rows)

        if output_format in ("json", "both"):
            payload = {
                "fecha_corte": fecha_corte,
                "total_campos": len(rows),
                "catalogo": rows,
            }
            with json_path.open("w", encoding="utf-8") as file:
                json.dump(payload, file, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(f"[diccionario_datos] fecha_corte={fecha_corte}"))
        self.stdout.write(f"- total_campos={len(rows)}")
        if output_format in ("csv", "both"):
            self.stdout.write(f"CSV: {csv_path}")
        if output_format in ("json", "both"):
            self.stdout.write(f"JSON: {json_path}")

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from apps.ahorros.models import Cuenta, Transaccion
from apps.creditos.models import Credito, HistorialPago
from apps.socios.models import Socio


@dataclass
class TableProfile:
    tabla: str
    total_registros: int
    nulos_campos_criticos: int
    pct_nulos_campos_criticos: float
    duplicados_clave: int
    pct_duplicados_clave: float
    fuera_de_rango: int
    pct_fuera_de_rango: float
    semaforo: str


def _duplicate_excess(model, key_fields: list[str]) -> int:
    if not key_fields:
        return 0
    duplicated_groups = (
        model.objects.values(*key_fields).annotate(n=Count("id")).filter(n__gt=1)
    )
    return int(sum(item["n"] - 1 for item in duplicated_groups))


def _pct(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((part / total) * 100.0, 2)


def _semaphore(pct_nulos: float, pct_duplicados: float, pct_fuera_rango: float) -> str:
    worst = max(pct_nulos, pct_duplicados, pct_fuera_rango)
    if worst >= 10:
        return "Rojo"
    if worst >= 3:
        return "Amarillo"
    return "Verde"


def _profile_tables() -> Iterable[TableProfile]:
    specs = [
        {
            "tabla": "socios",
            "model": Socio,
            "critical_null_q": Q(nombre__isnull=True)
            | Q(nombre="")
            | Q(email__isnull=True)
            | Q(email=""),
            "out_range_q": Q(),
            "dup_keys": ["email"],
        },
        {
            "tabla": "creditos",
            "model": Credito,
            "critical_null_q": Q(socio__isnull=True)
            | Q(monto__isnull=True)
            | Q(plazo__isnull=True)
            | Q(estado__isnull=True)
            | Q(estado=""),
            "out_range_q": Q(monto__lte=0)
            | Q(plazo__lte=0)
            | Q(ingreso_mensual__lte=0)
            | Q(deuda_actual__lt=0)
            | Q(antiguedad_meses__lt=0),
            "dup_keys": ["socio_id", "fecha_creacion", "monto", "plazo"],
        },
        {
            "tabla": "historial_pagos",
            "model": HistorialPago,
            "critical_null_q": Q(credito__isnull=True) | Q(fecha__isnull=True) | Q(monto__isnull=True),
            "out_range_q": Q(monto__lte=0),
            "dup_keys": ["credito_id", "fecha", "monto"],
        },
        {
            "tabla": "cuentas",
            "model": Cuenta,
            "critical_null_q": Q(socio__isnull=True) | Q(tipo__isnull=True) | Q(tipo=""),
            "out_range_q": Q(saldo__lt=0),
            "dup_keys": ["socio_id", "tipo", "fecha_creacion"],
        },
        {
            "tabla": "transacciones",
            "model": Transaccion,
            "critical_null_q": Q(cuenta__isnull=True) | Q(tipo__isnull=True) | Q(tipo="") | Q(fecha__isnull=True),
            "out_range_q": Q(monto__lte=0),
            "dup_keys": ["cuenta_id", "tipo", "monto", "fecha"],
        },
    ]

    for spec in specs:
        model = spec["model"]
        total = model.objects.count()
        nulos = model.objects.filter(spec["critical_null_q"]).count()
        fuera_rango = model.objects.filter(spec["out_range_q"]).count() if spec["out_range_q"] else 0
        duplicados = _duplicate_excess(model, spec["dup_keys"])

        pct_nulos = _pct(nulos, total)
        pct_dup = _pct(duplicados, total)
        pct_out = _pct(fuera_rango, total)
        semaforo = _semaphore(pct_nulos, pct_dup, pct_out)

        yield TableProfile(
            tabla=spec["tabla"],
            total_registros=total,
            nulos_campos_criticos=nulos,
            pct_nulos_campos_criticos=pct_nulos,
            duplicados_clave=duplicados,
            pct_duplicados_clave=pct_dup,
            fuera_de_rango=fuera_rango,
            pct_fuera_de_rango=pct_out,
            semaforo=semaforo,
        )


class Command(BaseCommand):
    help = "Perfila calidad de datos para tablas clave y genera reporte CSV/JSON."

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

        fecha_corte = datetime.now(timezone.utc).isoformat()
        profiles = list(_profile_tables())
        payload = {
            "fecha_corte": fecha_corte,
            "tablas": [item.__dict__ for item in profiles],
        }

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        csv_path = output_dir / f"perfilamiento_calidad_{ts}.csv"
        json_path = output_dir / f"perfilamiento_calidad_{ts}.json"

        if output_format in ("csv", "both"):
            with csv_path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=list(TableProfile.__annotations__.keys()),
                )
                writer.writeheader()
                for item in profiles:
                    writer.writerow(item.__dict__)

        if output_format in ("json", "both"):
            with json_path.open("w", encoding="utf-8") as file:
                json.dump(payload, file, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(f"[perfilar_datos] fecha_corte={fecha_corte}"))
        for item in profiles:
            self.stdout.write(
                f"- {item.tabla}: total={item.total_registros}, "
                f"nulos={item.nulos_campos_criticos} ({item.pct_nulos_campos_criticos}%), "
                f"dup={item.duplicados_clave} ({item.pct_duplicados_clave}%), "
                f"rango={item.fuera_de_rango} ({item.pct_fuera_de_rango}%), "
                f"semaforo={item.semaforo}"
            )

        if output_format in ("csv", "both"):
            self.stdout.write(f"CSV: {csv_path}")
        if output_format in ("json", "both"):
            self.stdout.write(f"JSON: {json_path}")

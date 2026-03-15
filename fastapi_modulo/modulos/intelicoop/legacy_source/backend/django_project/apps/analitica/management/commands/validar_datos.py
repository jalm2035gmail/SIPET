import csv
from datetime import date, datetime, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand
from django.db.models import F, Q

from apps.ahorros.models import Cuenta, Transaccion
from apps.creditos.models import Credito, HistorialPago
from apps.socios.models import Socio


def _append_rule(rows: list[dict[str, str]], tabla: str, regla: str, violaciones: int, severidad: str) -> None:
    rows.append(
        {
            "tabla": tabla,
            "regla": regla,
            "violaciones": str(violaciones),
            "severidad": severidad,
            "estado": "Incumple" if violaciones > 0 else "Cumple",
        }
    )


class Command(MAINCommand):
    help = "Valida reglas de calidad/consistencia y genera reporte de incumplimientos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-csv",
            default="docs/mineria/fase2/15_validacion_datos.csv",
            help="Ruta de salida CSV.",
        )
        parser.add_argument(
            "--output-md",
            default="docs/mineria/fase2/15_validacion_datos.md",
            help="Ruta de salida Markdown.",
        )

    def handle(self, *args, **options):
        output_csv = Path(options["output_csv"]).resolve()
        output_md = Path(options["output_md"]).resolve()
        today = date.today()

        rows: list[dict[str, str]] = []

        # Socios
        _append_rule(
            rows,
            "socios",
            "nombre no vacio",
            Socio.objects.filter(Q(nombre__isnull=True) | Q(nombre="")).count(),
            "Alta",
        )
        _append_rule(
            rows,
            "socios",
            "email no vacio",
            Socio.objects.filter(Q(email__isnull=True) | Q(email="")).count(),
            "Alta",
        )

        # Creditos
        _append_rule(rows, "creditos", "monto > 0", Credito.objects.filter(monto__lte=0).count(), "Alta")
        _append_rule(rows, "creditos", "plazo > 0", Credito.objects.filter(plazo__lte=0).count(), "Alta")
        _append_rule(
            rows,
            "creditos",
            "ingreso_mensual > 0",
            Credito.objects.filter(ingreso_mensual__lte=0).count(),
            "Alta",
        )
        _append_rule(
            rows,
            "creditos",
            "deuda_actual >= 0",
            Credito.objects.filter(deuda_actual__lt=0).count(),
            "Alta",
        )
        _append_rule(
            rows,
            "creditos",
            "deuda_actual <= ingreso_mensual",
            Credito.objects.filter(deuda_actual__gt=F("ingreso_mensual")).count(),
            "Media",
        )
        _append_rule(
            rows,
            "creditos",
            "antiguedad_meses >= 0",
            Credito.objects.filter(antiguedad_meses__lt=0).count(),
            "Media",
        )

        # Historial pagos
        _append_rule(
            rows,
            "historial_pagos",
            "monto > 0",
            HistorialPago.objects.filter(monto__lte=0).count(),
            "Alta",
        )
        _append_rule(
            rows,
            "historial_pagos",
            "fecha <= hoy",
            HistorialPago.objects.filter(fecha__gt=today).count(),
            "Baja",
        )

        # Ahorros
        _append_rule(rows, "cuentas", "saldo >= 0", Cuenta.objects.filter(saldo__lt=0).count(), "Media")
        _append_rule(
            rows,
            "transacciones",
            "monto > 0",
            Transaccion.objects.filter(monto__lte=0).count(),
            "Alta",
        )

        total_rules = len(rows)
        failed_rules = sum(1 for row in rows if row["estado"] == "Incumple")

        output_csv.parent.mkdir(parents=True, exist_ok=True)
        with output_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["tabla", "regla", "violaciones", "severidad", "estado"],
            )
            writer.writeheader()
            writer.writerows(rows)

        md_lines = [
            "# Validacion de Datos - Fase 2",
            "",
            f"Fecha de generacion: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Reglas evaluadas",
            "",
            "| Tabla | Regla | Violaciones | Severidad | Estado |",
            "|---|---|---:|---|---|",
        ]
        for row in rows:
            md_lines.append(
                "| {tabla} | {regla} | {violaciones} | {severidad} | {estado} |".format(
                    **row
                )
            )
        md_lines.extend(
            [
                "",
                "## Resumen",
                f"- Total de reglas: {total_rules}",
                f"- Reglas con incumplimientos: {failed_rules}",
                "",
                "## Estado para checklist Fase 2 (Punto 5 de 8)",
                "- Estado sugerido: `En revision`.",
                "- Cierre requerido: resolver reglas con incumplimientos y ejecutar corrida de confirmacion.",
                "",
            ]
        )
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text("\n".join(md_lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[validar_datos] validacion completada"))
        self.stdout.write(f"Total reglas: {total_rules}")
        self.stdout.write(f"Reglas incumplidas: {failed_rules}")
        self.stdout.write(f"CSV: {output_csv}")
        self.stdout.write(f"MD: {output_md}")

import csv
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand
from django.db.models import Count, Sum

from apps.ahorros.models import Cuenta, Transaccion
from apps.analitica.models import ResultadoMoraTemprana
from apps.creditos.models import Credito
from apps.socios.models import Socio


class Command(MAINCommand):
    help = "Elemento 1/4 de 1.2: genera catalogo maestro institucional consolidado (verdad unica por socio)."

    def add_arguments(self, parser):
        parser.add_argument("--report-csv", default="docs/mineria/masterdata/01_catalogo_maestro_institucional.csv")
        parser.add_argument("--report-md", default="docs/mineria/masterdata/01_catalogo_maestro_institucional.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        creditos_por_socio = {
            row["socio_id"]: {
                "total_creditos": row["total"],
                "monto_total_credito": float(row["monto_total"] or 0),
            }
            for row in Credito.objects.values("socio_id").annotate(
                total=Count("id"),
                monto_total=Sum("monto"),
            )
        }
        cuentas_por_socio = {
            row["socio_id"]: {
                "total_cuentas": row["total"],
                "saldo_total_captacion": float(row["saldo_total"] or 0),
            }
            for row in Cuenta.objects.values("socio_id").annotate(
                total=Count("id"),
                saldo_total=Sum("saldo"),
            )
        }
        tx_por_socio = {
            row["cuenta__socio_id"]: {
                "total_movimientos": row["total"],
                "monto_movimientos": float(row["monto_total"] or 0),
            }
            for row in Transaccion.objects.values("cuenta__socio_id").annotate(
                total=Count("id"),
                monto_total=Sum("monto"),
            )
        }
        mora_por_socio = {
            row["socio_id"]: {
                "total_alertas_mora": row["total"],
                "alertas_mora_alta": 0,
            }
            for row in ResultadoMoraTemprana.objects.values("socio_id").annotate(
                total=Count("id"),
            )
        }
        # Conteo de altas con query separada para compatibilidad simple.
        mora_altas = {
            row["socio_id"]: row["total"]
            for row in ResultadoMoraTemprana.objects.filter(alerta=ResultadoMoraTemprana.ALERTA_ALTA)
            .values("socio_id")
            .annotate(total=Count("id"))
        }
        for socio_id, total_altas in mora_altas.items():
            if socio_id not in mora_por_socio:
                mora_por_socio[socio_id] = {"total_alertas_mora": 0, "alertas_mora_alta": 0}
            mora_por_socio[socio_id]["alertas_mora_alta"] = total_altas

        rows = []
        for socio in Socio.objects.all().order_by("id"):
            c = creditos_por_socio.get(socio.id, {})
            a = cuentas_por_socio.get(socio.id, {})
            t = tx_por_socio.get(socio.id, {})
            m = mora_por_socio.get(socio.id, {})
            rows.append(
                {
                    "socio_id": socio.id,
                    "nombre": socio.nombre,
                    "email": socio.email,
                    "telefono": socio.telefono,
                    "direccion": socio.direccion,
                    "segmento": socio.segmento,
                    "fecha_registro": str(socio.fecha_registro),
                    "total_creditos": c.get("total_creditos", 0),
                    "monto_total_credito": f"{c.get('monto_total_credito', 0.0):.2f}",
                    "total_cuentas": a.get("total_cuentas", 0),
                    "saldo_total_captacion": f"{a.get('saldo_total_captacion', 0.0):.2f}",
                    "total_movimientos": t.get("total_movimientos", 0),
                    "monto_movimientos": f"{t.get('monto_movimientos', 0.0):.2f}",
                    "total_alertas_mora": m.get("total_alertas_mora", 0),
                    "alertas_mora_alta": m.get("alertas_mora_alta", 0),
                }
            )

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "socio_id",
                    "nombre",
                    "email",
                    "telefono",
                    "direccion",
                    "segmento",
                    "fecha_registro",
                    "total_creditos",
                    "monto_total_credito",
                    "total_cuentas",
                    "saldo_total_captacion",
                    "total_movimientos",
                    "monto_movimientos",
                    "total_alertas_mora",
                    "alertas_mora_alta",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

        lines = [
            "# Catalogo Maestro Institucional 1.2 - Elemento 1 de 4",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Alcance",
            "- Consolidacion por `socio_id` en una vista unificada institucional.",
            "- Integracion de dominios: socios, creditos, captacion, movimientos y alertas de mora.",
            "",
            "## Resumen",
            f"- Socios consolidados: {len(rows)}",
            "",
            "## Estado",
            "- Elemento 1 de 4 completado tecnicamente.",
            "- Verdad unica institucional MAIN implementada a nivel de catalogo maestro.",
            "",
            "## Artefactos",
            f"- Reporte CSV: `{report_csv}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[catalogo_maestro_institucional_1_2] catalogo generado"))
        self.stdout.write(f"socios={len(rows)}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")

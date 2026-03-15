import csv
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand

from apps.analitica.models import Campania


DEFAULT_COMERCIOS = [
    {"comercio_id": "COM-001", "nombre": "Farmacia Cooperativa", "categoria": "salud", "canal": "sucursal"},
    {"comercio_id": "COM-002", "nombre": "Agroinsumos Aliados", "categoria": "agro", "canal": "territorial"},
    {"comercio_id": "COM-003", "nombre": "Electro Hogar Local", "categoria": "retail", "canal": "digital"},
]


def _asignar_comercio(campania: Campania) -> dict:
    text = f"{campania.nombre} {campania.tipo}".lower()
    if "salud" in text or "farm" in text:
        return DEFAULT_COMERCIOS[0]
    if "agro" in text or "campo" in text:
        return DEFAULT_COMERCIOS[1]
    return DEFAULT_COMERCIOS[2]


class Command(MAINCommand):
    help = "Elemento 3/4 de 1.2: catalogo de comercios aliados y vinculacion con campanas."

    def add_arguments(self, parser):
        parser.add_argument("--report-csv", default="docs/mineria/masterdata/03_comercios_campanas.csv")
        parser.add_argument("--report-md", default="docs/mineria/masterdata/03_comercios_campanas.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        campanias_rows = []
        for campania in Campania.objects.all().order_by("id"):
            comercio = _asignar_comercio(campania)
            campanias_rows.append(
                {
                    "campania_id": campania.id,
                    "campania_nombre": campania.nombre,
                    "campania_tipo": campania.tipo,
                    "campania_estado": campania.estado,
                    "comercio_id": comercio["comercio_id"],
                    "comercio_nombre": comercio["nombre"],
                    "categoria": comercio["categoria"],
                    "canal": comercio["canal"],
                }
            )

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "tipo",
                    "comercio_id",
                    "comercio_nombre",
                    "categoria",
                    "canal",
                    "campania_id",
                    "campania_nombre",
                    "campania_tipo",
                    "campania_estado",
                ],
            )
            writer.writeheader()
            for comercio in DEFAULT_COMERCIOS:
                writer.writerow(
                    {
                        "tipo": "catalogo_comercio",
                        "comercio_id": comercio["comercio_id"],
                        "comercio_nombre": comercio["nombre"],
                        "categoria": comercio["categoria"],
                        "canal": comercio["canal"],
                        "campania_id": "",
                        "campania_nombre": "",
                        "campania_tipo": "",
                        "campania_estado": "",
                    }
                )
            for row in campanias_rows:
                writer.writerow(
                    {
                        "tipo": "mapeo_campania_comercio",
                        "comercio_id": row["comercio_id"],
                        "comercio_nombre": row["comercio_nombre"],
                        "categoria": row["categoria"],
                        "canal": row["canal"],
                        "campania_id": row["campania_id"],
                        "campania_nombre": row["campania_nombre"],
                        "campania_tipo": row["campania_tipo"],
                        "campania_estado": row["campania_estado"],
                    }
                )

        lines = [
            "# Catalogo Comercios/Campanas 1.2 - Elemento 3 de 4",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Catalogo MAIN de comercios aliados",
            f"- Comercios catalogados: {len(DEFAULT_COMERCIOS)}",
            f"- Campanas vinculadas: {len(campanias_rows)}",
            "",
            "## Estado",
            "- Elemento 3 de 4 completado tecnicamente.",
            "- Catalogo de comercios aliados y vinculacion con campanas implementados.",
            "",
            "## Artefactos",
            f"- Reporte CSV: `{report_csv}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[catalogo_comercios_campanas_1_2] catalogo generado"))
        self.stdout.write(f"comercios={len(DEFAULT_COMERCIOS)} campanas_vinculadas={len(campanias_rows)}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")

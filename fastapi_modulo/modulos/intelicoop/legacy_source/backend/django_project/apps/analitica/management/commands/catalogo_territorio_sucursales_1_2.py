import csv
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand

from apps.socios.models import Socio


SUCURSALES_MAIN = [
    {"sucursal_id": "SUC-YUR", "nombre_sucursal": "Yuriria", "municipio": "Yuriria", "region": "sur"},
    {"sucursal_id": "SUC-CUI", "nombre_sucursal": "Cuitzeo", "municipio": "Cuitzeo", "region": "norte"},
    {"sucursal_id": "SUC-SAM", "nombre_sucursal": "Santa Ana Maya", "municipio": "Santa Ana Maya", "region": "este"},
]


def _normalizar_texto(value: str) -> str:
    return (value or "").strip().lower()


def _asignar_sucursal(direccion: str) -> dict:
    text = _normalizar_texto(direccion)
    if "yuriria" in text:
        return SUCURSALES_MAIN[0]
    if "cuitzeo" in text:
        return SUCURSALES_MAIN[1]
    if "santa ana maya" in text or "santa_ana_maya" in text:
        return SUCURSALES_MAIN[2]
    # Default operativo cuando no hay georreferencia.
    return SUCURSALES_MAIN[0]


class Command(MAINCommand):
    help = "Elemento 2/4 de 1.2: catalogo de sucursales/territorio y mapeo de socios."

    def add_arguments(self, parser):
        parser.add_argument("--report-csv", default="docs/mineria/masterdata/02_sucursales_territorio.csv")
        parser.add_argument("--report-md", default="docs/mineria/masterdata/02_sucursales_territorio.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        socios_rows = []
        for socio in Socio.objects.all().order_by("id"):
            suc = _asignar_sucursal(socio.direccion)
            socios_rows.append(
                {
                    "socio_id": socio.id,
                    "socio_nombre": socio.nombre,
                    "direccion": socio.direccion,
                    "sucursal_id": suc["sucursal_id"],
                    "sucursal_nombre": suc["nombre_sucursal"],
                    "municipio": suc["municipio"],
                    "region": suc["region"],
                }
            )

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "tipo",
                    "sucursal_id",
                    "nombre_sucursal",
                    "municipio",
                    "region",
                    "socio_id",
                    "socio_nombre",
                    "direccion",
                ],
            )
            writer.writeheader()
            for suc in SUCURSALES_MAIN:
                writer.writerow(
                    {
                        "tipo": "catalogo_sucursal",
                        "sucursal_id": suc["sucursal_id"],
                        "nombre_sucursal": suc["nombre_sucursal"],
                        "municipio": suc["municipio"],
                        "region": suc["region"],
                        "socio_id": "",
                        "socio_nombre": "",
                        "direccion": "",
                    }
                )
            for row in socios_rows:
                writer.writerow(
                    {
                        "tipo": "mapeo_socio_territorio",
                        "sucursal_id": row["sucursal_id"],
                        "nombre_sucursal": row["sucursal_nombre"],
                        "municipio": row["municipio"],
                        "region": row["region"],
                        "socio_id": row["socio_id"],
                        "socio_nombre": row["socio_nombre"],
                        "direccion": row["direccion"],
                    }
                )

        lines = [
            "# Catalogo Sucursales/Territorio 1.2 - Elemento 2 de 4",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Catalogo MAIN",
            "- Yuriria",
            "- Cuitzeo",
            "- Santa Ana Maya",
            "",
            "## Resumen",
            f"- Sucursales catalogadas: {len(SUCURSALES_MAIN)}",
            f"- Socios mapeados a territorio: {len(socios_rows)}",
            "",
            "## Estado",
            "- Elemento 2 de 4 completado tecnicamente.",
            "- Sucursales y territorio institucionales definidos con `sucursal_id` consistente.",
            "",
            "## Artefactos",
            f"- Reporte CSV: `{report_csv}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[catalogo_territorio_sucursales_1_2] catalogo generado"))
        self.stdout.write(f"sucursales={len(SUCURSALES_MAIN)} socios_mapeados={len(socios_rows)}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")

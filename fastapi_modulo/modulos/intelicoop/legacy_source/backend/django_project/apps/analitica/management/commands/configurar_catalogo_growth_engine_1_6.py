import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand


DEFAULT_CATALOGO = {
    "version": "growth_engine_catalogo_v1",
    "fallback_sucursal": "Yuriria",
    "sucursales": [
        {
            "sucursal_id": "yuriria",
            "nombre": "Yuriria",
            "territorio_keywords": ["yuriria"],
            "ejecutivos": ["ejec_yur_01", "ejec_yur_02"],
        },
        {
            "sucursal_id": "cuitzeo",
            "nombre": "Cuitzeo",
            "territorio_keywords": ["cuitzeo"],
            "ejecutivos": ["ejec_cui_01"],
        },
        {
            "sucursal_id": "santa_ana_maya",
            "nombre": "Santa Ana Maya",
            "territorio_keywords": ["santa ana maya"],
            "ejecutivos": ["ejec_sam_01"],
        },
    ],
}


class Command(BaseCommand):
    help = "Configura catalogo operativo de sucursales/territorio/ejecutivos para Growth Engine 1.6."

    def add_arguments(self, parser):
        parser.add_argument("--catalog-version", default="growth_engine_catalogo_v1")
        parser.add_argument(
            "--catalogo-json",
            default="docs/mineria/growth_engine/00_catalogo_sucursales_ejecutivos.json",
        )
        parser.add_argument(
            "--report-csv",
            default="docs/mineria/growth_engine/00_catalogo_sucursales_ejecutivos.csv",
        )
        parser.add_argument(
            "--report-md",
            default="docs/mineria/growth_engine/00_catalogo_sucursales_ejecutivos.md",
        )

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        catalogo_json_opt = Path(options["catalogo_json"])
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        catalogo_json = catalogo_json_opt if catalogo_json_opt.is_absolute() else (root / catalogo_json_opt)
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        version = str(options["catalog_version"] or "growth_engine_catalogo_v1")
        payload = dict(DEFAULT_CATALOGO)
        payload["version"] = version

        catalogo_json.parent.mkdir(parents=True, exist_ok=True)
        catalogo_json.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

        rows = []
        for s in payload["sucursales"]:
            rows.append(
                {
                    "version": version,
                    "sucursal_id": s["sucursal_id"],
                    "sucursal_nombre": s["nombre"],
                    "territorio_keywords": "|".join(s["territorio_keywords"]),
                    "ejecutivos": "|".join(s["ejecutivos"]),
                }
            )
        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["version", "sucursal_id", "sucursal_nombre", "territorio_keywords", "ejecutivos"],
            )
            writer.writeheader()
            writer.writerows(rows)

        lines = [
            "# Catalogo Operativo Growth Engine 1.6 - Punto 1 de 3",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            f"Version catalogo: {version}",
            "",
            "## Estado",
            "- Punto 1 de 3 completado tecnicamente.",
            "- Catalogo real de sucursales y ejecutivos definido y versionado.",
            "",
            "## Artefactos",
            f"- Catalogo JSON: `{catalogo_json}`",
            f"- Matriz CSV: `{report_csv}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[configurar_catalogo_growth_engine_1_6] catalogo generado"))
        self.stdout.write(f"catalog_version={version}")
        self.stdout.write(f"catalogo_json={catalogo_json}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")

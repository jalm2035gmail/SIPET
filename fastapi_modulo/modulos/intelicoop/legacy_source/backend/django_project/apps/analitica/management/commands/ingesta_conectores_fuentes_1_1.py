import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand


class Command(MAINCommand):
    help = "Etapa 2/4 de Data Intake: diagnostico de conectores (PostgreSQL/MySQL/APIs/SFTP/archivos)."

    def add_arguments(self, parser):
        parser.add_argument("--report-csv", default="docs/mineria/intake/02_conectores_fuentes.csv")
        parser.add_argument("--report-md", default="docs/mineria/intake/02_conectores_fuentes.md")
        parser.add_argument(
            "--manifest-json",
            default="docs/mineria/intake/02_conectores_manifest.json",
            help="Salida JSON con estado de conectores.",
        )
        parser.add_argument(
            "--input-dir",
            default=".run/mineria/intake/incoming",
            help="Directorio de archivos para conector tipo archivo.",
        )

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        manifest_json_opt = Path(options["manifest_json"])
        input_dir_opt = Path(options["input_dir"])

        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)
        manifest_json = manifest_json_opt if manifest_json_opt.is_absolute() else (root / manifest_json_opt)
        input_dir = input_dir_opt if input_dir_opt.is_absolute() else (root / input_dir_opt)

        ts = datetime.now(timezone.utc).isoformat()

        postgres_ready = bool(os.getenv("POSTGRES_HOST")) and bool(os.getenv("POSTGRES_DB"))
        mysql_ready = bool(os.getenv("MYSQL_HOST")) and bool(os.getenv("MYSQL_DB"))
        sftp_ready = bool(os.getenv("SFTP_HOST")) and bool(os.getenv("SFTP_USER"))
        api_ready = bool(os.getenv("EXTERNAL_API_MAIN_URL")) or bool(os.getenv("DJANGO_MAIN_URL"))
        files_ready = input_dir.exists()

        connectors = [
            {
                "conector": "postgresql",
                "tipo": "dataMAIN",
                "estado": "Configurado" if postgres_ready else "Pendiente",
                "detalle": (
                    f"host={os.getenv('POSTGRES_HOST', 'N/A')};db={os.getenv('POSTGRES_DB', 'N/A')}"
                    if postgres_ready
                    else "configurar POSTGRES_HOST y POSTGRES_DB"
                ),
            },
            {
                "conector": "mysql",
                "tipo": "dataMAIN",
                "estado": "Configurado" if mysql_ready else "Pendiente",
                "detalle": (
                    f"host={os.getenv('MYSQL_HOST', 'N/A')};db={os.getenv('MYSQL_DB', 'N/A')}"
                    if mysql_ready
                    else "configurar MYSQL_HOST y MYSQL_DB"
                ),
            },
            {
                "conector": "api_rest",
                "tipo": "api",
                "estado": "Configurado" if api_ready else "Pendiente",
                "detalle": (
                    f"MAIN={os.getenv('EXTERNAL_API_MAIN_URL', os.getenv('DJANGO_MAIN_URL', 'N/A'))}"
                    if api_ready
                    else "configurar EXTERNAL_API_MAIN_URL"
                ),
            },
            {
                "conector": "sftp",
                "tipo": "file_transfer",
                "estado": "Configurado" if sftp_ready else "Pendiente",
                "detalle": (
                    f"host={os.getenv('SFTP_HOST', 'N/A')};user={os.getenv('SFTP_USER', 'N/A')}"
                    if sftp_ready
                    else "configurar SFTP_HOST y SFTP_USER"
                ),
            },
            {
                "conector": "archivos",
                "tipo": "file",
                "estado": "Configurado" if files_ready else "Pendiente",
                "detalle": f"input_dir={input_dir}",
            },
        ]

        manifest_payload = {
            "generated_at": ts,
            "summary": {
                "total": len(connectors),
                "configurados": sum(1 for row in connectors if row["estado"] == "Configurado"),
                "pendientes": sum(1 for row in connectors if row["estado"] != "Configurado"),
            },
            "connectors": connectors,
        }

        manifest_json.parent.mkdir(parents=True, exist_ok=True)
        manifest_json.write_text(json.dumps(manifest_payload, ensure_ascii=True, indent=2), encoding="utf-8")

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["conector", "tipo", "estado", "detalle"])
            writer.writeheader()
            writer.writerows(connectors)

        lines = [
            "# Data Intake 1.1 - Etapa 2 de 4: Conectores por Fuente",
            "",
            f"Fecha ejecucion UTC: {ts}",
            "",
            "## Cobertura",
            "- PostgreSQL/MySQL (MAINs de datos).",
            "- API REST (servicios internos/externos).",
            "- SFTP (transferencia de archivos).",
            "- Archivos locales (CSV/Excel/PDF).",
            "",
            "## Resumen",
            f"- Conectores evaluados: {manifest_payload['summary']['total']}",
            f"- Configurados: {manifest_payload['summary']['configurados']}",
            f"- Pendientes: {manifest_payload['summary']['pendientes']}",
            "",
            "| Conector | Tipo | Estado | Detalle |",
            "|---|---|---|---|",
        ]
        for row in connectors:
            lines.append(f"| {row['conector']} | {row['tipo']} | {row['estado']} | {row['detalle']} |")
        lines.extend(
            [
                "",
                "## Estado",
                "- Etapa 2 de 4 completada tecnicamente.",
                "- Diagnostico MAIN de conectores generado.",
                "",
                "## Artefactos",
                f"- Reporte CSV: `{report_csv}`",
                f"- Manifest JSON: `{manifest_json}`",
                "",
            ]
        )
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[ingesta_conectores_fuentes_1_1] diagnostico generado"))
        self.stdout.write(
            f"conectores={manifest_payload['summary']['total']} configurados={manifest_payload['summary']['configurados']}"
        )
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")
        self.stdout.write(f"manifest_json={manifest_json}")

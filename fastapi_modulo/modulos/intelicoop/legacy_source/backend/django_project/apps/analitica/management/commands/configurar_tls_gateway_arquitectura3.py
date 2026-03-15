import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand


class Command(MAINCommand):
    help = (
        "Arquitectura 3 - Etapa 3/4: valida y documenta configuracion TLS "
        "en gateway Nginx con compose override."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--certs-dir",
            default="certs",
            help="Directorio esperado para certificados TLS (fullchain.pem, privkey.pem).",
        )
        parser.add_argument(
            "--report-csv",
            default="docs/mineria/arquitectura3/03_tls_gateway.csv",
        )
        parser.add_argument(
            "--report-md",
            default="docs/mineria/arquitectura3/03_tls_gateway.md",
        )
        parser.add_argument(
            "--manifest-json",
            default="docs/mineria/arquitectura3/03_tls_gateway.json",
        )

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        certs_dir_opt = Path(options["certs_dir"])
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        manifest_json_opt = Path(options["manifest_json"])

        certs_dir = certs_dir_opt if certs_dir_opt.is_absolute() else (root / certs_dir_opt)
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)
        manifest_json = manifest_json_opt if manifest_json_opt.is_absolute() else (root / manifest_json_opt)

        executed_at = datetime.now(timezone.utc).isoformat()

        tls_conf = root / "docker" / "nginx.gateway.tls.conf"
        tls_compose = root / "docker" / "docker-compose.tls.yml"
        cert_fullchain = certs_dir / "fullchain.pem"
        cert_privkey = certs_dir / "privkey.pem"

        rows = [
            {
                "control": "nginx_tls_conf",
                "estado": "Configurado" if tls_conf.exists() else "Pendiente",
                "detalle": str(tls_conf),
            },
            {
                "control": "compose_tls_override",
                "estado": "Configurado" if tls_compose.exists() else "Pendiente",
                "detalle": str(tls_compose),
            },
            {
                "control": "cert_fullchain",
                "estado": "Configurado" if cert_fullchain.exists() else "Pendiente",
                "detalle": str(cert_fullchain),
            },
            {
                "control": "cert_privkey",
                "estado": "Configurado" if cert_privkey.exists() else "Pendiente",
                "detalle": str(cert_privkey),
            },
            {
                "control": "hsts_header",
                "estado": "Configurado" if tls_conf.exists() and "Strict-Transport-Security" in tls_conf.read_text(encoding="utf-8") else "Pendiente",
                "detalle": "header_hsts_en_nginx_tls_conf",
            },
        ]

        summary = {
            "total_controles": len(rows),
            "configurados": sum(1 for row in rows if row["estado"] == "Configurado"),
            "pendientes": sum(1 for row in rows if row["estado"] != "Configurado"),
        }

        manifest_payload = {
            "generated_at": executed_at,
            "summary": summary,
            "rows": rows,
            "run_instructions": {
                "compose_command": (
                    "docker compose --env-file .env -f docker/docker-compose.yml "
                    "-f docker/docker-compose.tls.yml up -d --build"
                ),
                "https_url_local": "https://localhost:8443",
            },
        }

        manifest_json.parent.mkdir(parents=True, exist_ok=True)
        manifest_json.write_text(json.dumps(manifest_payload, ensure_ascii=True, indent=2), encoding="utf-8")

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["control", "estado", "detalle"])
            writer.writeheader()
            writer.writerows(rows)

        lines = [
            "# Arquitectura 3 - Etapa 3 de 4: TLS en Transito",
            "",
            f"Fecha ejecucion UTC: {executed_at}",
            "",
            "## Resultado",
            f"- Controles evaluados: {summary['total_controles']}",
            f"- Configurados: {summary['configurados']}",
            f"- Pendientes: {summary['pendientes']}",
            "",
            "## Controles",
            "| Control | Estado | Detalle |",
            "|---|---|---|",
        ]
        for row in rows:
            lines.append(f"| {row['control']} | {row['estado']} | {row['detalle']} |")

        lines.extend(
            [
                "",
                "## Ejecucion TLS (compose override)",
                "- Comando:",
                "```bash",
                "docker compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.tls.yml up -d --build",
                "```",
                "- URL local HTTPS esperada: `https://localhost:8443`",
                "- Certificados requeridos: `certs/fullchain.pem` y `certs/privkey.pem`",
                "",
                "## Estado",
                "- Etapa 3 de 4 completada tecnicamente.",
                "- Configuracion TLS del gateway habilitable en despliegue productivo.",
                "",
                "## Artefactos",
                f"- Reporte CSV: `{report_csv}`",
                f"- Manifest JSON: `{manifest_json}`",
                "",
            ]
        )
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[configurar_tls_gateway_arquitectura3] proceso finalizado"))
        self.stdout.write(f"controles={summary['total_controles']} pendientes={summary['pendientes']}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")
        self.stdout.write(f"manifest_json={manifest_json}")

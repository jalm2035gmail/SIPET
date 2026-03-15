import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand
from django.db import connections


class Command(MAINCommand):
    help = (
        "Arquitectura 3 - Etapa 1/4: crea esquemas raw/clean/analytics en PostgreSQL "
        "y genera reporte de estado."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--schemas",
            default="raw,clean,analytics",
            help="Lista de esquemas separados por coma.",
        )
        parser.add_argument(
            "--db-alias",
            default="default",
            help="Alias de MAIN de datos en Django settings.",
        )
        parser.add_argument(
            "--report-csv",
            default="docs/mineria/arquitectura3/01_data_layer_schemas.csv",
        )
        parser.add_argument(
            "--report-md",
            default="docs/mineria/arquitectura3/01_data_layer_schemas.md",
        )
        parser.add_argument(
            "--manifest-json",
            default="docs/mineria/arquitectura3/01_data_layer_schemas.json",
        )

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        manifest_json_opt = Path(options["manifest_json"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)
        manifest_json = manifest_json_opt if manifest_json_opt.is_absolute() else (root / manifest_json_opt)

        db_alias = options["db_alias"]
        connection = connections[db_alias]
        vendor = connection.vendor
        executed_at = datetime.now(timezone.utc).isoformat()

        raw_schemas = [item.strip().lower() for item in str(options["schemas"]).split(",")]
        schemas = [item for item in raw_schemas if item]
        if not schemas:
            schemas = ["raw", "clean", "analytics"]

        rows = []
        created_count = 0
        skipped_count = 0

        if vendor != "postgresql":
            for schema_name in schemas:
                rows.append(
                    {
                        "schema": schema_name,
                        "db_alias": db_alias,
                        "db_vendor": vendor,
                        "estado": "Pendiente",
                        "detalle": "requiere_postgresql",
                        "fecha_ejecucion_utc": executed_at,
                    }
                )
                skipped_count += 1
        else:
            with connection.cursor() as cursor:
                for schema_name in schemas:
                    # SQL identifier is controlled (only [a-z0-9_]) to avoid injection.
                    safe = "".join(ch for ch in schema_name if ch.isalnum() or ch == "_")
                    if safe != schema_name or not safe:
                        rows.append(
                            {
                                "schema": schema_name,
                                "db_alias": db_alias,
                                "db_vendor": vendor,
                                "estado": "Error",
                                "detalle": "schema_invalido",
                                "fecha_ejecucion_utc": executed_at,
                            }
                        )
                        skipped_count += 1
                        continue

                    cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{safe}"')
                    rows.append(
                        {
                            "schema": safe,
                            "db_alias": db_alias,
                            "db_vendor": vendor,
                            "estado": "Configurado",
                            "detalle": "create_schema_if_not_exists_ok",
                            "fecha_ejecucion_utc": executed_at,
                        }
                    )
                    created_count += 1

        summary = {
            "total": len(rows),
            "configurados": created_count,
            "pendientes_o_omitidos": skipped_count,
        }

        manifest_payload = {
            "generated_at": executed_at,
            "dataMAIN": {"alias": db_alias, "vendor": vendor},
            "summary": summary,
            "rows": rows,
        }

        manifest_json.parent.mkdir(parents=True, exist_ok=True)
        manifest_json.write_text(json.dumps(manifest_payload, ensure_ascii=True, indent=2), encoding="utf-8")

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["schema", "db_alias", "db_vendor", "estado", "detalle", "fecha_ejecucion_utc"],
            )
            writer.writeheader()
            writer.writerows(rows)

        lines = [
            "# Arquitectura 3 - Etapa 1 de 4: Data Layer (Esquemas PostgreSQL)",
            "",
            f"Fecha ejecucion UTC: {executed_at}",
            f"DB alias: {db_alias}",
            f"DB vendor: {vendor}",
            "",
            "## Objetivo",
            "- Preparar separacion de capas de datos: raw / clean / analytics.",
            "",
            "## Resultado",
            f"- Esquemas solicitados: {len(schemas)}",
            f"- Configurados: {created_count}",
            f"- Pendientes/Omitidos: {skipped_count}",
            "",
            "| Schema | Estado | Detalle |",
            "|---|---|---|",
        ]
        for row in rows:
            lines.append(f"| {row['schema']} | {row['estado']} | {row['detalle']} |")

        lines.extend(
            [
                "",
                "## Estado",
                "- Etapa 1 de 4 completada tecnicamente.",
                "- MAIN de Data Layer preparada para separar ingestas crudas, limpieza y analitica.",
                "",
                "## Artefactos",
                f"- Reporte CSV: `{report_csv}`",
                f"- Manifest JSON: `{manifest_json}`",
                "",
            ]
        )
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[configurar_esquemas_data_layer_arquitectura3] proceso finalizado"))
        self.stdout.write(
            f"db_vendor={vendor} schemas_total={summary['total']} configurados={summary['configurados']}"
        )
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")
        self.stdout.write(f"manifest_json={manifest_json}")

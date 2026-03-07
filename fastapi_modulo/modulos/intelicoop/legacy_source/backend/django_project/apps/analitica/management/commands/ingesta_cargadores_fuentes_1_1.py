import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand


SOURCE_SPECS = {
    "socios": {
        "filename": "socios.csv",
        "required_fields": ["id_socio", "nombre", "email"],
    },
    "creditos": {
        "filename": "creditos.csv",
        "required_fields": ["id_credito", "id_socio", "monto"],
    },
    "captacion": {
        "filename": "captacion.csv",
        "required_fields": ["id_movimiento", "id_socio", "tipo", "monto", "fecha"],
    },
    "cobranza": {
        "filename": "cobranza.csv",
        "required_fields": ["id_gestion", "id_credito", "estado", "fecha"],
    },
    "contabilidad": {
        "filename": "contabilidad.csv",
        "required_fields": ["id_asiento", "cuenta", "monto", "fecha"],
    },
}


class Command(BaseCommand):
    help = "Etapa 1/4 de Data Intake: cargadores por fuente para socios, creditos, captacion, cobranza y contabilidad."

    def add_arguments(self, parser):
        parser.add_argument(
            "--input-dir",
            default=".run/mineria/intake/incoming",
            help="Directorio con archivos CSV por fuente.",
        )
        parser.add_argument(
            "--raw-dir",
            default=".run/mineria/intake/raw",
            help="Directorio de salida para datos crudos normalizados.",
        )
        parser.add_argument(
            "--report-csv",
            default="docs/mineria/intake/01_cargadores_fuentes.csv",
        )
        parser.add_argument(
            "--report-md",
            default="docs/mineria/intake/01_cargadores_fuentes.md",
        )
        parser.add_argument(
            "--actor",
            default="sistema_ingesta",
            help="Actor responsable de la carga (usuario/proceso).",
        )
        parser.add_argument(
            "--dataset-version",
            default="intake_v1",
            help="Version logica del dataset cargado.",
        )

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]

        input_dir_opt = Path(options["input_dir"])
        raw_dir_opt = Path(options["raw_dir"])
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])

        input_dir = input_dir_opt if input_dir_opt.is_absolute() else (root / input_dir_opt)
        raw_dir = raw_dir_opt if raw_dir_opt.is_absolute() else (root / raw_dir_opt)
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        actor = str(options["actor"]).strip() or "sistema_ingesta"
        dataset_version = str(options["dataset_version"]).strip() or "intake_v1"
        executed_at = datetime.now(timezone.utc).isoformat()

        rows = []
        total_records = 0
        raw_dir.mkdir(parents=True, exist_ok=True)

        for source_name, spec in SOURCE_SPECS.items():
            source_file = input_dir / spec["filename"]
            raw_output = raw_dir / f"{source_name}.jsonl"
            required_fields = spec["required_fields"]

            if not source_file.exists():
                rows.append(
                    {
                        "fuente": source_name,
                        "archivo_entrada": str(source_file),
                        "archivo_raw": str(raw_output),
                        "registros": "0",
                        "estado": "Sin archivo",
                        "detalle": "archivo_no_encontrado",
                        "actor": actor,
                        "dataset_version": dataset_version,
                        "fecha_ejecucion_utc": executed_at,
                    }
                )
                continue

            records = []
            with source_file.open("r", encoding="utf-8", newline="") as file:
                reader = csv.DictReader(file)
                source_fields = reader.fieldnames or []
                missing = [field for field in required_fields if field not in source_fields]
                if missing:
                    rows.append(
                        {
                            "fuente": source_name,
                            "archivo_entrada": str(source_file),
                            "archivo_raw": str(raw_output),
                            "registros": "0",
                            "estado": "Error",
                            "detalle": f"faltan_campos:{','.join(missing)}",
                            "actor": actor,
                            "dataset_version": dataset_version,
                            "fecha_ejecucion_utc": executed_at,
                        }
                    )
                    continue

                for index, row in enumerate(reader, start=1):
                    record = {
                        "source": source_name,
                        "row_num": index,
                        "loaded_at": executed_at,
                        "dataset_version": dataset_version,
                        "actor": actor,
                        "data": row,
                    }
                    records.append(record)

            with raw_output.open("w", encoding="utf-8") as file:
                for record in records:
                    file.write(json.dumps(record, ensure_ascii=True) + "\n")

            total_records += len(records)
            rows.append(
                {
                    "fuente": source_name,
                    "archivo_entrada": str(source_file),
                    "archivo_raw": str(raw_output),
                    "registros": str(len(records)),
                    "estado": "Cargado",
                    "detalle": "ok",
                    "actor": actor,
                    "dataset_version": dataset_version,
                    "fecha_ejecucion_utc": executed_at,
                }
            )

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "fuente",
                    "archivo_entrada",
                    "archivo_raw",
                    "registros",
                    "estado",
                    "detalle",
                    "actor",
                    "dataset_version",
                    "fecha_ejecucion_utc",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

        lines = [
            "# Data Intake 1.1 - Etapa 1 de 4: Cargadores por Fuente",
            "",
            f"Fecha ejecucion UTC: {executed_at}",
            f"Actor: {actor}",
            f"Dataset version: {dataset_version}",
            "",
            "## Fuentes evaluadas",
            f"- Total fuentes: {len(SOURCE_SPECS)}",
            f"- Total registros cargados: {total_records}",
            "",
            "| Fuente | Estado | Registros | Detalle |",
            "|---|---|---:|---|",
        ]
        for row in rows:
            lines.append(f"| {row['fuente']} | {row['estado']} | {row['registros']} | {row['detalle']} |")
        lines.extend(
            [
                "",
                "## Estado",
                "- Etapa 1 de 4 completada tecnicamente.",
                "- Cargadores base por fuente implementados con salida raw.",
                "",
                "## Artefactos",
                f"- Reporte CSV: `{report_csv}`",
                f"- Directorio raw: `{raw_dir}`",
                "",
            ]
        )
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[ingesta_cargadores_fuentes_1_1] carga finalizada"))
        self.stdout.write(f"fuentes={len(SOURCE_SPECS)} registros={total_records}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")

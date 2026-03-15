import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand


SOURCES = ["socios", "creditos", "captacion", "cobranza", "contabilidad"]


def _normalize_record(source: str, data: dict) -> dict:
    out = {str(k).strip(): ("" if v is None else str(v).strip()) for k, v in data.items()}

    if source == "socios":
        if "email" in out:
            out["email"] = out["email"].lower()
    if "monto" in out:
        raw_monto = out["monto"].replace(",", ".")
        try:
            out["monto"] = f"{float(raw_monto):.2f}"
        except ValueError:
            pass
    if "tipo" in out:
        out["tipo"] = out["tipo"].lower()
    if "estado" in out:
        out["estado"] = out["estado"].lower()
    return out


class Command(MAINCommand):
    help = "Etapa 4/4 de Data Intake: auditoria de cargas y salida estandarizada (raw -> standardized)."

    def add_arguments(self, parser):
        parser.add_argument("--raw-dir", default=".run/mineria/intake/raw")
        parser.add_argument("--std-dir", default=".run/mineria/intake/standardized")
        parser.add_argument("--audit-jsonl", default=".run/mineria/intake/audit_registry.jsonl")
        parser.add_argument("--report-csv", default="docs/mineria/intake/04_auditoria_salida_estandarizada.csv")
        parser.add_argument("--report-md", default="docs/mineria/intake/04_auditoria_salida_estandarizada.md")
        parser.add_argument("--actor", default="sistema_ingesta")
        parser.add_argument("--dataset-version", default="intake_v1")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        raw_dir_opt = Path(options["raw_dir"])
        std_dir_opt = Path(options["std_dir"])
        audit_jsonl_opt = Path(options["audit_jsonl"])
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])

        raw_dir = raw_dir_opt if raw_dir_opt.is_absolute() else (root / raw_dir_opt)
        std_dir = std_dir_opt if std_dir_opt.is_absolute() else (root / std_dir_opt)
        audit_jsonl = audit_jsonl_opt if audit_jsonl_opt.is_absolute() else (root / audit_jsonl_opt)
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        actor = str(options["actor"]).strip() or "sistema_ingesta"
        dataset_version = str(options["dataset_version"]).strip() or "intake_v1"
        executed_at = datetime.now(timezone.utc).isoformat()

        std_dir.mkdir(parents=True, exist_ok=True)
        audit_jsonl.parent.mkdir(parents=True, exist_ok=True)

        rows = []
        audit_events = []
        total_raw = 0
        total_std = 0

        for source in SOURCES:
            raw_path = raw_dir / f"{source}.jsonl"
            std_path = std_dir / f"{source}.jsonl"

            raw_records = []
            if raw_path.exists():
                with raw_path.open("r", encoding="utf-8") as file:
                    for line in file:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            payload = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        data = payload.get("data", {})
                        if isinstance(data, dict):
                            raw_records.append(data)

            std_records = [_normalize_record(source, record) for record in raw_records]
            with std_path.open("w", encoding="utf-8") as file:
                for idx, record in enumerate(std_records, start=1):
                    envelope = {
                        "source": source,
                        "row_num": idx,
                        "standardized_at": executed_at,
                        "actor": actor,
                        "dataset_version": dataset_version,
                        "data": record,
                    }
                    file.write(json.dumps(envelope, ensure_ascii=True) + "\n")

            status = "Procesado" if raw_records else "Sin datos"
            audit_event = {
                "event_id": f"{source}_{executed_at}",
                "source": source,
                "actor": actor,
                "executed_at": executed_at,
                "dataset_version": dataset_version,
                "raw_path": str(raw_path),
                "standardized_path": str(std_path),
                "raw_records": len(raw_records),
                "standardized_records": len(std_records),
                "status": status,
            }
            audit_events.append(audit_event)

            total_raw += len(raw_records)
            total_std += len(std_records)

            rows.append(
                {
                    "fuente": source,
                    "raw_path": str(raw_path),
                    "standardized_path": str(std_path),
                    "raw_records": str(len(raw_records)),
                    "standardized_records": str(len(std_records)),
                    "estado": status,
                    "actor": actor,
                    "dataset_version": dataset_version,
                    "fecha_ejecucion_utc": executed_at,
                }
            )

        with audit_jsonl.open("a", encoding="utf-8") as file:
            for event in audit_events:
                file.write(json.dumps(event, ensure_ascii=True) + "\n")

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "fuente",
                    "raw_path",
                    "standardized_path",
                    "raw_records",
                    "standardized_records",
                    "estado",
                    "actor",
                    "dataset_version",
                    "fecha_ejecucion_utc",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

        lines = [
            "# Data Intake 1.1 - Etapa 4 de 4: Auditoria y Salida Estandarizada",
            "",
            f"Fecha ejecucion UTC: {executed_at}",
            f"Actor: {actor}",
            f"Dataset version: {dataset_version}",
            "",
            "## Resultado de transformacion",
            f"- Registros raw leidos: {total_raw}",
            f"- Registros estandarizados: {total_std}",
            f"- Bitacora auditoria: `{audit_jsonl}`",
            "",
            "| Fuente | Estado | Raw | Standardized |",
            "|---|---|---:|---:|",
        ]
        for row in rows:
            lines.append(
                f"| {row['fuente']} | {row['estado']} | {row['raw_records']} | {row['standardized_records']} |"
            )
        lines.extend(
            [
                "",
                "## Estado",
                "- Etapa 4 de 4 completada tecnicamente.",
                "- Registro de auditoria y salida standardized implementados.",
                "",
                "## Artefactos",
                f"- Reporte CSV: `{report_csv}`",
                f"- Directorio standardized: `{std_dir}`",
                "",
            ]
        )
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[ingesta_auditoria_salida_1_1] etapa finalizada"))
        self.stdout.write(f"raw={total_raw} standardized={total_std}")
        self.stdout.write(f"audit_jsonl={audit_jsonl}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")

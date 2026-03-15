import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand


SOURCE_RULES = {
    "socios": {"id_field": "id_socio", "required": ["id_socio", "nombre", "email"]},
    "creditos": {"id_field": "id_credito", "required": ["id_credito", "id_socio", "monto"]},
    "captacion": {"id_field": "id_movimiento", "required": ["id_movimiento", "id_socio", "tipo", "monto", "fecha"]},
    "cobranza": {"id_field": "id_gestion", "required": ["id_gestion", "id_credito", "estado", "fecha"]},
    "contabilidad": {"id_field": "id_asiento", "required": ["id_asiento", "cuenta", "monto", "fecha"]},
}


def _is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _is_date_yyyy_mm_dd(value: str) -> bool:
    if not isinstance(value, str) or len(value) != 10:
        return False
    return value[4] == "-" and value[7] == "-" and value.replace("-", "").isdigit()


class Command(MAINCommand):
    help = "Etapa 3/4 de Data Intake: validaciones de duplicados, obligatorios, formatos y consistencia."

    def add_arguments(self, parser):
        parser.add_argument("--raw-dir", default=".run/mineria/intake/raw")
        parser.add_argument("--report-csv", default="docs/mineria/intake/03_validaciones_intake.csv")
        parser.add_argument("--report-md", default="docs/mineria/intake/03_validaciones_intake.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        raw_dir_opt = Path(options["raw_dir"])
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        raw_dir = raw_dir_opt if raw_dir_opt.is_absolute() else (root / raw_dir_opt)
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        executed_at = datetime.now(timezone.utc).isoformat()
        rows = []
        issues_total = 0
        records_total = 0

        for source, rule in SOURCE_RULES.items():
            path = raw_dir / f"{source}.jsonl"
            if not path.exists():
                rows.append(
                    {
                        "fuente": source,
                        "registros": "0",
                        "duplicados": "0",
                        "obligatorios_invalidos": "0",
                        "formato_invalidos": "0",
                        "consistencia_invalidos": "0",
                        "estado": "Sin datos",
                        "detalle": "archivo_raw_no_encontrado",
                    }
                )
                continue

            records = []
            with path.open("r", encoding="utf-8") as file:
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
                        records.append(data)

            duplicates = 0
            required_invalid = 0
            format_invalid = 0
            consistency_invalid = 0

            seen = set()
            id_field = rule["id_field"]
            for record in records:
                record_id = str(record.get(id_field, "")).strip()
                if record_id in seen and record_id:
                    duplicates += 1
                if record_id:
                    seen.add(record_id)

                for field in rule["required"]:
                    value = str(record.get(field, "")).strip()
                    if not value:
                        required_invalid += 1
                        break

                if source == "socios":
                    email = str(record.get("email", "")).strip()
                    if "@" not in email:
                        format_invalid += 1
                if source in {"creditos", "captacion", "contabilidad"}:
                    monto = str(record.get("monto", "")).strip()
                    if monto and (not _is_number(monto) or float(monto) < 0):
                        format_invalid += 1
                if source in {"captacion", "cobranza", "contabilidad"}:
                    fecha = str(record.get("fecha", "")).strip()
                    if fecha and not _is_date_yyyy_mm_dd(fecha):
                        format_invalid += 1

                if source == "creditos":
                    id_socio = str(record.get("id_socio", "")).strip()
                    if record_id and id_socio and record_id == id_socio:
                        consistency_invalid += 1

            source_issues = duplicates + required_invalid + format_invalid + consistency_invalid
            issues_total += source_issues
            records_total += len(records)

            rows.append(
                {
                    "fuente": source,
                    "registros": str(len(records)),
                    "duplicados": str(duplicates),
                    "obligatorios_invalidos": str(required_invalid),
                    "formato_invalidos": str(format_invalid),
                    "consistencia_invalidos": str(consistency_invalid),
                    "estado": "Cumple" if source_issues == 0 else "En revision",
                    "detalle": f"issues={source_issues}",
                }
            )

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "fuente",
                    "registros",
                    "duplicados",
                    "obligatorios_invalidos",
                    "formato_invalidos",
                    "consistencia_invalidos",
                    "estado",
                    "detalle",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

        lines = [
            "# Data Intake 1.1 - Etapa 3 de 4: Validaciones de Calidad",
            "",
            f"Fecha ejecucion UTC: {executed_at}",
            "",
            "## Validaciones ejecutadas",
            "- Duplicados por ID de negocio.",
            "- Campos obligatorios por fuente.",
            "- Formatos (email, fecha, montos).",
            "- Consistencia basica entre campos.",
            "",
            "## Resumen",
            f"- Registros evaluados: {records_total}",
            f"- Issues totales: {issues_total}",
            "",
            "| Fuente | Estado | Registros | Duplicados | Obligatorios invalidos | Formato invalidos | Consistencia invalidos |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
        for row in rows:
            lines.append(
                f"| {row['fuente']} | {row['estado']} | {row['registros']} | {row['duplicados']} | {row['obligatorios_invalidos']} | {row['formato_invalidos']} | {row['consistencia_invalidos']} |"
            )
        lines.extend(
            [
                "",
                "## Estado",
                "- Etapa 3 de 4 completada tecnicamente.",
                "- Validaciones de calidad de intake ejecutadas con evidencia reproducible.",
                "",
                "## Artefactos",
                f"- Reporte CSV: `{report_csv}`",
                "",
            ]
        )
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[ingesta_validaciones_1_1] validaciones generadas"))
        self.stdout.write(f"registros={records_total} issues={issues_total}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")

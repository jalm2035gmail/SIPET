import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pick_latest(directory: Path, pattern: str) -> Path | None:
    files = sorted(directory.glob(pattern))
    if not files:
        return None
    return files[-1]


class Command(MAINCommand):
    help = "Registra lineage de carga analitica (origen->transformacion->salida) con versionado."

    def add_arguments(self, parser):
        parser.add_argument("--source-tag", default="django_db", help="Origen principal de datos.")
        parser.add_argument("--dataset-version", default="ds_20260218_v1", help="Version del dataset.")
        parser.add_argument("--feature-set-version", default="fs_20260218_v1", help="Version del feature set.")
        parser.add_argument("--model-version", default="na_fase2", help="Version de modelo asociada.")
        parser.add_argument(
            "--registry-jsonl",
            default=".run/mineria/lineage_registry.jsonl",
            help="Archivo acumulado de registros lineage.",
        )
        parser.add_argument(
            "--output-csv",
            default="docs/mineria/fase2/16_lineage_cargas.csv",
            help="Reporte CSV de la corrida actual.",
        )
        parser.add_argument(
            "--output-md",
            default="docs/mineria/fase2/16_lineage_cargas.md",
            help="Reporte Markdown de la corrida actual.",
        )

    def handle(self, *args, **options):
        run_time = datetime.now(timezone.utc).isoformat()
        run_id = datetime.now(timezone.utc).strftime("lineage_%Y%m%dT%H%M%SZ")

        source_tag = options["source_tag"]
        dataset_version = options["dataset_version"]
        feature_set_version = options["feature_set_version"]
        model_version = options["model_version"]

        registry_jsonl = Path(options["registry_jsonl"]).resolve()
        output_csv = Path(options["output_csv"]).resolve()
        output_md = Path(options["output_md"]).resolve()

        mineria_dir = Path(".run/mineria").resolve()
        fase2_dir = Path("docs/mineria/fase2").resolve()

        artifacts = []
        candidates = [
            _pick_latest(mineria_dir, "perfilamiento_calidad_*.json"),
            _pick_latest(mineria_dir, "diccionario_datos_*.json"),
            fase2_dir / "12_reporte_calidad_datos.md",
            fase2_dir / "13_plan_remediacion_calidad.csv",
            fase2_dir / "14_homologacion_catalogos.csv",
            fase2_dir / "15_validacion_datos.csv",
        ]
        for path in candidates:
            if path and path.exists():
                artifacts.append(
                    {
                        "run_id": run_id,
                        "fecha_carga": run_time,
                        "source_tag": source_tag,
                        "dataset_version": dataset_version,
                        "feature_set_version": feature_set_version,
                        "model_version": model_version,
                        "artifact_path": str(path),
                        "artifact_sha256": _sha256(path),
                    }
                )

        registry_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with registry_jsonl.open("a", encoding="utf-8") as file:
            for row in artifacts:
                file.write(json.dumps(row, ensure_ascii=False) + "\n")

        output_csv.parent.mkdir(parents=True, exist_ok=True)
        with output_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "run_id",
                    "fecha_carga",
                    "source_tag",
                    "dataset_version",
                    "feature_set_version",
                    "model_version",
                    "artifact_path",
                    "artifact_sha256",
                ],
            )
            writer.writeheader()
            writer.writerows(artifacts)

        md_lines = [
            "# Lineage de Cargas - Fase 2",
            "",
            f"Run ID: `{run_id}`",
            f"Fecha: {run_time}",
            f"Source tag: `{source_tag}`",
            f"Dataset version: `{dataset_version}`",
            f"Feature set version: `{feature_set_version}`",
            f"Model version: `{model_version}`",
            "",
            "## Artefactos registrados",
            "",
            "| Artifact path | SHA256 |",
            "|---|---|",
        ]
        for item in artifacts:
            md_lines.append(f"| `{item['artifact_path']}` | `{item['artifact_sha256']}` |")
        md_lines.extend(
            [
                "",
                "## Estado para checklist Fase 2 (Punto 6 de 8)",
                "- Estado sugerido: `En revision`.",
                "- Cierre requerido: adoptar este registro en corrida productiva recurrente.",
                "",
            ]
        )
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text("\n".join(md_lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[registrar_lineage_carga] lineage registrado"))
        self.stdout.write(f"Run ID: {run_id}")
        self.stdout.write(f"Registros: {len(artifacts)}")
        self.stdout.write(f"Registry: {registry_jsonl}")
        self.stdout.write(f"CSV: {output_csv}")
        self.stdout.write(f"MD: {output_md}")

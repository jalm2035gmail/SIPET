import csv
import pickle
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand

from .entrenar_scoring_mvp import (
    _accuracy,
    _auc,
    _balance,
    _brier_score,
    _build_samples_from_db,
    _build_synthetic_samples,
    _split,
)


def _deuda_ratio(sample) -> float:
    return float(sample.deuda) / max(float(sample.ingreso), 1.0)


def _segmentos(samples: list) -> list[tuple[str, str, list]]:
    ingreso_bajo = [s for s in samples if float(s.ingreso) <= 3000.0]
    ingreso_medio = [s for s in samples if 3000.0 < float(s.ingreso) <= 7000.0]
    ingreso_alto = [s for s in samples if float(s.ingreso) > 7000.0]

    antig_baja = [s for s in samples if int(s.antiguedad) <= 12]
    antig_media = [s for s in samples if 12 < int(s.antiguedad) <= 36]
    antig_alta = [s for s in samples if int(s.antiguedad) > 36]

    ratio_bajo = [s for s in samples if _deuda_ratio(s) <= 0.30]
    ratio_medio = [s for s in samples if 0.30 < _deuda_ratio(s) <= 0.60]
    ratio_alto = [s for s in samples if _deuda_ratio(s) > 0.60]

    return [
        ("ingreso", "<=3000", ingreso_bajo),
        ("ingreso", "3000-7000", ingreso_medio),
        ("ingreso", ">7000", ingreso_alto),
        ("antiguedad", "<=12m", antig_baja),
        ("antiguedad", "13-36m", antig_media),
        ("antiguedad", ">36m", antig_alta),
        ("deuda_ratio", "<=0.30", ratio_bajo),
        ("deuda_ratio", "0.31-0.60", ratio_medio),
        ("deuda_ratio", ">0.60", ratio_alto),
    ]


class Command(MAINCommand):
    help = "Evalua el scoring MVP por segmentos y documenta seleccion de modelo."

    def add_arguments(self, parser):
        parser.add_argument("--window-days", type=int, default=3650)
        parser.add_argument("--min-samples", type=int, default=80)
        parser.add_argument("--synthetic-size", type=int, default=300)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument(
            "--report-csv",
            default="docs/mineria/fase3/04_evaluacion_seleccion_modelo.csv",
        )
        parser.add_argument(
            "--report-md",
            default="docs/mineria/fase3/04_evaluacion_seleccion_modelo.md",
        )

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        model_path = root / "backend" / "fastapi_service" / "app" / "core" / "modelo_scoring.pkl"
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        seed = int(options["seed"])
        min_samples = int(options["min_samples"])
        db_samples = _build_samples_from_db(int(options["window_days"]))
        source = "db"
        samples = db_samples
        if len(samples) < min_samples:
            source = "synthetic"
            samples = _build_synthetic_samples(int(options["synthetic_size"]), seed)

        samples = _balance(samples, seed=seed)
        _train, valid = _split(samples, seed=seed)

        benchmark = {
            "max_antiguedad": 120.0,
            "peso_disponibilidad": 0.70,
            "peso_antiguedad": 0.30,
            "bias": 0.0,
        }
        deployed = dict(benchmark)
        if model_path.exists():
            with model_path.open("rb") as file:
                artifact = pickle.load(file)
            deployed = dict(artifact.get("params") or benchmark)

        global_deployed = {
            "brier": _brier_score(valid, deployed),
            "acc": _accuracy(valid, deployed),
            "auc": _auc(valid, deployed),
        }
        global_benchmark = {
            "brier": _brier_score(valid, benchmark),
            "acc": _accuracy(valid, benchmark),
            "auc": _auc(valid, benchmark),
        }

        min_segment_samples = 10
        max_brier_drift = 0.12
        rows = []
        eligible = 0
        stable = 0

        for dimension, segmento, seg_samples in _segmentos(valid):
            n = len(seg_samples)
            if n == 0:
                continue
            dep_brier = _brier_score(seg_samples, deployed)
            ben_brier = _brier_score(seg_samples, benchmark)
            dep_auc = _auc(seg_samples, deployed)
            ben_auc = _auc(seg_samples, benchmark)
            delta_global_brier = dep_brier - global_deployed["brier"]
            es_elegible = n >= min_segment_samples
            es_estable = es_elegible and abs(delta_global_brier) <= max_brier_drift
            if es_elegible:
                eligible += 1
            if es_estable:
                stable += 1
            rows.append(
                {
                    "dimension": dimension,
                    "segmento": segmento,
                    "samples": n,
                    "brier_modelo": f"{dep_brier:.6f}",
                    "brier_benchmark": f"{ben_brier:.6f}",
                    "delta_brier_vs_benchmark": f"{(dep_brier - ben_brier):.6f}",
                    "auc_modelo": f"{dep_auc:.6f}",
                    "auc_benchmark": f"{ben_auc:.6f}",
                    "delta_auc_vs_benchmark": f"{(dep_auc - ben_auc):.6f}",
                    "delta_brier_vs_global": f"{delta_global_brier:.6f}",
                    "elegible_estabilidad": "si" if es_elegible else "no",
                    "estable": "si" if es_estable else "no",
                }
            )

        estabilidad_ok = eligible > 0 and (stable / eligible) >= 0.70
        mejora_global = global_deployed["brier"] <= global_benchmark["brier"]
        decision = "mantener_modelo_desplegado" if (mejora_global and estabilidad_ok) else "ajustar_o_reentrenar"

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "dimension",
                    "segmento",
                    "samples",
                    "brier_modelo",
                    "brier_benchmark",
                    "delta_brier_vs_benchmark",
                    "auc_modelo",
                    "auc_benchmark",
                    "delta_auc_vs_benchmark",
                    "delta_brier_vs_global",
                    "elegible_estabilidad",
                    "estable",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

        lines = [
            "# Evaluacion y Seleccion de Modelo - Punto 3 de 8 (Fase 3)",
            "",
            f"Fecha: {datetime.now(timezone.utc).isoformat()}",
            f"Fuente de datos: `{source}`",
            f"Muestras de validacion: {len(valid)}",
            "",
            "## Metricas globales",
            "",
            f"- Modelo desplegado: brier={global_deployed['brier']:.6f}, acc={global_deployed['acc']:.6f}, auc={global_deployed['auc']:.6f}",
            f"- Benchmark: brier={global_benchmark['brier']:.6f}, acc={global_benchmark['acc']:.6f}, auc={global_benchmark['auc']:.6f}",
            "",
            "## Estabilidad por segmentos",
            "",
            f"- Segmentos elegibles (>= {min_segment_samples} muestras): {eligible}",
            f"- Segmentos estables: {stable}",
            f"- Proporcion estable: {(stable / eligible):.2%}" if eligible else "- Proporcion estable: N/A",
            f"- Umbral estabilidad: abs(delta brier vs global) <= {max_brier_drift:.2f}",
            "",
            "## Decision de seleccion",
            "",
            f"- Mejora global vs benchmark: {'si' if mejora_global else 'no'}",
            f"- Estabilidad suficiente: {'si' if estabilidad_ok else 'no'}",
            f"- Decision: `{decision}`",
            "",
            "## Artefactos",
            f"- Modelo evaluado: `{model_path}`",
            f"- Reporte CSV: `{report_csv}`",
            "",
            "## Estado",
            "- Punto 3 de 8 completado tecnicamente.",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[evaluar_scoring_mvp] evaluacion completada"))
        self.stdout.write(f"source={source} valid={len(valid)}")
        self.stdout.write(f"global_brier_model={global_deployed['brier']:.6f}")
        self.stdout.write(f"global_brier_benchmark={global_benchmark['brier']:.6f}")
        self.stdout.write(f"eligible_segments={eligible} stable_segments={stable}")
        self.stdout.write(f"decision={decision}")
        self.stdout.write(f"report={report_md}")

import csv
import pickle
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand
from django.utils import timezone as django_timezone

from apps.creditos.models import Credito


@dataclass
class Sample:
    ingreso: float
    deuda: float
    antiguedad: int
    y: int


def _clip_01(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def _predict(params: dict, ingreso: float, deuda: float, antiguedad: int) -> float:
    max_antiguedad = float(params.get("max_antiguedad", 120))
    peso_disp = float(params.get("peso_disponibilidad", 0.7))
    peso_ant = float(params.get("peso_antiguedad", 0.3))
    bias = float(params.get("bias", 0.0))

    disponibilidad = max(ingreso - deuda, 0.0) / max(ingreso, 1.0)
    antig_norm = min(float(antiguedad) / max(max_antiguedad, 1.0), 1.0)
    return _clip_01(bias + (peso_disp * disponibilidad) + (peso_ant * antig_norm))


def _brier_score(samples: list[Sample], params: dict) -> float:
    if not samples:
        return 1.0
    err = 0.0
    for s in samples:
        p = _predict(params, s.ingreso, s.deuda, s.antiguedad)
        err += (p - s.y) ** 2
    return err / len(samples)


def _accuracy(samples: list[Sample], params: dict, threshold: float = 0.6) -> float:
    if not samples:
        return 0.0
    ok = 0
    for s in samples:
        p = _predict(params, s.ingreso, s.deuda, s.antiguedad)
        pred = 1 if p >= threshold else 0
        if pred == s.y:
            ok += 1
    return ok / len(samples)


def _auc(samples: list[Sample], params: dict) -> float:
    positives = []
    negatives = []
    for s in samples:
        p = _predict(params, s.ingreso, s.deuda, s.antiguedad)
        if s.y == 1:
            positives.append(p)
        else:
            negatives.append(p)
    if not positives or not negatives:
        return 0.5
    wins = 0.0
    total = len(positives) * len(negatives)
    for pp in positives:
        for pn in negatives:
            if pp > pn:
                wins += 1.0
            elif pp == pn:
                wins += 0.5
    return wins / total


def _build_samples_from_db(window_days: int) -> list[Sample]:
    since = django_timezone.now() - timedelta(days=window_days)
    rows = (
        Credito.objects.filter(fecha_creacion__gte=since)
        .exclude(ingreso_mensual__lte=0)
        .exclude(deuda_actual__lt=0)
        .exclude(antiguedad_meses__lt=0)
        .values("ingreso_mensual", "deuda_actual", "antiguedad_meses", "estado")
    )
    samples: list[Sample] = []
    for row in rows:
        estado = str(row["estado"])
        if estado not in {"aprobado", "rechazado"}:
            continue
        y = 1 if estado == "rechazado" else 0
        samples.append(
            Sample(
                ingreso=float(row["ingreso_mensual"]),
                deuda=float(row["deuda_actual"]),
                antiguedad=int(row["antiguedad_meses"]),
                y=y,
            )
        )
    return samples


def _build_synthetic_samples(n: int, seed: int) -> list[Sample]:
    rng = random.Random(seed)
    out: list[Sample] = []
    for _ in range(n):
        ingreso = rng.uniform(1500, 12000)
        ratio = rng.uniform(0.05, 0.95)
        deuda = ingreso * ratio
        antiguedad = rng.randint(0, 180)
        risk = (ratio * 0.75) + (max(0, 1 - (antiguedad / 180)) * 0.25) + rng.uniform(-0.08, 0.08)
        y = 1 if risk > 0.55 else 0
        out.append(Sample(ingreso=ingreso, deuda=deuda, antiguedad=antiguedad, y=y))
    return out


def _balance(samples: list[Sample], seed: int) -> list[Sample]:
    rng = random.Random(seed)
    pos = [s for s in samples if s.y == 1]
    neg = [s for s in samples if s.y == 0]
    if not pos or not neg:
        return samples
    if len(pos) == len(neg):
        return samples
    major = pos if len(pos) > len(neg) else neg
    minor = neg if major is pos else pos
    rng.shuffle(major)
    major = major[: len(minor)]
    mixed = major + minor
    rng.shuffle(mixed)
    return mixed


def _split(samples: list[Sample], seed: int) -> tuple[list[Sample], list[Sample]]:
    rng = random.Random(seed)
    rows = list(samples)
    rng.shuffle(rows)
    cut = max(1, int(len(rows) * 0.8))
    return rows[:cut], rows[cut:] or rows[:1]


class Command(MAINCommand):
    help = "Entrena MAINline/candidato del scoring MVP y actualiza artefacto de modelo."

    def add_arguments(self, parser):
        parser.add_argument("--window-days", type=int, default=3650)
        parser.add_argument("--min-samples", type=int, default=80)
        parser.add_argument("--synthetic-size", type=int, default=300)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument(
            "--report-csv",
            default="docs/mineria/fase3/03_entrenamiento_scoring_mvp.csv",
        )
        parser.add_argument(
            "--report-md",
            default="docs/mineria/fase3/03_entrenamiento_scoring_mvp.md",
        )

    def handle(self, *args, **options):
        seed = int(options["seed"])
        min_samples = int(options["min_samples"])
        db_samples = _build_samples_from_db(int(options["window_days"]))

        source = "db"
        samples = db_samples
        if len(samples) < min_samples:
            source = "synthetic"
            samples = _build_synthetic_samples(int(options["synthetic_size"]), seed)

        samples = _balance(samples, seed=seed)
        train, valid = _split(samples, seed=seed)

        benchmark = {
            "max_antiguedad": 120.0,
            "peso_disponibilidad": 0.70,
            "peso_antiguedad": 0.30,
            "bias": 0.0,
        }

        best = dict(benchmark)
        best_brier = _brier_score(valid, best)
        for disp in [0.55, 0.6, 0.65, 0.7, 0.75]:
            ant = 1.0 - disp
            for bias in [-0.12, -0.08, -0.04, 0.0, 0.04]:
                candidate = {
                    "max_antiguedad": 120.0,
                    "peso_disponibilidad": disp,
                    "peso_antiguedad": ant,
                    "bias": bias,
                }
                score = _brier_score(valid, candidate)
                if score < best_brier:
                    best = candidate
                    best_brier = score

        benchmark_metrics = {
            "brier": _brier_score(valid, benchmark),
            "acc": _accuracy(valid, benchmark),
            "auc": _auc(valid, benchmark),
        }
        candidate_metrics = {
            "brier": _brier_score(valid, best),
            "acc": _accuracy(valid, best),
            "auc": _auc(valid, best),
        }

        root = Path(__file__).resolve().parents[6]
        model_path = root / "backend" / "fastapi_service" / "app" / "core" / "modelo_scoring.pkl"
        backup_path = model_path.with_name(f"modelo_scoring_backup_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.pkl")
        if model_path.exists():
            backup_path.write_bytes(model_path.read_bytes())

        artifact = {
            "model_kind": "weighted_score_v1",
            "params": best,
            "metadata": {
                "trained_at": datetime.now(timezone.utc).isoformat(),
                "source": source,
                "sample_count": len(samples),
                "train_count": len(train),
                "valid_count": len(valid),
                "benchmark_metrics": benchmark_metrics,
                "candidate_metrics": candidate_metrics,
                "selected": "candidate" if candidate_metrics["brier"] <= benchmark_metrics["brier"] else "benchmark",
            },
        }
        if artifact["metadata"]["selected"] == "benchmark":
            artifact["params"] = benchmark

        with model_path.open("wb") as file:
            pickle.dump(artifact, file)

        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)
        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["modelo", "brier", "acc", "auc", "params"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "modelo": "benchmark",
                    "brier": f"{benchmark_metrics['brier']:.6f}",
                    "acc": f"{benchmark_metrics['acc']:.6f}",
                    "auc": f"{benchmark_metrics['auc']:.6f}",
                    "params": str(benchmark),
                }
            )
            writer.writerow(
                {
                    "modelo": "candidate",
                    "brier": f"{candidate_metrics['brier']:.6f}",
                    "acc": f"{candidate_metrics['acc']:.6f}",
                    "auc": f"{candidate_metrics['auc']:.6f}",
                    "params": str(best),
                }
            )

        lines = [
            "# Entrenamiento Scoring MVP - Punto 2 de 8 (Fase 3)",
            "",
            f"Fecha: {datetime.now(timezone.utc).isoformat()}",
            f"Fuente de datos: `{source}`",
            f"Muestras usadas: {len(samples)} (train={len(train)}, valid={len(valid)})",
            "",
            "## Metricas en validacion",
            "",
            f"- Benchmark: brier={benchmark_metrics['brier']:.6f}, acc={benchmark_metrics['acc']:.6f}, auc={benchmark_metrics['auc']:.6f}",
            f"- Candidato: brier={candidate_metrics['brier']:.6f}, acc={candidate_metrics['acc']:.6f}, auc={candidate_metrics['auc']:.6f}",
            "",
            "## Parametros seleccionados",
            f"- {artifact['params']}",
            "",
            "## Artefactos",
            f"- Modelo actualizado: `{model_path}`",
            f"- Backup previo: `{backup_path if model_path.exists() else 'N/A'}`",
            f"- Reporte CSV: `{report_csv}`",
            "",
            "## Estado",
            "- Punto 2 de 8 completado tecnicamente.",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[entrenar_scoring_mvp] entrenamiento completado"))
        self.stdout.write(f"source={source} samples={len(samples)} train={len(train)} valid={len(valid)}")
        self.stdout.write(f"benchmark_brier={benchmark_metrics['brier']:.6f}")
        self.stdout.write(f"candidate_brier={candidate_metrics['brier']:.6f}")
        self.stdout.write(f"selected={artifact['metadata']['selected']}")
        self.stdout.write(f"model={model_path}")
        self.stdout.write(f"report={report_md}")

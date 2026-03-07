from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

MODEL_PATH = Path(__file__).resolve().parent / "modelo_scoring.pkl"


def load_model_artifact() -> dict[str, Any]:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")

    with MODEL_PATH.open("rb") as f:
        artifact = pickle.load(f)

    if not isinstance(artifact, dict):
        raise ValueError("Invalid model artifact format: expected dict")

    return artifact


def _clip_01(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def _predict_weighted_model(artifact: dict[str, Any], ingreso: float, deuda: float, antiguedad: int) -> float:
    params = artifact.get("params", {})
    max_antiguedad = float(params.get("max_antiguedad", 120))
    peso_disponibilidad = float(params.get("peso_disponibilidad", 0.7))
    peso_antiguedad = float(params.get("peso_antiguedad", 0.3))
    bias = float(params.get("bias", 0.0))

    disponibilidad = max(ingreso - deuda, 0.0) / max(ingreso, 1.0)
    antiguedad_norm = min(float(antiguedad) / max(max_antiguedad, 1.0), 1.0)

    score = bias + (peso_disponibilidad * disponibilidad) + (peso_antiguedad * antiguedad_norm)
    return _clip_01(score)


def predict_score(artifact: dict[str, Any], ingreso: float, deuda: float, antiguedad: int) -> float:
    model_kind = artifact.get("model_kind")

    if model_kind == "weighted_score_v1":
        return _predict_weighted_model(artifact, ingreso, deuda, antiguedad)

    # Compatibility: if a real serialized model object with predict_proba exists.
    model_obj = artifact.get("model")
    if model_obj is not None and hasattr(model_obj, "predict_proba"):
        feature_row = [[ingreso, deuda, antiguedad]]
        proba = float(model_obj.predict_proba(feature_row)[0][1])
        return _clip_01(proba)

    raise ValueError("Unsupported model artifact: missing supported model_kind/model object")

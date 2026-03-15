from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any, Dict, Tuple


MODEL_PATH = (
    Path(__file__).resolve().parent
    / "assets"
    / "modelo_scoring.pkl"
)
MODEL_VERSION = "intelicoop_scoring_v1"
_MODEL: Any = None
_MODEL_LOADED = False


def _load_model() -> Any:
    global _MODEL, _MODEL_LOADED
    if _MODEL_LOADED:
        return _MODEL
    _MODEL_LOADED = True
    if not MODEL_PATH.exists():
        _MODEL = None
        return None
    try:
        with MODEL_PATH.open("rb") as fh:
            _MODEL = pickle.load(fh)
    except Exception:
        _MODEL = None
    return _MODEL


def _fallback_score(ingreso_mensual: float, deuda_actual: float, antiguedad_meses: int) -> float:
    if ingreso_mensual <= 0:
        return 0.15
    ratio = deuda_actual / ingreso_mensual if ingreso_mensual else 1.0
    ratio_score = max(0.0, min(1.0, 1.0 - ratio))
    antiguedad_score = max(0.0, min(1.0, antiguedad_meses / 36.0))
    return round((ratio_score * 0.75) + (antiguedad_score * 0.25), 4)


def _predict_model_score(model: Any, features: list[float]) -> float | None:
    try:
        if hasattr(model, "predict_proba"):
            result = model.predict_proba([features])[0]
            if len(result) > 1:
                return float(result[1])
            return float(result[0])
        if hasattr(model, "predict"):
            result = model.predict([features])[0]
            return float(result)
    except Exception:
        return None
    return None


def evaluate_scoring(ingreso_mensual: float, deuda_actual: float, antiguedad_meses: int) -> Tuple[float, str, str, str]:
    model = _load_model()
    features = [float(ingreso_mensual), float(deuda_actual), float(antiguedad_meses)]
    score = _predict_model_score(model, features) if model is not None else None
    if score is None:
        score = _fallback_score(*features)
    score = max(0.0, min(1.0, float(score)))
    if score >= 0.8:
        recomendacion = "aprobar"
        riesgo = "bajo"
    elif score >= 0.55:
        recomendacion = "evaluar"
        riesgo = "medio"
    else:
        recomendacion = "rechazar"
        riesgo = "alto"
    return round(score, 4), recomendacion, riesgo, MODEL_VERSION


def summarize_scoring(rows: list[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(rows)
    por_riesgo = {"bajo": 0, "medio": 0, "alto": 0}
    por_recomendacion = {"aprobar": 0, "evaluar": 0, "rechazar": 0}
    score_sum = 0.0
    recientes = []
    for row in rows:
        score = float(row.get("score", 0) or 0)
        score_sum += score
        riesgo = str(row.get("riesgo", "")).lower()
        recomendacion = str(row.get("recomendacion", "")).lower()
        if riesgo in por_riesgo:
            por_riesgo[riesgo] += 1
        if recomendacion in por_recomendacion:
            por_recomendacion[recomendacion] += 1
        recientes.append(
            {
                "id": row.get("id"),
                "solicitud_id": row.get("solicitud_id"),
                "socio_id": row.get("socio_id"),
                "credito_id": row.get("credito_id"),
                "score": score,
                "recomendacion": recomendacion,
                "riesgo": riesgo,
                "model_version": row.get("model_version", MODEL_VERSION),
                "fecha_creacion": row.get("fecha_creacion"),
            }
        )
    recientes = list(reversed(recientes[-5:]))
    return {
        "total_inferencias": total,
        "score_promedio": round(score_sum / total, 4) if total else 0.0,
        "por_riesgo": por_riesgo,
        "por_recomendacion": por_recomendacion,
        "recientes": recientes,
    }

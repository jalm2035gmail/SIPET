from pydantic import BaseModel, Field
from fastapi import APIRouter

from app.core.scoring_model import load_model_artifact, predict_score

router = APIRouter()


class ScoringInput(BaseModel):
    ingreso_mensual: float = Field(..., gt=0)
    deuda_actual: float = Field(..., ge=0)
    antiguedad_meses: int = Field(..., ge=0)


@router.post("/scoring")
def scoring(data: ScoringInput) -> dict[str, float | str]:
    artifact = load_model_artifact()
    raw_score = predict_score(artifact, data.ingreso_mensual, data.deuda_actual, data.antiguedad_meses)
    score = round(raw_score, 2)

    if score >= 0.8:
        recomendacion, riesgo = "aprobar", "bajo"
    elif score >= 0.6:
        recomendacion, riesgo = "evaluar", "medio"
    else:
        recomendacion, riesgo = "rechazar", "alto"

    return {"score": score, "recomendacion": recomendacion, "riesgo": riesgo}

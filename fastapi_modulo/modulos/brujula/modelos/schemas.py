from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from fastapi_modulo.modulos.brujula.modelos.enums import (
    AnalysisFormatKind,
    AnalysisFormulaKind,
    BrujulaCategory,
    PeriodKind,
)


class BrujulaPeriod(BaseModel):
    key: str = Field(default="")
    label: str = Field(default="")
    kind: PeriodKind = Field(default=PeriodKind.HISTORICO)


class BrujulaIndicatorRow(BaseModel):
    indicador: str = Field(default="")
    values: dict[str, str] = Field(default_factory=dict)
    orden: int = Field(default=0)


class IndicatorValueUpdate(BaseModel):
    indicador: str = Field(default="")
    values: dict[str, str] = Field(default_factory=dict)


class IndicatorNotebookUpdate(BaseModel):
    rows: list[IndicatorValueUpdate] = Field(default_factory=list)


class IndicatorDefinitionOverrideUpdate(BaseModel):
    indicador: str = Field(default="")
    estandar_meta: str = Field(default="")
    semaforo_rojo: str = Field(default="")
    semaforo_verde: str = Field(default="")


class BrujulaIndicatorDefinitionPayload(BaseModel):
    nombre: str = Field(default="")
    indicador: str = Field(default="")
    estandar_meta: str = Field(default="")
    semaforo_rojo: str = Field(default="")
    semaforo_verde: str = Field(default="")
    categoria: BrujulaCategory | None = Field(default=None)


class IndicatorMatrixResponse(BaseModel):
    periods: list[BrujulaPeriod] = Field(default_factory=list)
    rows: list[BrujulaIndicatorRow] = Field(default_factory=list)


class IndicatorScenarioPeriod(BaseModel):
    result: str = Field(default="")
    raw_result: float | None = Field(default=None)
    inputs: list[dict[str, Any]] = Field(default_factory=list)


class IndicatorScenario(BaseModel):
    indicador: str = Field(default="")
    formula_kind: AnalysisFormulaKind = Field(default=AnalysisFormulaKind.RATIO)
    format_kind: AnalysisFormatKind = Field(default=AnalysisFormatKind.PERCENT)
    meta: str = Field(default="")
    periods: dict[str, IndicatorScenarioPeriod] = Field(default_factory=dict)


class IndicatorScenariosResponse(BaseModel):
    periods: list[BrujulaPeriod] = Field(default_factory=list)
    scenarios: list[IndicatorScenario] = Field(default_factory=list)


class ApiSuccessEnvelope(BaseModel):
    success: bool = Field(default=True)
    data: Any = None


class ApiErrorEnvelope(BaseModel):
    success: bool = Field(default=False)
    error: str = Field(default="")

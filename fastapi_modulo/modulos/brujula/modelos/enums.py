from __future__ import annotations

from enum import Enum


class PeriodKind(str, Enum):
    HISTORICO = "historico"
    PROYECTADO = "proyectado"


class BrujulaCategory(str, Enum):
    BALANCE_SOCIAL = "Balance social"
    RENTABILIDAD = "Rentabilidad"
    UNIDAD_INSTITUCIONAL = "Unidad institucional"
    JUNTA_DIRECTIVA_GOBERNANZA = "Junta directiva / gobernanza"
    UTILIZACION_RECURSOS = "Utilizacion de recursos"
    LIQUIDEZ = "Liquidez"
    ADMINISTRACION = "Administracion"


class AnalysisFormulaKind(str, Enum):
    RATIO = "ratio"
    DIFFERENCE = "difference"
    GROWTH = "growth"
    RATIO_AVERAGE = "ratio_average"
    DIRECT = "direct"


class AnalysisFormatKind(str, Enum):
    PERCENT = "percent"
    AMOUNT = "amount"
    NUMBER = "number"


class ThresholdValue(str, Enum):
    NOT_APPLICABLE = "N/A"


class ApiStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"

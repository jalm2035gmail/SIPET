from __future__ import annotations

from enum import Enum
from typing import Iterable


class BaseCatalogEnum(str, Enum):
    @classmethod
    def values(cls) -> tuple[str, ...]:
        return tuple(item.value for item in cls)


class EstadoControl(BaseCatalogEnum):
    ACTIVO = "Activo"
    INACTIVO = "Inactivo"


class PeriodicidadControl(BaseCatalogEnum):
    DIARIO = "Diario"
    SEMANAL = "Semanal"
    MENSUAL = "Mensual"
    TRIMESTRAL = "Trimestral"
    SEMESTRAL = "Semestral"
    ANUAL = "Anual"
    EVENTUAL = "Eventual"


class EstadoPrograma(BaseCatalogEnum):
    BORRADOR = "Borrador"
    APROBADO = "Aprobado"
    EN_EJECUCION = "En ejecucion"
    CERRADO = "Cerrado"


class EstadoActividad(BaseCatalogEnum):
    PROGRAMADO = "Programado"
    EN_PROCESO = "En proceso"
    COMPLETADO = "Completado"
    DIFERIDO = "Diferido"
    CANCELADO = "Cancelado"


class TipoEvidencia(BaseCatalogEnum):
    DOCUMENTO = "Documento"
    FOTOGRAFIA = "Fotografia"
    CORREO_ELECTRONICO = "Correo electronico"
    ACTA = "Acta"
    CAPTURA_PANTALLA = "Captura de pantalla"
    OTRO = "Otro"


class ResultadoEvaluacion(BaseCatalogEnum):
    CUMPLE = "Cumple"
    CUMPLE_PARCIALMENTE = "Cumple parcialmente"
    NO_CUMPLE = "No cumple"
    POR_EVALUAR = "Por evaluar"


class NivelRiesgoHallazgo(BaseCatalogEnum):
    BAJO = "Bajo"
    MEDIO = "Medio"
    ALTO = "Alto"
    CRITICO = "Critico"


class EstadoHallazgo(BaseCatalogEnum):
    ABIERTO = "Abierto"
    EN_ATENCION = "En atencion"
    SUBSANADO = "Subsanado"
    CERRADO = "Cerrado"


class EstadoAccionCorrectiva(BaseCatalogEnum):
    PENDIENTE = "Pendiente"
    EN_PROCESO = "En proceso"
    EJECUTADA = "Ejecutada"
    VERIFICADA = "Verificada"
    CANCELADA = "Cancelada"


CONTROL_ESTADOS = EstadoControl.values()
CONTROL_PERIODICIDADES = PeriodicidadControl.values()
PROGRAMA_ESTADOS = EstadoPrograma.values()
ACTIVIDAD_ESTADOS = EstadoActividad.values()
EVIDENCIA_TIPOS = TipoEvidencia.values()
EVIDENCIA_RESULTADOS = ResultadoEvaluacion.values()
HALLAZGO_RIESGOS = NivelRiesgoHallazgo.values()
HALLAZGO_ESTADOS = EstadoHallazgo.values()
ACCION_ESTADOS = EstadoAccionCorrectiva.values()


def clean_text(value: object) -> str:
    return str(value or "").strip()


def clean_optional_text(value: object) -> str | None:
    text = clean_text(value)
    return text or None


def coerce_choice(value: object, allowed: Iterable[str], default: str) -> str:
    raw = clean_text(value)
    if not raw:
        return default
    normalized = raw.casefold()
    for option in allowed:
        if option.casefold() == normalized:
            return option
    return default


__all__ = [
    "ACCION_ESTADOS",
    "ACTIVIDAD_ESTADOS",
    "BaseCatalogEnum",
    "CONTROL_ESTADOS",
    "CONTROL_PERIODICIDADES",
    "EVIDENCIA_RESULTADOS",
    "EVIDENCIA_TIPOS",
    "EstadoAccionCorrectiva",
    "EstadoActividad",
    "EstadoControl",
    "EstadoHallazgo",
    "EstadoPrograma",
    "HALLAZGO_ESTADOS",
    "HALLAZGO_RIESGOS",
    "NivelRiesgoHallazgo",
    "PeriodicidadControl",
    "PROGRAMA_ESTADOS",
    "ResultadoEvaluacion",
    "TipoEvidencia",
    "clean_optional_text",
    "clean_text",
    "coerce_choice",
]

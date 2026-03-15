from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from fastapi_modulo.modulos.control_interno.modelos.enums import (
    EstadoAccionCorrectiva,
    EstadoActividad,
    EstadoControl,
    EstadoHallazgo,
    EstadoPrograma,
    NivelRiesgoHallazgo,
    PeriodicidadControl,
    ResultadoEvaluacion,
    TipoEvidencia,
)


class _SchemaBase(BaseModel):
    class Config:
        extra = "ignore"
        use_enum_values = True


class ControlInternoCreate(_SchemaBase):
    codigo: str = Field(min_length=1)
    nombre: str = Field(min_length=1)
    componente: str = Field(min_length=1)
    area: str = Field(min_length=1)
    tipo_riesgo: Optional[str] = None
    periodicidad: Optional[PeriodicidadControl] = None
    descripcion: Optional[str] = None
    normativa: Optional[str] = None
    estado: Optional[EstadoControl] = None


class ControlInternoUpdate(_SchemaBase):
    codigo: Optional[str] = None
    nombre: Optional[str] = None
    componente: Optional[str] = None
    area: Optional[str] = None
    tipo_riesgo: Optional[str] = None
    periodicidad: Optional[PeriodicidadControl] = None
    descripcion: Optional[str] = None
    normativa: Optional[str] = None
    estado: Optional[EstadoControl] = None


class ProgramaCreate(_SchemaBase):
    anio: int
    nombre: str = Field(min_length=1)
    descripcion: Optional[str] = None
    estado: Optional[EstadoPrograma] = None


class ProgramaUpdate(_SchemaBase):
    anio: Optional[int] = None
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    estado: Optional[EstadoPrograma] = None


class ProgramaActividadCreate(_SchemaBase):
    control_id: Optional[int] = None
    descripcion: Optional[str] = None
    responsable: Optional[str] = None
    fecha_inicio_programada: Optional[str] = None
    fecha_fin_programada: Optional[str] = None
    fecha_inicio_real: Optional[str] = None
    fecha_fin_real: Optional[str] = None
    estado: Optional[EstadoActividad] = None
    observaciones: Optional[str] = None


class ProgramaActividadUpdate(_SchemaBase):
    control_id: Optional[int] = None
    descripcion: Optional[str] = None
    responsable: Optional[str] = None
    fecha_inicio_programada: Optional[str] = None
    fecha_fin_programada: Optional[str] = None
    fecha_inicio_real: Optional[str] = None
    fecha_fin_real: Optional[str] = None
    estado: Optional[EstadoActividad] = None
    observaciones: Optional[str] = None


class EvidenciaCreate(_SchemaBase):
    titulo: str = Field(min_length=1)
    tipo: Optional[TipoEvidencia] = None
    fecha_evidencia: Optional[str] = None
    control_id: Optional[int] = None
    actividad_id: Optional[int] = None
    resultado_evaluacion: Optional[ResultadoEvaluacion] = None
    descripcion: Optional[str] = None
    observaciones: Optional[str] = None


class EvidenciaUpdate(_SchemaBase):
    titulo: Optional[str] = None
    tipo: Optional[TipoEvidencia] = None
    fecha_evidencia: Optional[str] = None
    control_id: Optional[int] = None
    actividad_id: Optional[int] = None
    resultado_evaluacion: Optional[ResultadoEvaluacion] = None
    descripcion: Optional[str] = None
    observaciones: Optional[str] = None


class HallazgoCreate(_SchemaBase):
    evidencia_id: Optional[int] = None
    actividad_id: Optional[int] = None
    control_id: Optional[int] = None
    codigo: Optional[str] = None
    titulo: str = Field(min_length=1)
    descripcion: Optional[str] = None
    causa: Optional[str] = None
    efecto: Optional[str] = None
    componente_coso: Optional[str] = None
    nivel_riesgo: Optional[NivelRiesgoHallazgo] = None
    estado: Optional[EstadoHallazgo] = None
    fecha_deteccion: Optional[str] = None
    fecha_limite: Optional[str] = None
    responsable: Optional[str] = None


class HallazgoUpdate(_SchemaBase):
    evidencia_id: Optional[int] = None
    actividad_id: Optional[int] = None
    control_id: Optional[int] = None
    codigo: Optional[str] = None
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    causa: Optional[str] = None
    efecto: Optional[str] = None
    componente_coso: Optional[str] = None
    nivel_riesgo: Optional[NivelRiesgoHallazgo] = None
    estado: Optional[EstadoHallazgo] = None
    fecha_deteccion: Optional[str] = None
    fecha_limite: Optional[str] = None
    responsable: Optional[str] = None


class AccionCorrectivaCreate(_SchemaBase):
    descripcion: str = Field(min_length=1)
    responsable: Optional[str] = None
    fecha_compromiso: Optional[str] = None
    fecha_ejecucion: Optional[str] = None
    estado: Optional[EstadoAccionCorrectiva] = None
    evidencia_seguimiento: Optional[str] = None


class AccionCorrectivaUpdate(_SchemaBase):
    descripcion: Optional[str] = None
    responsable: Optional[str] = None
    fecha_compromiso: Optional[str] = None
    fecha_ejecucion: Optional[str] = None
    estado: Optional[EstadoAccionCorrectiva] = None
    evidencia_seguimiento: Optional[str] = None


def validate_schema(schema_cls: type[_SchemaBase], data: dict[str, Any]) -> _SchemaBase:
    if hasattr(schema_cls, "model_validate"):
        return schema_cls.model_validate(data)
    return schema_cls.parse_obj(data)


def dump_schema(model: _SchemaBase, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_unset=exclude_unset)
    return model.dict(exclude_unset=exclude_unset)


__all__ = [
    "AccionCorrectivaCreate",
    "AccionCorrectivaUpdate",
    "ControlInternoCreate",
    "ControlInternoUpdate",
    "EvidenciaCreate",
    "EvidenciaUpdate",
    "HallazgoCreate",
    "HallazgoUpdate",
    "ProgramaActividadCreate",
    "ProgramaActividadUpdate",
    "ProgramaCreate",
    "ProgramaUpdate",
    "dump_schema",
    "validate_schema",
]

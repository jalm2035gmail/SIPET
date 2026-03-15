from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from .enums import (
    EstadoAuditoria,
    EstadoHallazgo,
    EstadoRecomendacion,
    NivelRiesgo,
    PrioridadRecomendacion,
    TipoAuditoria,
)


class AuditoriaCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=30)
    nombre: str = Field(..., min_length=1, max_length=200)
    tipo: TipoAuditoria = TipoAuditoria.INTERNA
    area_auditada: Optional[str] = Field(None, max_length=150)
    objetivo: Optional[str] = None
    alcance: Optional[str] = None
    periodo: Optional[str] = Field(None, max_length=50)
    fecha_inicio: Optional[date] = None
    fecha_fin_est: Optional[date] = None
    fecha_fin_real: Optional[date] = None
    estado: EstadoAuditoria = EstadoAuditoria.PLANIFICADA
    responsable: Optional[str] = Field(None, max_length=150)
    auditor_lider: Optional[str] = Field(None, max_length=150)


class AuditoriaUpdate(BaseModel):
    codigo: Optional[str] = Field(None, min_length=1, max_length=30)
    nombre: Optional[str] = Field(None, min_length=1, max_length=200)
    tipo: Optional[TipoAuditoria] = None
    area_auditada: Optional[str] = Field(None, max_length=150)
    objetivo: Optional[str] = None
    alcance: Optional[str] = None
    periodo: Optional[str] = Field(None, max_length=50)
    fecha_inicio: Optional[date] = None
    fecha_fin_est: Optional[date] = None
    fecha_fin_real: Optional[date] = None
    estado: Optional[EstadoAuditoria] = None
    responsable: Optional[str] = Field(None, max_length=150)
    auditor_lider: Optional[str] = Field(None, max_length=150)


class HallazgoCreate(BaseModel):
    auditoria_id: int
    codigo: Optional[str] = Field(None, max_length=30)
    titulo: str = Field(..., min_length=1, max_length=200)
    descripcion: Optional[str] = None
    criterio: Optional[str] = None
    condicion: Optional[str] = None
    causa: Optional[str] = None
    efecto: Optional[str] = None
    nivel_riesgo: NivelRiesgo = NivelRiesgo.MEDIO
    estado: EstadoHallazgo = EstadoHallazgo.ABIERTO
    responsable: Optional[str] = Field(None, max_length=150)
    fecha_limite: Optional[date] = None


class HallazgoUpdate(BaseModel):
    codigo: Optional[str] = Field(None, max_length=30)
    titulo: Optional[str] = Field(None, min_length=1, max_length=200)
    descripcion: Optional[str] = None
    criterio: Optional[str] = None
    condicion: Optional[str] = None
    causa: Optional[str] = None
    efecto: Optional[str] = None
    nivel_riesgo: Optional[NivelRiesgo] = None
    estado: Optional[EstadoHallazgo] = None
    responsable: Optional[str] = Field(None, max_length=150)
    fecha_limite: Optional[date] = None


class RecomendacionCreate(BaseModel):
    hallazgo_id: int
    descripcion: str = Field(..., min_length=1)
    responsable: Optional[str] = Field(None, max_length=150)
    prioridad: PrioridadRecomendacion = PrioridadRecomendacion.MEDIA
    fecha_compromiso: Optional[date] = None
    estado: EstadoRecomendacion = EstadoRecomendacion.PENDIENTE
    porcentaje_avance: int = Field(default=0, ge=0, le=100)


class RecomendacionUpdate(BaseModel):
    descripcion: Optional[str] = None
    responsable: Optional[str] = Field(None, max_length=150)
    prioridad: Optional[PrioridadRecomendacion] = None
    fecha_compromiso: Optional[date] = None
    estado: Optional[EstadoRecomendacion] = None
    porcentaje_avance: Optional[int] = Field(default=None, ge=0, le=100)


class SeguimientoCreate(BaseModel):
    recomendacion_id: int
    fecha: Optional[date] = None
    descripcion: str = Field(..., min_length=1)
    porcentaje_avance: int = Field(default=0, ge=0, le=100)
    evidencia: Optional[str] = None
    registrado_por: Optional[str] = Field(None, max_length=150)

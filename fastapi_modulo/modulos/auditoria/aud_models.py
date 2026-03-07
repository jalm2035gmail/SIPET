from __future__ import annotations

from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


# ── Auditoría ─────────────────────────────────────────────────────────────────

class AuditoriaCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=30)
    nombre: str = Field(..., min_length=1, max_length=200)
    tipo: str = "interna"
    area_auditada: Optional[str] = None
    objetivo: Optional[str] = None
    alcance: Optional[str] = None
    periodo: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin_est: Optional[date] = None
    fecha_fin_real: Optional[date] = None
    estado: str = "planificada"
    responsable: Optional[str] = None
    auditor_lider: Optional[str] = None


class AuditoriaUpdate(BaseModel):
    codigo: Optional[str] = None
    nombre: Optional[str] = None
    tipo: Optional[str] = None
    area_auditada: Optional[str] = None
    objetivo: Optional[str] = None
    alcance: Optional[str] = None
    periodo: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin_est: Optional[date] = None
    fecha_fin_real: Optional[date] = None
    estado: Optional[str] = None
    responsable: Optional[str] = None
    auditor_lider: Optional[str] = None


# ── Hallazgo ──────────────────────────────────────────────────────────────────

class HallazgoCreate(BaseModel):
    auditoria_id: int
    codigo: Optional[str] = None
    titulo: str = Field(..., min_length=1, max_length=200)
    descripcion: Optional[str] = None
    criterio: Optional[str] = None
    condicion: Optional[str] = None
    causa: Optional[str] = None
    efecto: Optional[str] = None
    nivel_riesgo: str = "medio"
    estado: str = "abierto"
    responsable: Optional[str] = None
    fecha_limite: Optional[date] = None


class HallazgoUpdate(BaseModel):
    codigo: Optional[str] = None
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    criterio: Optional[str] = None
    condicion: Optional[str] = None
    causa: Optional[str] = None
    efecto: Optional[str] = None
    nivel_riesgo: Optional[str] = None
    estado: Optional[str] = None
    responsable: Optional[str] = None
    fecha_limite: Optional[date] = None


# ── Recomendación ─────────────────────────────────────────────────────────────

class RecomendacionCreate(BaseModel):
    hallazgo_id: int
    descripcion: str = Field(..., min_length=1)
    responsable: Optional[str] = None
    prioridad: str = "media"
    fecha_compromiso: Optional[date] = None
    estado: str = "pendiente"
    porcentaje_avance: int = Field(default=0, ge=0, le=100)


class RecomendacionUpdate(BaseModel):
    descripcion: Optional[str] = None
    responsable: Optional[str] = None
    prioridad: Optional[str] = None
    fecha_compromiso: Optional[date] = None
    estado: Optional[str] = None
    porcentaje_avance: Optional[int] = Field(default=None, ge=0, le=100)


# ── Seguimiento ───────────────────────────────────────────────────────────────

class SeguimientoCreate(BaseModel):
    recomendacion_id: int
    fecha: Optional[date] = None
    descripcion: str = Field(..., min_length=1)
    porcentaje_avance: int = Field(default=0, ge=0, le=100)
    evidencia: Optional[str] = None
    registrado_por: Optional[str] = None

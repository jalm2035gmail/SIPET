from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CrmMAIN(BaseModel):
    model_config = ConfigDict(protected_namespaces=())


# ── Contacto ──────────────────────────────────────────────────────────────────

class ContactoCreate(CrmMAIN):
    nombre: str = Field(min_length=1)
    email: Optional[str] = None
    telefono: str = ""
    empresa: str = ""
    puesto: str = ""
    tipo: str = "prospecto"
    fuente: str = "manual"
    notas: Optional[str] = None


class ContactoUpdate(CrmMAIN):
    nombre: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    empresa: Optional[str] = None
    puesto: Optional[str] = None
    tipo: Optional[str] = None
    fuente: Optional[str] = None
    notas: Optional[str] = None


# ── Oportunidad ───────────────────────────────────────────────────────────────

class OportunidadCreate(CrmMAIN):
    contacto_id: int
    nombre: str = Field(min_length=1)
    etapa: str = "prospecto"
    valor_estimado: float = Field(ge=0, default=0.0)
    probabilidad: int = Field(ge=0, le=100, default=0)
    fecha_cierre_est: Optional[date] = None
    responsable: str = ""
    descripcion: Optional[str] = None


class OportunidadUpdate(CrmMAIN):
    nombre: Optional[str] = None
    etapa: Optional[str] = None
    valor_estimado: Optional[float] = None
    probabilidad: Optional[int] = None
    fecha_cierre_est: Optional[date] = None
    responsable: Optional[str] = None
    descripcion: Optional[str] = None


# ── Actividad ─────────────────────────────────────────────────────────────────

class ActividadCreate(CrmMAIN):
    contacto_id: Optional[int] = None
    oportunidad_id: Optional[int] = None
    tipo: str = "tarea"
    titulo: str = Field(min_length=1)
    descripcion: Optional[str] = None
    fecha: datetime = Field(default_factory=datetime.utcnow)
    completada: bool = False
    responsable: str = ""


class ActividadUpdate(CrmMAIN):
    tipo: Optional[str] = None
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    fecha: Optional[datetime] = None
    completada: Optional[bool] = None
    responsable: Optional[str] = None


# ── Nota ──────────────────────────────────────────────────────────────────────

class NotaCreate(CrmMAIN):
    contacto_id: Optional[int] = None
    oportunidad_id: Optional[int] = None
    contenido: str = Field(min_length=1)
    autor: str = ""


# ── Campaña ───────────────────────────────────────────────────────────────────

class CampaniaCreate(CrmMAIN):
    nombre: str = Field(min_length=1)
    tipo: str = "email"
    estado: str = "borrador"
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    descripcion: Optional[str] = None


class CampaniaUpdate(CrmMAIN):
    nombre: Optional[str] = None
    tipo: Optional[str] = None
    estado: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    descripcion: Optional[str] = None


# ── Contacto–Campaña ──────────────────────────────────────────────────────────

class ContactoCampaniaCreate(CrmMAIN):
    contacto_id: int
    campania_id: int
    estado: str = "pendiente"

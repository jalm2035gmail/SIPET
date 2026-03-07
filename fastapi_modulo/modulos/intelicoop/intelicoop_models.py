from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class IntelicoopBaseModel(BaseModel):
    model_config = ConfigDict(protected_namespaces=())


class SocioCreate(IntelicoopBaseModel):
    nombre: str = Field(min_length=1)
    email: str = Field(min_length=3)
    telefono: str = ""
    direccion: str = ""
    segmento: str = "inactivo"


class CreditoCreate(IntelicoopBaseModel):
    socio_id: int
    monto: float = Field(ge=0)
    plazo: int = Field(ge=1)
    ingreso_mensual: float = Field(ge=0, default=0)
    deuda_actual: float = Field(ge=0, default=0)
    antiguedad_meses: int = Field(ge=0, default=0)
    estado: str = "solicitado"


class CampaniaCreate(IntelicoopBaseModel):
    nombre: str = Field(min_length=1)
    tipo: str = Field(min_length=1)
    fecha_inicio: str = ""
    fecha_fin: str = ""
    estado: str = "borrador"


class ProspectoCreate(IntelicoopBaseModel):
    nombre: str = Field(min_length=1)
    telefono: str = ""
    direccion: str = ""
    fuente: str = ""
    score_propension: float = Field(ge=0, le=1, default=0)


class ContactoCampaniaCreate(IntelicoopBaseModel):
    campania_id: int
    socio_id: int
    ejecutivo_id: str = "ejecutivo_general"
    canal: str = "telefono"
    estado_contacto: str = "pendiente"


class SeguimientoCampaniaCreate(IntelicoopBaseModel):
    campania_id: int
    socio_id: int
    lista: str = "general"
    etapa: str = "contactado"
    conversion: bool = False
    monto_colocado: float = Field(ge=0, default=0)


class CuentaCreate(IntelicoopBaseModel):
    socio_id: int
    tipo: str = "ahorro"
    saldo: float = Field(ge=0, default=0)


class TransaccionCreate(IntelicoopBaseModel):
    cuenta_id: int
    monto: float = Field(gt=0)
    tipo: str = "deposito"


class HistorialPagoCreate(IntelicoopBaseModel):
    credito_id: int
    monto: float = Field(gt=0)


class ScoringEvaluateInput(IntelicoopBaseModel):
    solicitud_id: Optional[str] = None
    socio_id: Optional[int] = None
    credito_id: Optional[int] = None
    ingreso_mensual: float = Field(ge=0)
    deuda_actual: float = Field(ge=0, default=0)
    antiguedad_meses: int = Field(ge=0, default=0)


class ScoringResult(IntelicoopBaseModel):
    id: int
    solicitud_id: str
    socio_id: Optional[int] = None
    credito_id: Optional[int] = None
    ingreso_mensual: float
    deuda_actual: float
    antiguedad_meses: int
    score: float
    recomendacion: str
    riesgo: str
    model_version: str
    fecha_creacion: datetime

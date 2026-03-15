from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import (
    BucketMora,
    EstadoCredito,
    EstadoPromesaPago,
    NivelRiesgo,
    ResultadoGestion,
    TipoGestionCobranza,
    TipoIndicador,
)


class ORMBaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ClienteCreateSchema(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=40)
    nombre_completo: str = Field(..., min_length=1, max_length=180)
    identificacion: str = Field(..., min_length=1, max_length=40)
    telefono: Optional[str] = None
    correo: Optional[str] = None
    direccion: Optional[str] = None
    segmento: Optional[str] = None
    nivel_riesgo: NivelRiesgo = NivelRiesgo.BAJO


class ClienteResponseSchema(ORMBaseSchema):
    id: int
    codigo: str
    nombre_completo: str
    identificacion: str
    telefono: Optional[str] = None
    correo: Optional[str] = None
    direccion: Optional[str] = None
    segmento: Optional[str] = None
    nivel_riesgo: str
    activo: bool


class CreditoCreateSchema(BaseModel):
    cliente_id: int
    numero_credito: str = Field(..., min_length=1, max_length=50)
    producto: str = Field(..., min_length=1, max_length=100)
    fecha_desembolso: date
    fecha_vencimiento: Optional[date] = None
    monto_original: Decimal = Field(default=Decimal("0"), ge=0)
    tasa_interes: Decimal = Field(default=Decimal("0"), ge=0)
    saldo_capital: Decimal = Field(default=Decimal("0"), ge=0)
    etapa_colocacion: str = Field(default="formalizacion", min_length=1, max_length=40)
    score_riesgo: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    documentacion_completa: bool = True
    es_renovacion: bool = False
    oficial: Optional[str] = None
    sucursal: Optional[str] = None


class CreditoResponseSchema(ORMBaseSchema):
    id: int
    cliente_id: int
    numero_credito: str
    producto: str
    fecha_desembolso: date
    fecha_vencimiento: Optional[date] = None
    monto_original: Decimal
    tasa_interes: Decimal
    saldo_capital: Decimal
    estado: str
    bucket_mora: str
    dias_mora: int
    etapa_colocacion: str
    score_riesgo: Decimal
    documentacion_completa: bool
    es_renovacion: bool
    oficial: Optional[str] = None
    sucursal: Optional[str] = None


class SaldoCreditoSchema(ORMBaseSchema):
    id: int
    credito_id: int
    saldo_capital: Decimal
    saldo_interes: Decimal
    saldo_mora: Decimal
    saldo_total: Decimal
    fecha_corte: date


class MoraCreditoSchema(ORMBaseSchema):
    id: int
    credito_id: int
    fecha_exigible: Optional[date] = None
    dias_mora: int
    bucket: str
    monto_vencido: Decimal
    porcentaje_cobertura: Decimal


class PromesaPagoCreateSchema(BaseModel):
    credito_id: int
    fecha_compromiso: date
    monto_comprometido: Decimal = Field(..., ge=0)
    observaciones: Optional[str] = None


class PromesaPagoUpdateSchema(BaseModel):
    monto_cumplido: Decimal = Field(default=Decimal("0"), ge=0)
    estado: EstadoPromesaPago
    observaciones: Optional[str] = None


class PromesaPagoResponseSchema(ORMBaseSchema):
    id: int
    credito_id: int
    fecha_promesa: date
    fecha_compromiso: date
    monto_comprometido: Decimal
    monto_cumplido: Decimal
    estado: str
    observaciones: Optional[str] = None


class GestionCobranzaCreateSchema(BaseModel):
    credito_id: int
    tipo_gestion: TipoGestionCobranza
    resultado: ResultadoGestion
    responsable: Optional[str] = None
    comentario: Optional[str] = None
    proxima_accion: Optional[str] = None
    fecha_proxima_accion: Optional[date] = None


class GestionCobranzaResponseSchema(ORMBaseSchema):
    id: int
    credito_id: int
    fecha_gestion: datetime
    tipo_gestion: str
    resultado: str
    responsable: Optional[str] = None
    comentario: Optional[str] = None
    proxima_accion: Optional[str] = None
    fecha_proxima_accion: Optional[date] = None


class CastigoCreditoCreateSchema(BaseModel):
    credito_id: int
    fecha_castigo: date
    monto_castigado: Decimal = Field(..., ge=0)
    motivo: Optional[str] = None
    aprobado_por: Optional[str] = None
    observaciones: Optional[str] = None


class ReestructuraCreditoCreateSchema(BaseModel):
    credito_id: int
    fecha_reestructura: date
    nuevo_plazo_meses: Optional[int] = Field(default=None, ge=1)
    nueva_tasa: Optional[Decimal] = Field(default=None, ge=0)
    cuota_anterior: Optional[Decimal] = Field(default=None, ge=0)
    cuota_nueva: Optional[Decimal] = Field(default=None, ge=0)
    justificacion: Optional[str] = None
    aprobado_por: Optional[str] = None


class IndicadorCarteraSchema(ORMBaseSchema):
    id: int
    fecha_corte: date
    tipo_indicador: str
    nombre: str
    valor: Decimal
    meta: Optional[Decimal] = None
    semaforo: str
    detalle: Optional[str] = None


class IndicadorSnapshotSchema(BaseModel):
    tipo_indicador: TipoIndicador
    nombre: str
    valor: Decimal
    meta: Optional[Decimal] = None
    semaforo: NivelRiesgo
    detalle: Optional[str] = None


class CreditoResumenSchema(BaseModel):
    credito_id: int
    numero_credito: str
    cliente: str
    saldo_total: Decimal
    dias_mora: int
    bucket_mora: BucketMora
    estado: EstadoCredito
    nivel_riesgo: NivelRiesgo


class ResumenCarteraSchema(BaseModel):
    total_creditos: int
    total_clientes: int
    saldo_total: Decimal
    saldo_vencido: Decimal
    indice_mora: Decimal
    distribucion_buckets: dict[str, int]


class MesaControlResumenSchema(BaseModel):
    fecha_corte: date
    cartera: ResumenCarteraSchema
    recuperacion_mes: Decimal
    efectividad_cobranza: Decimal
    promesas_pendientes: int
    casos_criticos: int


@field_validator("correo")
@classmethod
def _noop_email_validator(cls, value: Optional[str]) -> Optional[str]:
    return value

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from fastapi_modulo.modulos.activo_fijo.enums import (
    EstadoActivo,
    EstadoAsignacion,
    EstadoMantenimiento,
    MetodoDepreciacion,
    MotivoBaja,
    TipoMantenimiento,
)

METODOS_DEPRECIACION_VALIDOS = {item.value for item in MetodoDepreciacion}
ESTADOS_ACTIVO_VALIDOS = {item.value for item in EstadoActivo}
ESTADOS_ASIGNACION_VALIDOS = {item.value for item in EstadoAsignacion}
TIPOS_MANTENIMIENTO_VALIDOS = {item.value for item in TipoMantenimiento}
ESTADOS_MANTENIMIENTO_VALIDOS = {item.value for item in EstadoMantenimiento}
MOTIVOS_BAJA_VALIDOS = {item.value for item in MotivoBaja}


class ActivoCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=40)
    nombre: str = Field(..., min_length=1, max_length=200)
    categoria: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    numero_serie: Optional[str] = None
    proveedor: Optional[str] = None
    fecha_adquisicion: Optional[date] = None
    valor_adquisicion: Decimal = Field(default=Decimal("0"), ge=0)
    valor_residual: Decimal = Field(default=Decimal("0"), ge=0)
    vida_util_meses: int = Field(default=60, ge=1)
    metodo_depreciacion: str = MetodoDepreciacion.LINEA_RECTA.value
    ubicacion: Optional[str] = None
    responsable: Optional[str] = None
    estado: str = EstadoActivo.ACTIVO.value
    descripcion: Optional[str] = None

    @field_validator("metodo_depreciacion")
    @classmethod
    def validate_metodo_depreciacion(cls, value: str) -> str:
        if value not in METODOS_DEPRECIACION_VALIDOS:
            raise ValueError("Metodo de depreciacion no permitido")
        return value

    @field_validator("estado")
    @classmethod
    def validate_estado(cls, value: str) -> str:
        if value not in ESTADOS_ACTIVO_VALIDOS:
            raise ValueError("Estado no permitido")
        return value

    @model_validator(mode="after")
    def validate_valores(self):
        if self.valor_residual > self.valor_adquisicion:
            raise ValueError("El valor residual no puede ser mayor al valor de adquisicion")
        return self


class ActivoUpdate(BaseModel):
    codigo: Optional[str] = None
    nombre: Optional[str] = None
    categoria: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    numero_serie: Optional[str] = None
    proveedor: Optional[str] = None
    fecha_adquisicion: Optional[date] = None
    valor_adquisicion: Optional[Decimal] = None
    valor_residual: Optional[Decimal] = None
    vida_util_meses: Optional[int] = Field(default=None, ge=1)
    metodo_depreciacion: Optional[str] = None
    ubicacion: Optional[str] = None
    responsable: Optional[str] = None
    estado: Optional[str] = None
    descripcion: Optional[str] = None

    @field_validator("metodo_depreciacion")
    @classmethod
    def validate_metodo_depreciacion(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in METODOS_DEPRECIACION_VALIDOS:
            raise ValueError("Metodo de depreciacion no permitido")
        return value

    @field_validator("estado")
    @classmethod
    def validate_estado(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in ESTADOS_ACTIVO_VALIDOS:
            raise ValueError("Estado no permitido")
        return value

    @model_validator(mode="after")
    def validate_valores(self):
        if (
            self.valor_residual is not None
            and self.valor_adquisicion is not None
            and self.valor_residual > self.valor_adquisicion
        ):
            raise ValueError("El valor residual no puede ser mayor al valor de adquisicion")
        return self


class DepreciarRequest(BaseModel):
    periodo: Optional[str] = None
    tasa_saldo_decreciente: Optional[Decimal] = None


class AsignacionCreate(BaseModel):
    activo_id: int
    empleado: Optional[str] = None
    area: Optional[str] = None
    fecha_asignacion: Optional[date] = None
    fecha_devolucion: Optional[date] = None
    estado: str = EstadoAsignacion.VIGENTE.value
    observaciones: Optional[str] = None

    @field_validator("estado")
    @classmethod
    def validate_estado(cls, value: str) -> str:
        if value not in ESTADOS_ASIGNACION_VALIDOS:
            raise ValueError("Estado de asignacion no permitido")
        return value

    @model_validator(mode="after")
    def validate_fechas(self):
        if (
            self.fecha_asignacion is not None
            and self.fecha_devolucion is not None
            and self.fecha_devolucion < self.fecha_asignacion
        ):
            raise ValueError("La fecha de devolucion no puede ser menor a la fecha de asignacion")
        return self


class AsignacionUpdate(BaseModel):
    empleado: Optional[str] = None
    area: Optional[str] = None
    fecha_asignacion: Optional[date] = None
    fecha_devolucion: Optional[date] = None
    estado: Optional[str] = None
    observaciones: Optional[str] = None

    @field_validator("estado")
    @classmethod
    def validate_estado(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in ESTADOS_ASIGNACION_VALIDOS:
            raise ValueError("Estado de asignacion no permitido")
        return value

    @model_validator(mode="after")
    def validate_fechas(self):
        if (
            self.fecha_asignacion is not None
            and self.fecha_devolucion is not None
            and self.fecha_devolucion < self.fecha_asignacion
        ):
            raise ValueError("La fecha de devolucion no puede ser menor a la fecha de asignacion")
        return self


class MantenimientoCreate(BaseModel):
    activo_id: int
    tipo: str = TipoMantenimiento.PREVENTIVO.value
    descripcion: Optional[str] = None
    proveedor: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    costo: Optional[Decimal] = Field(default=None, ge=0)
    estado: str = EstadoMantenimiento.PENDIENTE.value
    observaciones: Optional[str] = None

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, value: str) -> str:
        if value not in TIPOS_MANTENIMIENTO_VALIDOS:
            raise ValueError("Tipo de mantenimiento no permitido")
        return value

    @field_validator("estado")
    @classmethod
    def validate_estado(cls, value: str) -> str:
        if value not in ESTADOS_MANTENIMIENTO_VALIDOS:
            raise ValueError("Estado de mantenimiento no permitido")
        return value

    @model_validator(mode="after")
    def validate_fechas(self):
        if (
            self.fecha_inicio is not None
            and self.fecha_fin is not None
            and self.fecha_fin < self.fecha_inicio
        ):
            raise ValueError("La fecha fin no puede ser menor a la fecha inicio")
        return self


class MantenimientoUpdate(BaseModel):
    tipo: Optional[str] = None
    descripcion: Optional[str] = None
    proveedor: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    costo: Optional[Decimal] = Field(default=None, ge=0)
    estado: Optional[str] = None
    observaciones: Optional[str] = None

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in TIPOS_MANTENIMIENTO_VALIDOS:
            raise ValueError("Tipo de mantenimiento no permitido")
        return value

    @field_validator("estado")
    @classmethod
    def validate_estado(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in ESTADOS_MANTENIMIENTO_VALIDOS:
            raise ValueError("Estado de mantenimiento no permitido")
        return value

    @model_validator(mode="after")
    def validate_fechas(self):
        if (
            self.fecha_inicio is not None
            and self.fecha_fin is not None
            and self.fecha_fin < self.fecha_inicio
        ):
            raise ValueError("La fecha fin no puede ser menor a la fecha inicio")
        return self


class BajaCreate(BaseModel):
    activo_id: int
    motivo: str = MotivoBaja.OBSOLESCENCIA.value
    fecha_baja: Optional[date] = None
    valor_residual_real: Optional[Decimal] = Field(default=None, ge=0)
    observaciones: Optional[str] = None

    @field_validator("motivo")
    @classmethod
    def validate_motivo(cls, value: str) -> str:
        if value not in MOTIVOS_BAJA_VALIDOS:
            raise ValueError("Motivo de baja no permitido")
        return value


__all__ = [
    "ActivoCreate",
    "ActivoUpdate",
    "AsignacionCreate",
    "AsignacionUpdate",
    "BajaCreate",
    "DepreciarRequest",
    "MantenimientoCreate",
    "MantenimientoUpdate",
]

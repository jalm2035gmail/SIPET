from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


# ── Activo ────────────────────────────────────────────────────────────────────

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
    metodo_depreciacion: str = "linea_recta"
    ubicacion: Optional[str] = None
    responsable: Optional[str] = None
    estado: str = "activo"
    descripcion: Optional[str] = None


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


# ── Depreciación ──────────────────────────────────────────────────────────────

class DepreciarRequest(BaseModel):
    periodo: Optional[str] = None          # YYYY-MM; si es None se usa mes actual
    tasa_saldo_decreciente: Optional[Decimal] = None   # solo para saldo_decreciente


# ── Asignación ────────────────────────────────────────────────────────────────

class AsignacionCreate(BaseModel):
    activo_id: int
    empleado: Optional[str] = None
    area: Optional[str] = None
    fecha_asignacion: Optional[date] = None
    fecha_devolucion: Optional[date] = None
    estado: str = "vigente"
    observaciones: Optional[str] = None


class AsignacionUpdate(BaseModel):
    empleado: Optional[str] = None
    area: Optional[str] = None
    fecha_asignacion: Optional[date] = None
    fecha_devolucion: Optional[date] = None
    estado: Optional[str] = None
    observaciones: Optional[str] = None


# ── Mantenimiento ─────────────────────────────────────────────────────────────

class MantenimientoCreate(BaseModel):
    activo_id: int
    tipo: str = "preventivo"
    descripcion: Optional[str] = None
    proveedor: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    costo: Optional[Decimal] = Field(default=None, ge=0)
    estado: str = "pendiente"
    observaciones: Optional[str] = None


class MantenimientoUpdate(BaseModel):
    tipo: Optional[str] = None
    descripcion: Optional[str] = None
    proveedor: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    costo: Optional[Decimal] = Field(default=None, ge=0)
    estado: Optional[str] = None
    observaciones: Optional[str] = None


# ── Baja ──────────────────────────────────────────────────────────────────────

class BajaCreate(BaseModel):
    activo_id: int
    motivo: str = "obsolescencia"
    fecha_baja: Optional[date] = None
    valor_residual_real: Optional[Decimal] = Field(default=None, ge=0)
    observaciones: Optional[str] = None

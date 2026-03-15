from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from fastapi_modulo.db import MAIN
from fastapi_modulo.modulos.activo_fijo.enums import (
    EstadoActivo,
    EstadoAsignacion,
    EstadoMantenimiento,
    MetodoDepreciacion,
    MotivoBaja,
    TipoMantenimiento,
)


class AfActivo(MAIN):
    __tablename__ = "af_activo"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(40), nullable=False, unique=True, index=True)
    nombre = Column(String(200), nullable=False)
    categoria = Column(String(80), nullable=True)
    marca = Column(String(80), nullable=True)
    modelo = Column(String(80), nullable=True)
    numero_serie = Column(String(100), nullable=True)
    proveedor = Column(String(150), nullable=True)
    fecha_adquisicion = Column(Date, nullable=True)
    valor_adquisicion = Column(Numeric(14, 2), nullable=False, default=0)
    valor_residual = Column(Numeric(14, 2), nullable=False, default=0)
    vida_util_meses = Column(Integer, nullable=False, default=60)
    metodo_depreciacion = Column(String(30), nullable=False, default=MetodoDepreciacion.LINEA_RECTA.value)
    valor_libro = Column(Numeric(14, 2), nullable=True)
    ubicacion = Column(String(150), nullable=True)
    responsable = Column(String(150), nullable=True)
    estado = Column(String(30), nullable=False, default=EstadoActivo.ACTIVO.value)
    descripcion = Column(Text, nullable=True)
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)
    actualizado_en = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    depreciaciones = relationship(
        "AfDepreciacion",
        back_populates="activo",
        cascade="all, delete-orphan",
    )
    asignaciones = relationship(
        "AfAsignacion",
        back_populates="activo",
        cascade="all, delete-orphan",
    )
    mantenimientos = relationship(
        "AfMantenimiento",
        back_populates="activo",
        cascade="all, delete-orphan",
    )
    baja = relationship(
        "AfBaja",
        back_populates="activo",
        uselist=False,
        cascade="all, delete-orphan",
    )


class AfDepreciacion(MAIN):
    __tablename__ = "af_depreciacion"
    __table_args__ = (
        UniqueConstraint("activo_id", "periodo", name="uq_af_dep_activo_periodo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    activo_id = Column(
        Integer,
        ForeignKey("af_activo.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    periodo = Column(String(7), nullable=False)
    metodo = Column(String(30), nullable=True)
    valor_depreciacion = Column(Numeric(14, 2), nullable=False)
    valor_libro_anterior = Column(Numeric(14, 2), nullable=False)
    valor_libro_nuevo = Column(Numeric(14, 2), nullable=False)
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)

    activo = relationship("AfActivo", back_populates="depreciaciones")


class AfAsignacion(MAIN):
    __tablename__ = "af_asignacion"

    id = Column(Integer, primary_key=True, index=True)
    activo_id = Column(
        Integer,
        ForeignKey("af_activo.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    empleado = Column(String(150), nullable=True)
    area = Column(String(150), nullable=True)
    fecha_asignacion = Column(Date, nullable=False, default=date.today)
    fecha_devolucion = Column(Date, nullable=True)
    estado = Column(String(20), nullable=False, default=EstadoAsignacion.VIGENTE.value)
    observaciones = Column(Text, nullable=True)
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)
    actualizado_en = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    activo = relationship("AfActivo", back_populates="asignaciones")


class AfMantenimiento(MAIN):
    __tablename__ = "af_mantenimiento"

    id = Column(Integer, primary_key=True, index=True)
    activo_id = Column(
        Integer,
        ForeignKey("af_activo.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo = Column(String(30), nullable=False, default=TipoMantenimiento.PREVENTIVO.value)
    descripcion = Column(Text, nullable=True)
    proveedor = Column(String(150), nullable=True)
    fecha_inicio = Column(Date, nullable=True)
    fecha_fin = Column(Date, nullable=True)
    costo = Column(Numeric(14, 2), nullable=True)
    estado = Column(String(20), nullable=False, default=EstadoMantenimiento.PENDIENTE.value)
    observaciones = Column(Text, nullable=True)
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)
    actualizado_en = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    activo = relationship("AfActivo", back_populates="mantenimientos")


class AfBaja(MAIN):
    __tablename__ = "af_baja"

    id = Column(Integer, primary_key=True, index=True)
    activo_id = Column(
        Integer,
        ForeignKey("af_activo.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    motivo = Column(String(50), nullable=False, default=MotivoBaja.OBSOLESCENCIA.value)
    fecha_baja = Column(Date, nullable=False, default=date.today)
    valor_residual_real = Column(Numeric(14, 2), nullable=True)
    observaciones = Column(Text, nullable=True)
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)

    activo = relationship("AfActivo", back_populates="baja")


__all__ = [
    "AfActivo",
    "AfAsignacion",
    "AfBaja",
    "AfDepreciacion",
    "AfMantenimiento",
]

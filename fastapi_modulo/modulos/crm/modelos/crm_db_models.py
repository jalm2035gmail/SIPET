from __future__ import annotations

from datetime import datetime, date

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from fastapi_modulo.db import MAIN


class CrmContacto(MAIN):
    __tablename__ = "crm_contactos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    email = Column(String(150), nullable=True, unique=True, index=True)
    telefono = Column(String(30), nullable=False, default="")
    empresa = Column(String(150), nullable=False, default="")
    puesto = Column(String(100), nullable=False, default="")
    tipo = Column(String(20), nullable=False, default="prospecto")  # prospecto / cliente / inactivo
    fuente = Column(String(50), nullable=False, default="manual")   # backend / referido / campania / manual
    notas = Column(Text, nullable=True)
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)
    actualizado_en = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class CrmOportunidad(MAIN):
    __tablename__ = "crm_oportunidades"

    id = Column(Integer, primary_key=True, index=True)
    contacto_id = Column(Integer, ForeignKey("crm_contactos.id"), nullable=False, index=True)
    nombre = Column(String(200), nullable=False)
    etapa = Column(String(30), nullable=False, default="prospecto")
    # prospecto / negociacion / propuesta / cerrado_ganado / cerrado_perdido
    valor_estimado = Column(Float, nullable=False, default=0.0)
    probabilidad = Column(Integer, nullable=False, default=0)   # 0–100
    fecha_cierre_est = Column(Date, nullable=True)
    responsable = Column(String(100), nullable=False, default="")
    descripcion = Column(Text, nullable=True)
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)
    actualizado_en = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class CrmActividad(MAIN):
    __tablename__ = "crm_actividades"

    id = Column(Integer, primary_key=True, index=True)
    contacto_id = Column(Integer, ForeignKey("crm_contactos.id"), nullable=True, index=True)
    oportunidad_id = Column(Integer, ForeignKey("crm_oportunidades.id"), nullable=True, index=True)
    tipo = Column(String(30), nullable=False, default="tarea")
    # llamada / reunion / email / visita / tarea
    titulo = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=True)
    fecha = Column(DateTime, nullable=False, default=datetime.utcnow)
    completada = Column(Boolean, nullable=False, default=False)
    responsable = Column(String(100), nullable=False, default="")
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)


class CrmNota(MAIN):
    __tablename__ = "crm_notas"

    id = Column(Integer, primary_key=True, index=True)
    contacto_id = Column(Integer, ForeignKey("crm_contactos.id"), nullable=True, index=True)
    oportunidad_id = Column(Integer, ForeignKey("crm_oportunidades.id"), nullable=True, index=True)
    contenido = Column(Text, nullable=False)
    autor = Column(String(100), nullable=False, default="")
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)


class CrmCampania(MAIN):
    __tablename__ = "crm_campanias"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    tipo = Column(String(50), nullable=False, default="email")
    # email / llamada / evento / promocion
    estado = Column(String(20), nullable=False, default="borrador")
    # borrador / activa / finalizada
    fecha_inicio = Column(Date, nullable=True)
    fecha_fin = Column(Date, nullable=True)
    descripcion = Column(Text, nullable=True)
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)


class CrmContactoCampania(MAIN):
    """Relación N:M entre contactos y campañas."""
    __tablename__ = "crm_contactos_campanias"
    __table_args__ = (
        UniqueConstraint("contacto_id", "campania_id", name="uq_crm_contacto_campania"),
    )

    id = Column(Integer, primary_key=True, index=True)
    contacto_id = Column(Integer, ForeignKey("crm_contactos.id"), nullable=False, index=True)
    campania_id = Column(Integer, ForeignKey("crm_campanias.id"), nullable=False, index=True)
    estado = Column(String(20), nullable=False, default="pendiente")
    # pendiente / contactado / convertido

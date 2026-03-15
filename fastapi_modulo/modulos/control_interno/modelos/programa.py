from __future__ import annotations

from datetime import datetime, date
from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from fastapi_modulo.db import MAIN


class ProgramaAnual(MAIN):
    """Encabezado del programa anual de control interno por año."""
    __tablename__ = "ci_programa_anual"
    __table_args__ = (
        UniqueConstraint("tenant_id", "anio", name="uq_ci_programa_anual_tenant_anio"),
        Index("ix_ci_programa_anual_tenant_id", "tenant_id"),
        Index("ix_ci_programa_anual_anio_estado", "anio", "estado"),
        Index("ix_ci_programa_anual_estado", "estado"),
    )

    id            = Column(Integer, primary_key=True, index=True)
    tenant_id     = Column(String(120), nullable=False, default="default")
    anio          = Column(Integer, nullable=False, index=True)
    nombre        = Column(String(200), nullable=False)
    descripcion   = Column(Text, nullable=True)
    estado        = Column(String(50), nullable=False, default="Borrador")
    # Borrador | Aprobado | En ejecución | Cerrado
    creado_en     = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    actividades   = relationship("ProgramaActividad", back_populates="programa",
                                 cascade="all, delete-orphan")


class ProgramaActividad(MAIN):
    """Actividad de control programada dentro de un programa anual."""
    __tablename__ = "ci_programa_actividad"
    __table_args__ = (
        Index("ix_ci_programa_actividad_tenant_id", "tenant_id"),
        Index("ix_ci_programa_actividad_estado", "estado"),
        Index("ix_ci_programa_actividad_responsable", "responsable"),
        Index("ix_ci_programa_actividad_fecha_fin_programada", "fecha_fin_programada"),
        Index("ix_ci_programa_actividad_programa_estado", "programa_id", "estado"),
    )

    id                      = Column(Integer, primary_key=True, index=True)
    tenant_id               = Column(String(120), nullable=False, default="default")
    programa_id             = Column(Integer, ForeignKey("ci_programa_anual.id",
                                                          ondelete="CASCADE"),
                                     nullable=False, index=True)
    control_id              = Column(Integer, ForeignKey("control_interno.id",
                                                          ondelete="SET NULL"),
                                     nullable=True, index=True)
    # Datos propios de la actividad programada
    descripcion             = Column(Text, nullable=True)
    responsable             = Column(String(150), nullable=True)
    fecha_inicio_programada = Column(Date, nullable=True)
    fecha_fin_programada    = Column(Date, nullable=True)
    fecha_inicio_real       = Column(Date, nullable=True)
    fecha_fin_real          = Column(Date, nullable=True)
    estado                  = Column(String(50), nullable=False, default="Programado")
    # Programado | En proceso | Completado | Diferido | Cancelado
    observaciones           = Column(Text, nullable=True)
    creado_en               = Column(DateTime, default=datetime.utcnow)
    actualizado_en          = Column(DateTime, default=datetime.utcnow,
                                     onupdate=datetime.utcnow)

    programa  = relationship("ProgramaAnual", back_populates="actividades")
    control   = relationship("ControlInterno", foreign_keys=[control_id])

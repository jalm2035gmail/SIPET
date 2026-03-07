from __future__ import annotations

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from fastapi_modulo.db import Base


class Hallazgo(Base):
    """Hallazgo de control interno detectado durante una evaluación."""
    __tablename__ = "ci_hallazgo"

    id                = Column(Integer, primary_key=True, index=True)
    # Vínculos opcionales
    evidencia_id      = Column(Integer,
                               ForeignKey("ci_evidencia.id", ondelete="SET NULL"),
                               nullable=True, index=True)
    actividad_id      = Column(Integer,
                               ForeignKey("ci_programa_actividad.id", ondelete="SET NULL"),
                               nullable=True, index=True)
    control_id        = Column(Integer,
                               ForeignKey("control_interno.id", ondelete="SET NULL"),
                               nullable=True, index=True)
    # Datos del hallazgo
    codigo            = Column(String(30),  nullable=True, index=True)
    titulo            = Column(String(200), nullable=False)
    descripcion       = Column(Text,        nullable=True)
    causa             = Column(Text,        nullable=True)
    efecto            = Column(Text,        nullable=True)
    componente_coso   = Column(String(100), nullable=True)
    nivel_riesgo      = Column(String(30),  nullable=False, default="Medio")
    # Bajo | Medio | Alto | Crítico
    estado            = Column(String(50),  nullable=False, default="Abierto")
    # Abierto | En atención | Subsanado | Cerrado
    fecha_deteccion   = Column(Date, nullable=True)
    fecha_limite      = Column(Date, nullable=True)
    responsable       = Column(String(150), nullable=True)
    creado_en         = Column(DateTime, default=datetime.utcnow)
    actualizado_en    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    evidencia  = relationship("Evidencia",         foreign_keys=[evidencia_id])
    actividad  = relationship("ProgramaActividad", foreign_keys=[actividad_id])
    control    = relationship("ControlInterno",    foreign_keys=[control_id])
    acciones   = relationship("AccionCorrectiva",  back_populates="hallazgo",
                              cascade="all, delete-orphan")


class AccionCorrectiva(Base):
    """Acción correctiva asociada a un hallazgo de control interno."""
    __tablename__ = "ci_accion_correctiva"

    id              = Column(Integer, primary_key=True, index=True)
    hallazgo_id     = Column(Integer,
                             ForeignKey("ci_hallazgo.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    descripcion     = Column(Text,        nullable=False)
    responsable     = Column(String(150), nullable=True)
    fecha_compromiso = Column(Date,       nullable=True)
    fecha_ejecucion  = Column(Date,       nullable=True)
    estado          = Column(String(50),  nullable=False, default="Pendiente")
    # Pendiente | En proceso | Ejecutada | Verificada | Cancelada
    evidencia_seguimiento = Column(Text,  nullable=True)
    creado_en       = Column(DateTime, default=datetime.utcnow)
    actualizado_en  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hallazgo = relationship("Hallazgo", back_populates="acciones")

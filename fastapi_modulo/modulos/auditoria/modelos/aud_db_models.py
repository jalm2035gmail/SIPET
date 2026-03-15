from __future__ import annotations

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint

from fastapi_modulo.db import MAIN


class AudAuditoria(MAIN):
    """Proyecto / encargo de auditoría."""
    __tablename__ = "aud_auditoria"

    id              = Column(Integer, primary_key=True, index=True)
    codigo          = Column(String(30),  nullable=False, unique=True, index=True)
    nombre          = Column(String(200), nullable=False)
    tipo            = Column(String(30),  nullable=False, default="interna")
    # interna | externa | especial | compliance
    area_auditada   = Column(String(150), nullable=True)
    objetivo        = Column(Text,        nullable=True)
    alcance         = Column(Text,        nullable=True)
    periodo         = Column(String(50),  nullable=True)
    fecha_inicio    = Column(Date,        nullable=True)
    fecha_fin_est   = Column(Date,        nullable=True)
    fecha_fin_real  = Column(Date,        nullable=True)
    estado          = Column(String(30),  nullable=False, default="planificada")
    # planificada | en_proceso | informe | cerrada
    responsable     = Column(String(150), nullable=True)
    auditor_lider   = Column(String(150), nullable=True)
    creado_en       = Column(DateTime, nullable=False, default=datetime.utcnow)
    actualizado_en  = Column(DateTime, nullable=False, default=datetime.utcnow,
                             onupdate=datetime.utcnow)

    hallazgos = relationship("AudHallazgo", back_populates="auditoria",
                             cascade="all, delete-orphan")


class AudHallazgo(MAIN):
    """Hallazgo detectado dentro de una auditoría."""
    __tablename__ = "aud_hallazgo"
    __table_args__ = (
        UniqueConstraint('auditoria_id', 'codigo', name='uq_auditoria_codigo_hallazgo'),
    )

    id              = Column(Integer, primary_key=True, index=True)
    auditoria_id    = Column(Integer, ForeignKey("aud_auditoria.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    codigo          = Column(String(30),  nullable=False, index=True)
    titulo          = Column(String(200), nullable=False)
    descripcion     = Column(Text,        nullable=True)
    criterio        = Column(Text,        nullable=True)   # Qué debería ser
    condicion       = Column(Text,        nullable=True)   # Qué es
    causa           = Column(Text,        nullable=True)
    efecto          = Column(Text,        nullable=True)
    nivel_riesgo    = Column(String(20),  nullable=False, default="medio", index=True)
    # bajo | medio | alto | critico
    estado          = Column(String(30),  nullable=False, default="abierto", index=True)
    # abierto | en_atencion | implementado | verificado | cerrado
    responsable     = Column(String(150), nullable=True)
    fecha_limite    = Column(Date,        nullable=True)
    creado_en       = Column(DateTime, nullable=False, default=datetime.utcnow)
    actualizado_en  = Column(DateTime, nullable=False, default=datetime.utcnow,
                             onupdate=datetime.utcnow)

    auditoria       = relationship("AudAuditoria", back_populates="hallazgos")
    recomendaciones = relationship("AudRecomendacion", back_populates="hallazgo",
                                   cascade="all, delete-orphan")


class AudRecomendacion(MAIN):
    """Recomendación vinculada a un hallazgo de auditoría."""
    __tablename__ = "aud_recomendacion"

    id                  = Column(Integer, primary_key=True, index=True)
    hallazgo_id         = Column(Integer, ForeignKey("aud_hallazgo.id", ondelete="CASCADE"),
                                 nullable=False, index=True)
    descripcion         = Column(Text,        nullable=False)
    responsable         = Column(String(150), nullable=True)
    prioridad           = Column(String(10),  nullable=False, default="media", index=True)
    # alta | media | baja
    fecha_compromiso    = Column(Date,        nullable=True, index=True)
    estado              = Column(String(20),  nullable=False, default="pendiente")
    # pendiente | en_proceso | implementada | rechazada
    porcentaje_avance   = Column(Integer,     nullable=False, default=0)
    creado_en           = Column(DateTime, nullable=False, default=datetime.utcnow)
    actualizado_en      = Column(DateTime, nullable=False, default=datetime.utcnow,
                                 onupdate=datetime.utcnow)

    hallazgo    = relationship("AudHallazgo", back_populates="recomendaciones")
    seguimiento = relationship("AudSeguimiento", back_populates="recomendacion",
                               cascade="all, delete-orphan")


class AudSeguimiento(MAIN):
    """Entrada de seguimiento sobre el avance de una recomendación."""
    __tablename__ = "aud_seguimiento"

    id                  = Column(Integer, primary_key=True, index=True)
    recomendacion_id    = Column(Integer, ForeignKey("aud_recomendacion.id", ondelete="CASCADE"),
                                 nullable=False, index=True)
    fecha               = Column(Date,        nullable=False, default=date.today)
    descripcion         = Column(Text,        nullable=False)
    porcentaje_avance   = Column(Integer,     nullable=False, default=0)
    evidencia           = Column(Text, nullable=True)   # Lista de evidencias (JSON/texto)
    evidencia_tipo      = Column(String(50), nullable=True)   # Tipo de archivo
    evidencia_nombre    = Column(String(200), nullable=True)  # Nombre original
    evidencia_url       = Column(String(300), nullable=True)  # URL de archivo
    evidencia_metadatos = Column(Text, nullable=True)         # Metadatos de carga (JSON)
    registrado_por      = Column(String(150), nullable=True)
    creado_en           = Column(DateTime, nullable=False, default=datetime.utcnow)

    recomendacion = relationship("AudRecomendacion", back_populates="seguimiento")

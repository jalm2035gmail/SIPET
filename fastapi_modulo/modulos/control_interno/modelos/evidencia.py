from __future__ import annotations

from datetime import datetime, date
from sqlalchemy import BigInteger, Column, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from fastapi_modulo.db import MAIN


class Evidencia(MAIN):
    """Evidencia documental de la ejecución de un control interno."""
    __tablename__ = "ci_evidencia"
    __table_args__ = (
        Index("ix_ci_evidencia_tenant_id", "tenant_id"),
        Index("ix_ci_evidencia_resultado_evaluacion", "resultado_evaluacion"),
        Index("ix_ci_evidencia_fecha_evidencia", "fecha_evidencia"),
        Index("ix_ci_evidencia_control_resultado", "control_id", "resultado_evaluacion"),
        Index("ix_ci_evidencia_actividad_resultado", "actividad_id", "resultado_evaluacion"),
    )

    id                   = Column(Integer, primary_key=True, index=True)
    tenant_id            = Column(String(120), nullable=False, default="default")
    # Vínculos opcionales
    actividad_id         = Column(Integer,
                                  ForeignKey("ci_programa_actividad.id", ondelete="SET NULL"),
                                  nullable=True, index=True)
    control_id           = Column(Integer,
                                  ForeignKey("control_interno.id", ondelete="SET NULL"),
                                  nullable=True, index=True)
    # Datos de la evidencia
    titulo               = Column(String(200), nullable=False)
    tipo                 = Column(String(50),  nullable=False, default="Documento")
    # Documento | Fotografía | Correo electrónico | Acta | Captura de pantalla | Otro
    descripcion          = Column(Text, nullable=True)
    fecha_evidencia      = Column(Date, nullable=True)
    # Resultado de la evaluación
    resultado_evaluacion = Column(String(50), nullable=False, default="Cumple")
    # Cumple | Cumple parcialmente | No cumple | Por evaluar
    observaciones        = Column(Text, nullable=True)
    # Archivo adjunto (opcional)
    archivo_nombre       = Column(String(255), nullable=True)
    archivo_uuid         = Column(String(64), nullable=True, index=True)
    archivo_nombre_original = Column(String(255), nullable=True)
    archivo_extension    = Column(String(20), nullable=True)
    archivo_ruta         = Column(String(500), nullable=True)
    archivo_mime         = Column(String(100), nullable=True)
    archivo_tamanio      = Column(BigInteger,  nullable=True)
    # Auditoría
    creado_en            = Column(DateTime, default=datetime.utcnow)
    actualizado_en       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    actividad = relationship("ProgramaActividad", foreign_keys=[actividad_id])
    control   = relationship("ControlInterno",    foreign_keys=[control_id])

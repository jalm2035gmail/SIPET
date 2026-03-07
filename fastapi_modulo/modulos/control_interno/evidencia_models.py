from __future__ import annotations

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, BigInteger, ForeignKey
from sqlalchemy.orm import relationship

from fastapi_modulo.db import Base


class Evidencia(Base):
    """Evidencia documental de la ejecución de un control interno."""
    __tablename__ = "ci_evidencia"

    id                   = Column(Integer, primary_key=True, index=True)
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
    archivo_ruta         = Column(String(500), nullable=True)
    archivo_mime         = Column(String(100), nullable=True)
    archivo_tamanio      = Column(BigInteger,  nullable=True)
    # Auditoría
    creado_en            = Column(DateTime, default=datetime.utcnow)
    actualizado_en       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    actividad = relationship("ProgramaActividad", foreign_keys=[actividad_id])
    control   = relationship("ControlInterno",    foreign_keys=[control_id])

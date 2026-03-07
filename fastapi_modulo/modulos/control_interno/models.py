from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from fastapi_modulo.db import Base


class ControlInterno(Base):
    __tablename__ = "control_interno"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(30), nullable=False, unique=True, index=True)
    nombre = Column(String(200), nullable=False)
    componente = Column(String(50), nullable=False)   # COSO
    area = Column(String(100), nullable=False)
    tipo_riesgo = Column(String(100), nullable=True)
    periodicidad = Column(String(30), nullable=False, default="Mensual")
    descripcion = Column(Text, nullable=True)
    normativa = Column(String(200), nullable=True)
    estado = Column(String(30), nullable=False, default="Activo")
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)
    actualizado_en = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

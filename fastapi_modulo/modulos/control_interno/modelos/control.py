from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, DateTime, Index, Integer, String, Text, UniqueConstraint
from fastapi_modulo.db import MAIN


class ControlInterno(MAIN):
    __tablename__ = "control_interno"
    __table_args__ = (
        UniqueConstraint("tenant_id", "codigo", name="uq_ci_control_tenant_codigo"),
        Index("ix_ci_control_estado", "estado"),
        Index("ix_ci_control_tenant_id", "tenant_id"),
        Index("ix_ci_control_area_estado", "area", "estado"),
        Index("ix_ci_control_componente_estado", "componente", "estado"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(120), nullable=False, default="default")
    codigo = Column(String(30), nullable=False, index=True)
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

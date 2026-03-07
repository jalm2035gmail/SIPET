from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint

from fastapi_modulo.db import Base


class MeEmpresa(Base):
    """Registro maestro de empresas en el sistema multiempresa."""

    __tablename__ = "me_empresa"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Identificadores
    codigo = Column(String(50), unique=True, nullable=False, index=True)
    """Código corto de la empresa, ej. 'AVANCOOP', 'POLOTITLAN'. Inmutable."""

    nombre = Column(String(200), nullable=False)
    """Razón social / nombre completo de la empresa."""

    tenant_id = Column(String(100), unique=True, nullable=False, index=True)
    """Slug que identifica la BD/sesión de esta empresa. Debe coincidir con el
    tenant_id del sistema de autenticación. Ej. 'avancoop', 'polotitlan'."""

    # Datos de contacto
    descripcion = Column(String(500))
    email_contacto = Column(String(200))
    telefono = Column(String(50))
    direccion = Column(String(400))
    rfc = Column(String(20))

    # Visual
    logo_filename = Column(String(300))
    """Nombre del archivo de logo almacenado en uploads/, ej. 'avancoop_logo.png'."""

    color_primario = Column(String(10), default="#0f172a")
    """Color HEX de la marca, usado en la vista de consolidado."""

    # Estado
    estado = Column(String(20), default="activa", nullable=False)
    """activa | inactiva"""

    # Auditoría
    creado_en = Column(DateTime, default=datetime.utcnow, nullable=False)
    actualizado_en = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_MAIN
from sqlalchemy.sql import func

MAIN = declarative_MAIN()


class MAINModel(MAIN):
    """Modelo MAIN con campos comunes"""
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(Integer, nullable=True)  # ID del usuario que creó
    updated_by = Column(Integer, nullable=True)  # ID del usuario que actualizó

    def to_dict(self) -> dict:
        """Convierte modelo a diccionario"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    def update(self, **kwargs: Any) -> None:
        """Actualiza atributos del modelo"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def soft_delete(self) -> None:
        """Eliminación lógica"""
        self.is_active = False
        self.updated_at = datetime.utcnow()

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, field_validator


class EmpresaCreate(BaseModel):
    codigo: str
    nombre: str
    tenant_id: str
    descripcion: Optional[str] = None
    email_contacto: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    rfc: Optional[str] = None
    color_primario: Optional[str] = "#0f172a"
    estado: Optional[str] = "activa"

    @field_validator("codigo")
    @classmethod
    def codigo_slug(cls, v: str) -> str:
        import re
        clean = re.sub(r"[^A-Za-z0-9_-]", "", v.strip().upper())
        if not clean:
            raise ValueError("El código solo puede contener letras, números, guiones y guiones bajos")
        return clean

    @field_validator("tenant_id")
    @classmethod
    def tenant_slug(cls, v: str) -> str:
        import re
        clean = re.sub(r"[^a-z0-9._-]", "-", v.strip().lower()).strip("-._")
        if not clean:
            raise ValueError("tenant_id inválido")
        return clean


class EmpresaUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    email_contacto: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    rfc: Optional[str] = None
    color_primario: Optional[str] = None
    estado: Optional[str] = None

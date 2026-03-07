from __future__ import annotations

import mimetypes
import os
import pathlib
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError

from fastapi_modulo.db import Base, SessionLocal, engine
from fastapi_modulo.modulos.multiempresa.me_db_models import MeEmpresa

_ME_TABLES = [MeEmpresa.__table__]

UPLOADS_DIR = pathlib.Path(__file__).parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def ensure_me_schema() -> None:
    Base.metadata.create_all(bind=engine, tables=_ME_TABLES, checkfirst=True)


def _db():
    ensure_me_schema()
    return SessionLocal()


# ── Serializer ────────────────────────────────────────────────────────────────

def _empresa_dict(obj: MeEmpresa) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "codigo": obj.codigo,
        "nombre": obj.nombre,
        "tenant_id": obj.tenant_id,
        "descripcion": obj.descripcion,
        "email_contacto": obj.email_contacto,
        "telefono": obj.telefono,
        "direccion": obj.direccion,
        "rfc": obj.rfc,
        "color_primario": obj.color_primario or "#0f172a",
        "estado": obj.estado,
        "logo_filename": obj.logo_filename,
        "logo_url": f"/api/multiempresa/logos/{obj.logo_filename}" if obj.logo_filename else None,
        "creado_en": obj.creado_en.isoformat() if obj.creado_en else None,
        "actualizado_en": obj.actualizado_en.isoformat() if obj.actualizado_en else None,
    }


# ── CRUD ──────────────────────────────────────────────────────────────────────

def list_empresas(estado: Optional[str] = None, tenant_filter: Optional[str] = None) -> List[Dict]:
    db = _db()
    try:
        q = db.query(MeEmpresa)
        if tenant_filter:
            q = q.filter(MeEmpresa.tenant_id == tenant_filter)
        if estado:
            q = q.filter(MeEmpresa.estado == estado)
        return [_empresa_dict(o) for o in q.order_by(MeEmpresa.nombre).all()]
    finally:
        db.close()


def get_empresa(empresa_id: int, tenant_filter: Optional[str] = None) -> Optional[Dict]:
    db = _db()
    try:
        q = db.query(MeEmpresa).filter(MeEmpresa.id == empresa_id)
        if tenant_filter:
            q = q.filter(MeEmpresa.tenant_id == tenant_filter)
        obj = q.first()
        return _empresa_dict(obj) if obj else None
    finally:
        db.close()


def get_empresa_by_tenant(tenant_id: str) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(MeEmpresa).filter(MeEmpresa.tenant_id == tenant_id).first()
        return _empresa_dict(obj) if obj else None
    finally:
        db.close()


def create_empresa(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        obj = MeEmpresa(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return _empresa_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_empresa(empresa_id: int, data: Dict[str, Any], tenant_filter: Optional[str] = None) -> Optional[Dict]:
    db = _db()
    try:
        q = db.query(MeEmpresa).filter(MeEmpresa.id == empresa_id)
        if tenant_filter:
            q = q.filter(MeEmpresa.tenant_id == tenant_filter)
        obj = q.first()
        if not obj:
            return None
        data["actualizado_en"] = datetime.utcnow()
        for k, v in data.items():
            setattr(obj, k, v)
        db.commit()
        db.refresh(obj)
        return _empresa_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_empresa(empresa_id: int, tenant_filter: Optional[str] = None) -> bool:
    db = _db()
    try:
        q = db.query(MeEmpresa).filter(MeEmpresa.id == empresa_id)
        if tenant_filter:
            q = q.filter(MeEmpresa.tenant_id == tenant_filter)
        obj = q.first()
        if not obj:
            return False
        # Remove logo file if present
        if obj.logo_filename:
            _remove_logo_file(obj.logo_filename)
        db.delete(obj)
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


# ── Logo management ───────────────────────────────────────────────────────────

def _remove_logo_file(filename: str) -> None:
    path = UPLOADS_DIR / filename
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


_ALLOWED_LOGO_MIME = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"}
_MAX_LOGO_BYTES = 2 * 1024 * 1024  # 2 MB


def save_logo(
    empresa_id: int,
    filename: str,
    data: bytes,
    content_type: str,
    tenant_filter: Optional[str] = None,
) -> Optional[Dict]:
    """Persist the logo file and update the empresa record. Returns updated empresa dict."""
    if content_type not in _ALLOWED_LOGO_MIME:
        raise ValueError(f"Tipo de archivo no soportado: {content_type}")
    if len(data) > _MAX_LOGO_BYTES:
        raise ValueError("El archivo excede el tamaño máximo de 2 MB")

    db = _db()
    try:
        q = db.query(MeEmpresa).filter(MeEmpresa.id == empresa_id)
        if tenant_filter:
            q = q.filter(MeEmpresa.tenant_id == tenant_filter)
        obj = q.first()
        if not obj:
            return None

        # Remove old logo
        if obj.logo_filename:
            _remove_logo_file(obj.logo_filename)

        # Determine extension
        ext = mimetypes.guess_extension(content_type) or ".bin"
        # Normalise common aliases
        ext = {".jpe": ".jpg", ".jpeg": ".jpg"}.get(ext, ext)
        safe_codigo = "".join(c for c in obj.codigo if c.isalnum() or c in "-_")
        new_filename = f"{safe_codigo.lower()}_logo{ext}"

        file_path = UPLOADS_DIR / new_filename
        file_path.write_bytes(data)

        obj.logo_filename = new_filename
        obj.actualizado_en = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return _empresa_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def get_logo_path(filename: str) -> Optional[pathlib.Path]:
    """Return the absolute Path of a logo file if it exists, otherwise None."""
    # Prevent path traversal
    safe = pathlib.Path(filename).name
    path = UPLOADS_DIR / safe
    return path if path.exists() else None


# ── Consolidado / KPIs ────────────────────────────────────────────────────────

def get_me_consolidado(tenant_filter: Optional[str] = None) -> Dict[str, Any]:
    """Return aggregated statistics. With tenant_filter, scoped to a single empresa."""
    db = _db()
    try:
        q = db.query(MeEmpresa)
        if tenant_filter:
            q = q.filter(MeEmpresa.tenant_id == tenant_filter)
        all_empresas = q.order_by(MeEmpresa.nombre).all()
        total = len(all_empresas)
        activas = sum(1 for e in all_empresas if e.estado == "activa")
        inactivas = total - activas
        con_logo = sum(1 for e in all_empresas if e.logo_filename)

        return {
            "total_empresas": total,
            "empresas_activas": activas,
            "empresas_inactivas": inactivas,
            "empresas_con_logo": con_logo,
            "empresas": [_empresa_dict(e) for e in all_empresas],
        }
    finally:
        db.close()

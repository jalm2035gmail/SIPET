from __future__ import annotations

import json
import mimetypes
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError

from fastapi_modulo.modulos.capacitacion.controladores.utils import STATIC_DIR
from fastapi_modulo.modulos.capacitacion.repositorios import archivos_repository as repo

UPLOADS_DIR = STATIC_DIR / "uploads"

ALLOWED_EXTENSIONS = {
    "documento": {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".txt"},
    "video": {".mp4", ".mov", ".m4v", ".webm"},
    "imagen": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"},
    "audio": {".mp3", ".wav", ".ogg", ".m4a"},
    "adjunto_evaluacion": {".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg", ".zip"},
    "evidencia": {".pdf", ".png", ".jpg", ".jpeg", ".mp4", ".mov", ".mp3", ".wav", ".zip"},
}


def _dt(value):
    if value is None:
        return None
    return value.isoformat() if isinstance(value, datetime) else str(value)


def _archivo_dict(obj):
    return {
        "id": obj.id,
        "entidad_tipo": obj.entidad_tipo,
        "entidad_id": obj.entidad_id,
        "categoria": obj.categoria,
        "nombre_original": obj.nombre_original,
        "nombre_archivo": obj.nombre_archivo,
        "ruta_relativa": obj.ruta_relativa,
        "public_url": obj.public_url,
        "mime_type": obj.mime_type,
        "size_bytes": obj.size_bytes,
        "creado_por": obj.creado_por,
        "metadata": json.loads(obj.metadata_json) if obj.metadata_json else {},
        "creado_en": _dt(obj.creado_en),
    }


def _safe_ext(filename):
    return Path(filename or "").suffix.lower()


def _validate_file(upload: UploadFile, categoria: str):
    ext = _safe_ext(upload.filename)
    allowed = ALLOWED_EXTENSIONS.get(categoria, set())
    if allowed and ext not in allowed:
        raise ValueError("Tipo de archivo no permitido")
    return ext


def _target_path(tenant_id: str, categoria: str, ext: str):
    subdir = UPLOADS_DIR / tenant_id / categoria
    subdir.mkdir(parents=True, exist_ok=True)
    filename = uuid.uuid4().hex + ext
    return subdir / filename


def save_upload(upload: UploadFile, *, categoria: str, tenant_id: str = "default", entidad_tipo: str | None = None, entidad_id: int | None = None, actor_key: str | None = None, metadata: dict | None = None):
    db = repo.get_db()
    try:
        ext = _validate_file(upload, categoria)
        target = _target_path(tenant_id, categoria, ext)
        size = 0
        with open(target, "wb") as fh:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                fh.write(chunk)
        rel = target.relative_to(STATIC_DIR).as_posix()
        mime = upload.content_type or mimetypes.guess_type(upload.filename or "")[0] or "application/octet-stream"
        obj = repo.create_archivo(
            db,
            {
                "tenant_id": tenant_id,
                "entidad_tipo": entidad_tipo,
                "entidad_id": entidad_id,
                "categoria": categoria,
                "nombre_original": upload.filename or target.name,
                "nombre_archivo": target.name,
                "ruta_relativa": rel,
                "public_url": "/capacitacion/assets/" + rel,
                "mime_type": mime,
                "size_bytes": size,
                "creado_por": actor_key,
                "metadata_json": json.dumps(metadata or {}),
                "creado_en": datetime.utcnow(),
            },
        )
        db.commit()
        db.refresh(obj)
        return _archivo_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        try:
            upload.file.close()
        except Exception:
            pass
        db.close()


def list_archivos(entidad_tipo=None, entidad_id=None, categoria=None):
    db = repo.get_db()
    try:
        return [_archivo_dict(item) for item in repo.list_archivos(db, entidad_tipo, entidad_id, categoria)]
    finally:
        db.close()

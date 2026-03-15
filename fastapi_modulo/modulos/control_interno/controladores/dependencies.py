from __future__ import annotations

import os
import re
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, Request, UploadFile

from fastapi_modulo.modulos.control_interno.repositorios.base import set_current_tenant
from fastapi_modulo.modulos.control_interno.servicios.evidencia_service import UPLOAD_DIR

MAX_FILE_SIZE = 25 * 1024 * 1024
ALLOWED_FILE_TYPES = {
    ".pdf": {"mime": "application/pdf"},
    ".doc": {"mime": "application/msword"},
    ".docx": {"mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".xls": {"mime": "application/vnd.ms-excel"},
    ".xlsx": {"mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    ".jpg": {"mime": "image/jpeg"},
    ".jpeg": {"mime": "image/jpeg"},
    ".png": {"mime": "image/png"},
    ".txt": {"mime": "text/plain"},
}


def sanitize_filename(name: str) -> str:
    base = os.path.splitext(name)[0]
    return re.sub(r"[^\w\-]", "_", base)[:80]


def _detect_mime(data: bytes, extension: str) -> str | None:
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1") and extension in {".doc", ".xls"}:
        return ALLOWED_FILE_TYPES[extension]["mime"]
    if data.startswith(b"PK\x03\x04") and extension in {".docx", ".xlsx"}:
        return ALLOWED_FILE_TYPES[extension]["mime"]
    if extension == ".txt":
        try:
            data.decode("utf-8")
            return "text/plain"
        except UnicodeDecodeError:
            return None
    return None


def _build_storage_path(extension: str) -> tuple[str, str]:
    year = datetime.utcnow().strftime("%Y")
    file_uuid = uuid.uuid4().hex
    storage_dir = Path(UPLOAD_DIR) / year
    storage_dir.mkdir(parents=True, exist_ok=True)
    return file_uuid, str(storage_dir / f"{file_uuid}{extension}")


async def save_uploaded_evidence(upload: UploadFile) -> dict[str, object]:
    data = await upload.read()
    if not data:
        raise HTTPException(status_code=400, detail="El archivo esta vacio.")
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="El archivo supera los 25 MB permitidos.")
    ext = os.path.splitext(upload.filename or "")[1].lower()
    if ext not in ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=415, detail="Extension de archivo no permitida.")
    declared_mime = (upload.content_type or "application/octet-stream").strip().lower()
    real_mime = _detect_mime(data, ext)
    if not real_mime:
        raise HTTPException(status_code=415, detail="No se pudo validar el tipo real del archivo.")
    allowed_mime = ALLOWED_FILE_TYPES[ext]["mime"]
    if real_mime != allowed_mime or declared_mime not in {allowed_mime, "application/octet-stream"}:
        raise HTTPException(status_code=415, detail="El tipo MIME del archivo no coincide con su contenido.")
    original_name = upload.filename or "evidencia"
    safe_name = sanitize_filename(original_name)
    file_uuid, path = _build_storage_path(ext)
    with open(path, "wb") as file_handle:
        file_handle.write(data)
    return {
        "archivo_nombre": safe_name,
        "archivo_uuid": file_uuid,
        "archivo_nombre_original": original_name,
        "archivo_extension": ext,
        "archivo_ruta": path,
        "archivo_mime": real_mime,
        "archivo_tamanio": len(data),
    }


def bind_tenant_context(request: Request) -> None:
    from fastapi_modulo import main as core

    tenant_id = getattr(core, "get_current_tenant")(request)
    set_current_tenant(tenant_id)


__all__ = ["ALLOWED_FILE_TYPES", "MAX_FILE_SIZE", "bind_tenant_context", "sanitize_filename", "save_uploaded_evidence"]

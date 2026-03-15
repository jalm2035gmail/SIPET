"""Adaptadores locales para dependencias compartidas del módulo."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func

from fastapi_modulo.db import SessionLocal

CAP_ADMIN_ROLES = {"superadministrador", "superadmin", "administrador", "administrador_multiempresa"}


def normalize_tenant_id(value: Optional[str]) -> str:
    raw = str(value or "").strip().lower()
    cleaned = []
    for ch in raw:
        if ch.isalnum() or ch in "._-":
            cleaned.append(ch)
        else:
            cleaned.append("-")
    normalized = "".join(cleaned).strip("-._")
    return normalized or "default"


def current_role(request: Request) -> str:
    return str(
        getattr(request.state, "user_role", None)
        or request.cookies.get("user_role")
        or request.cookies.get("role")
        or request.cookies.get("rol")
        or ""
    ).strip().lower()


def is_admin_or_superadmin(request: Request) -> bool:
    return current_role(request) in CAP_ADMIN_ROLES


def get_current_tenant(request: Request) -> str:
    tenant = getattr(request.state, "tenant_id", None)
    if tenant:
        return normalize_tenant_id(tenant)
    cookie_tenant = request.cookies.get("tenant_id")
    if cookie_tenant:
        return normalize_tenant_id(cookie_tenant)
    header_tenant = request.headers.get("x-tenant-id")
    if header_tenant and is_admin_or_superadmin(request):
        return normalize_tenant_id(header_tenant)
    return normalize_tenant_id("default")


def load_colab_meta() -> dict[str, Any]:
    app_env = (os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "development").strip().lower()
    sipet_data_dir = (os.environ.get("SIPET_DATA_DIR") or os.path.expanduser("~/.sipet/data")).strip()
    runtime_dir = (os.environ.get("RUNTIME_STORE_DIR") or os.path.join(sipet_data_dir, "runtime_store", app_env)).strip()
    meta_path = os.environ.get("COLAB_META_PATH") or os.path.join(runtime_dir, "colaboradores_meta.json")
    try:
        with open(meta_path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def find_user_row_by_session_name(session_name: str) -> Optional[Dict[str, Any]]:
    value = str(session_name or "").strip().lower()
    if not value:
        return None
    try:
        from fastapi_modulo.main import Usuario, _decrypt_sensitive, _sensitive_lookup_hash
    except Exception:
        return None

    db = SessionLocal()
    try:
        lookup_hash = _sensitive_lookup_hash(value)
        user = (
            db.query(Usuario)
            .filter((Usuario.usuario_hash == lookup_hash) | (Usuario.correo_hash == lookup_hash))
            .first()
        )
        if not user:
            user = db.query(Usuario).filter(func.lower(Usuario.full_name) == value).first()
        if not user:
            return None
        return {
            "id": user.id,
            "username": _decrypt_sensitive(user.usuario) or "",
            "full_name": user.full_name or "",
            "role": user.role or "",
        }
    finally:
        db.close()


def current_session_name(request: Request) -> str:
    session_name = str(
        getattr(request.state, "user_name", None)
        or request.cookies.get("user_name")
        or request.cookies.get("username")
        or request.cookies.get("usuario")
        or request.cookies.get("email")
        or ""
    ).strip()
    if session_name:
        return session_name
    try:
        from fastapi_modulo.main import AUTH_COOKIE_NAME, _read_session_cookie

        session_token = request.cookies.get(AUTH_COOKIE_NAME, "")
        session_data = _read_session_cookie(session_token) if session_token else None
        if isinstance(session_data, dict):
            return str(session_data.get("username") or "").strip()
    except Exception:
        pass
    return ""


def current_user_key(request: Request) -> str:
    try:
        from fastapi_modulo.main import _current_user_record
    except Exception:
        fallback = current_session_name(request)
        if fallback:
            return fallback
        raise HTTPException(status_code=401, detail="No autenticado")

    db = SessionLocal()
    try:
        user = _current_user_record(request, db)
        if user:
            return str(user.id)
    finally:
        db.close()

    fallback = current_session_name(request)
    if fallback:
        return fallback
    raise HTTPException(status_code=401, detail="No autenticado")


def user_has_capacitacion_access(request: Request) -> bool:
    if is_admin_or_superadmin(request):
        return True
    session_name = current_session_name(request)
    if not session_name:
        return False
    row = find_user_row_by_session_name(session_name)
    if row:
        meta = load_colab_meta()
        entry = meta.get(str(row.get("id")), {}) if isinstance(meta, dict) else {}
        app_access = entry.get("app_access", []) if isinstance(entry, dict) else []
        return isinstance(app_access, list) and "Capacitacion" in [str(item).strip() for item in app_access]
    return True


def require_access(request: Request) -> None:
    if user_has_capacitacion_access(request):
        return
    raise HTTPException(status_code=403, detail="Acceso restringido al módulo Capacitación")


def render_backend_page_safe(
    request: Request,
    *,
    title: str,
    description: str,
    content: str,
    hide_floating_actions: bool = True,
    show_page_header: bool = False,
    section_label: str = "Capacitación",
) -> HTMLResponse:
    try:
        from fastapi_modulo.main import render_backend_page

        return render_backend_page(
            request,
            title=title,
            description=description,
            content=content,
            hide_floating_actions=hide_floating_actions,
            show_page_header=show_page_header,
            section_label=section_label,
        )
    except Exception:
        return HTMLResponse(content=content)


def list_live_course_surveys_safe(curso_id: int, tenant_id: str) -> list[dict[str, Any]]:
    try:
        from fastapi_modulo.modulos.encuestas.modelos.encuestas_store import list_live_course_surveys

        rows = list_live_course_surveys(curso_id, tenant_id)
        return rows if isinstance(rows, list) else []
    except Exception:
        return []

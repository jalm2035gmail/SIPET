import os
import re
import json
import base64
import sqlite3
import glob
import secrets
import hashlib
import hmac
import time
import unicodedata
import shutil
import shlex
import subprocess
from datetime import datetime, date as Date, timedelta
from pathlib import Path
from urllib.parse import quote_plus
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from dotenv import load_dotenv
from fastapi import Request, UploadFile, HTTPException
from fastapi import File
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Text, JSON, UniqueConstraint, func, inspect
from sqlalchemy.orm import declarative_base, relationship
from cryptography.fernet import Fernet, InvalidToken
from textwrap import dedent
from html import escape
from fastapi_modulo.module_registry import (
    get_active_app_access_names,
    get_active_module_keys,
    is_app_access_enabled,
    list_system_app_access_options,
    list_modules_payload,
    register_enabled_routers,
)
from fastapi_modulo import db as core_db
from fastapi_modulo.db import DepartamentoOrganizacional
from fastapi_modulo.modulos.backend.controladores.backend_shell import (
    _render_backend_MAIN,
    backend_screen,
    enforce_backend_login,
    render_backend_page,
)
from fastapi import Response, Form, Body
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi import Depends
from typing import Set

import struct
import ipaddress
import httpx
templates = Jinja2Templates(directory="fastapi_modulo")
date = Date

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

HIDDEN_SYSTEM_USERS = {"0konomiyaki"}
PROCESS_STARTED_AT = time.time()
SIPET_VERSION = "1.00.00"
SYSTEM_APP_ACCESS_OPTIONS = tuple(list_system_app_access_options())
APP_ENV_DEFAULT = (os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "development").strip().lower()


DEFAULT_SIPET_DATA_DIR = (os.environ.get("SIPET_DATA_DIR") or os.path.expanduser("~/.sipet/data")).strip()
RUNTIME_STORE_DIR = (os.environ.get("RUNTIME_STORE_DIR") or f"fastapi_modulo/runtime_store/{APP_ENV_DEFAULT}").strip()
IDENTIDAD_LOGIN_CONFIG_PATH = (
    os.environ.get("IDENTIDAD_LOGIN_CONFIG_PATH")
    or "fastapi_modulo/identidad_login.json"
).strip()
IDENTIDAD_LOGIN_IMAGE_DIR = "fastapi_modulo/templates/imagenes"
DOCUMENTS_UPLOAD_DIR = "fastapi_modulo/uploads/documentos"
DEFAULT_LOGIN_IDENTITY = {
    "favicon_filename": "icon.png",
    "logo_filename": "icon.png",
    "desktop_bg_filename": "fondo.jpg",
    "mobile_bg_filename": "movil.jpg",
    "company_short_name": "AVAN",
    "login_message": "Incrementando el nivel de eficiencia",
    "menu_position": "arriba",
}
AUTH_COOKIE_NAME = "auth_session"
SIPET_PREMIUM_UI_TEMPLATE_CSS = dedent("""
    .sipet-ui-template .table-excel {
        width: 100% !important;
        border-collapse: collapse !important;
        border-spacing: 0 !important;
        background: transparent !important;
    }
    .sipet-ui-template .table-excel thead th {
        text-align: left !important;
        font-size: 13px !important;
        letter-spacing: .08em;
        text-transform: uppercase;
        color: rgba(15,23,42,.75) !important;
        background: linear-gradient(180deg, rgba(255,255,255,.92), rgba(255,255,255,.74)) !important;
        border-bottom: 1px solid rgba(15,23,42,.10) !important;
        border-right: 1px solid rgba(15,23,42,.10) !important;
        padding: 14px 16px !important;
    }
    .sipet-ui-template .table-excel thead th:last-child {
        border-right: 0 !important;
    }
    .sipet-ui-template .table-excel tbody td {
        border-bottom: 1px solid rgba(15,23,42,.08) !important;
        border-right: 1px solid rgba(15,23,42,.10) !important;
        background: #ffffff !important;
        padding: 12px !important;
        vertical-align: middle !important;
    }
    .sipet-ui-template .table-excel tbody td:last-child {
        border-right: 0 !important;
    }
    .sipet-ui-template .table-excel tbody tr:nth-child(even) td {
        background: #ecfdf3 !important;
    }
    .sipet-ui-template .table-excel tbody tr:hover td {
        background: #dcfce7 !important;
    }
    .sipet-ui-template .table-excel tbody tr:last-child td {
        border-bottom: 0 !important;
    }
    .sipet-ui-template .table-excel--compact tbody td {
        padding: 8px !important;
    }
    .sipet-ui-template .table-excel--compact tbody td.year {
        font-size: 16px !important;
        font-weight: 750 !important;
        letter-spacing: 0 !important;
        padding: 8px 12px !important;
    }
    .sipet-ui-template .table-excel--compact .macro-input {
        min-height: 34px !important;
        padding: 8px 10px !important;
    }
    .sipet-ui-template .table-excel .table-input {
        width: 100%;
        height: 36px;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 0 10px;
        background: #ffffff;
        color: #0f172a;
    }
    .sipet-ui-template .table-excel .table-input.num {
        text-align: right;
        font-variant-numeric: tabular-nums;
    }
    .sipet-ui-template .table-excel .table-actions-cell,
    .sipet-ui-template .table-excel .table-actions-head {
        text-align: center;
    }
    .sipet-ui-template .table-excel .table-add-btn {
        width: 34px;
        height: 34px;
        border-radius: 8px;
        border: 1px solid #0f172a;
        background: #ffffff;
        color: #0f172a;
        font-size: 1.1rem;
        font-weight: 700;
        cursor: pointer;
    }
    .sipet-ui-template .table-excel .table-delete-btn {
        width: 34px;
        height: 34px;
        border-radius: 8px;
        border: 1px solid #991b1b;
        background: #ffffff;
        color: #991b1b;
        font-size: 1rem;
        font-weight: 700;
        cursor: pointer;
    }
    .sipet-ui-template .table-primary-btn {
        height: 36px;
        padding: 0 12px;
        border-radius: 8px;
        border: 1px solid #0f172a;
        background: #0f172a;
        color: #ffffff;
        font-size: 0.95rem;
        font-weight: 600;
        cursor: pointer;
    }
    .sipet-ui-template .table-excel .ifb-row-label {
        font-weight: 600;
        color: #0f172a;
    }
    .sipet-ui-template .table-excel .ifb-validation-cell {
        padding: 10px;
    }
    .sipet-ui-template .table-excel .ifb-validation-output {
        font-size: 0.85rem;
        line-height: 1.35;
    }
    .sipet-ui-template .dg-grid > label {
        border: 1px solid rgba(15, 23, 42, .10);
        border-radius: 14px;
        padding: 10px;
    }
    .sipet-ui-template .dg-grid > label:nth-child(odd) {
        background: #ffffff;
    }
    .sipet-ui-template .dg-grid > label:nth-child(even) {
        background: #ecfdf3;
    }
""")


def _require_secret(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if value:
        return value
    fallback_names = {
        "AUTH_COOKIE_SECRET": ["SENSITIVE_DATA_SECRET", "SECRET_KEY", "SESSION_SECRET", "JWT_SECRET"],
    }
    for candidate in fallback_names.get(name, []):
        candidate_value = (os.environ.get(candidate) or "").strip()
        if candidate_value:
            print(f"[secrets] {name} no definida; usando {candidate} como fallback.")
            return candidate_value
    strict = (os.environ.get("STRICT_REQUIRED_SECRETS") or "").strip().lower() in {"1", "true", "yes", "on"}
    if strict:
        raise RuntimeError(
            f"{name} no está configurada. Define esta variable de entorno antes de iniciar la aplicación."
        )
    derived = hashlib.sha256(
        f"{name}:{os.environ.get('APP_ENV', 'development')}:{os.environ.get('RAILWAY_SERVICE_ID', 'local')}".encode("utf-8")
    ).hexdigest()
    print(
        f"[secrets] {name} no definida; usando secreto derivado temporal. "
        "Configura la variable en producción para persistencia de sesión."
    )
    return derived


AUTH_COOKIE_SECRET = _require_secret("AUTH_COOKIE_SECRET")
SENSITIVE_DATA_SECRET = (os.environ.get("SENSITIVE_DATA_SECRET") or AUTH_COOKIE_SECRET).strip()
PASSKEY_COOKIE_REGISTER = "passkey_register"
PASSKEY_COOKIE_AUTH = "passkey_auth"
PASSKEY_COOKIE_MFA_GATE = "passkey_mfa_gate"
PASSKEY_CHALLENGE_TTL_SECONDS = 300
GEOIP_CACHE_TTL_SECONDS = 60 * 60 * 6
_GEOIP_CACHE: Dict[str, Dict[str, Any]] = {}
LOGIN_RATE_LIMIT_WINDOW_SECONDS = int((os.environ.get("LOGIN_RATE_LIMIT_WINDOW_SECONDS") or "300").strip() or "300")
LOGIN_RATE_LIMIT_MAX_ATTEMPTS = int((os.environ.get("LOGIN_RATE_LIMIT_MAX_ATTEMPTS") or "7").strip() or "7")
_LOGIN_ATTEMPTS: Dict[str, List[float]] = {}
IDENTITY_UPLOAD_MAX_BYTES = int((os.environ.get("IDENTITY_UPLOAD_MAX_BYTES") or str(5 * 1024 * 1024)).strip() or str(5 * 1024 * 1024))
TOTP_PERIOD_SECONDS = int((os.environ.get("TOTP_PERIOD_SECONDS") or "30").strip() or "30")
TOTP_ALLOWED_DRIFT_STEPS = int((os.environ.get("TOTP_ALLOWED_DRIFT_STEPS") or "1").strip() or "1")


def normalize_role_name(role_name: Optional[str]) -> str:
    raw = (role_name or "").strip().lower()
    if not raw:
        return "usuario"
    normalized = unicodedata.normalize("NFKD", raw)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    if not normalized:
        return "usuario"
    if normalized in {"superadmin", "super_admin", "super_administrador", "superadministrador", "superadministrdor"}:
        return "superadministrador"
    if normalized in {"administrador_multiempresa", "admin_multiempresa", "multiempresa_admin", "administrador_multi"}:
        return "administrador_multiempresa"
    if normalized in {"admin", "administrador", "administador", "administrdor", "admnistrador"}:
        return "administrador"
    from fastapi_modulo.modulos.personalizacion.controladores.roles import ROLE_ALIASES

    return ROLE_ALIASES.get(normalized, normalized)


def get_current_role(request: Request) -> str:
    role = (
        getattr(request.state, "user_role", None)
        or getattr(request.state, "role", None)
        or request.cookies.get("user_role")
        or request.cookies.get("role")
        or request.cookies.get("rol")
        or ""
    )
    if not str(role or "").strip():
        session_token = request.cookies.get(AUTH_COOKIE_NAME, "")
        session_data = _read_session_cookie(session_token)
        if isinstance(session_data, dict):
            role = session_data.get("role") or ""
    if not str(role or "").strip():
        role = os.environ.get("DEFAULT_USER_ROLE") or ""
    return normalize_role_name(role)


def _normalize_tenant_id(value: Optional[str]) -> str:
    raw = (value or "").strip().lower()
    normalized = re.sub(r"[^a-z0-9._-]+", "-", raw).strip("-._")
    return normalized or "default"


def get_current_tenant(request: Request) -> str:
    tenant = getattr(request.state, "tenant_id", None)
    if tenant:
        return _normalize_tenant_id(tenant)
    cookie_tenant = request.cookies.get("tenant_id")
    if cookie_tenant:
        return _normalize_tenant_id(cookie_tenant)
    header_tenant = request.headers.get("x-tenant-id")
    if header_tenant and is_superadmin(request):
        return _normalize_tenant_id(header_tenant)
    return _normalize_tenant_id(os.environ.get("DEFAULT_TENANT_ID", "default"))


def _get_request_dataMAIN_info(request: Optional[Request] = None) -> Dict[str, str]:
    host = ""
    if request is not None:
        forwarded_host = request.headers.get("x-forwarded-host")
        host = (forwarded_host or request.headers.get("host") or request.url.hostname or "").strip()
    return core_db.get_current_dataMAIN_info(host)


def _normalize_host_identifier(value: Optional[str]) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        return ""
    if "://" in raw:
        raw = raw.split("://", 1)[1]
    raw = raw.split("/", 1)[0]
    raw = raw.split(",", 1)[0].strip()
    if ":" in raw and raw.count(":") == 1:
        raw = raw.split(":", 1)[0]
    return raw


def _parse_host_value_map(raw_value: str) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    raw = (raw_value or "").strip()
    if not raw:
        return mapping
    for chunk in raw.split(","):
        host, sep, value = chunk.partition("=")
        if not sep:
            continue
        normalized_host = _normalize_host_identifier(host)
        normalized_value = str(value or "").strip()
        if normalized_host and normalized_value:
            mapping[normalized_host] = normalized_value
    return mapping


UPDATE_SOURCE_MAP = _parse_host_value_map(
    os.environ.get("UPDATE_SOURCE_MAP")
    or (
        "avancoop.org=https://actualizaciones.circulocooperativo.com/avancoop/manifest.json,"
        "www.avancoop.org=https://actualizaciones.circulocooperativo.com/avancoop/manifest.json,"
        "cajapolotitlan.circulocooperativo.com=https://actualizaciones.circulocooperativo.com/polotitlan/manifest.json,"
        "sipet.circulocooperativo.com=https://actualizaciones.circulocooperativo.com/sipet/manifest.json"
    )
)
UPDATE_CHANNEL_MAP = _parse_host_value_map(
    os.environ.get("UPDATE_CHANNEL_MAP")
    or (
        "avancoop.org=avancoop,"
        "www.avancoop.org=avancoop,"
        "cajapolotitlan.circulocooperativo.com=polotitlan,"
        "sipet.circulocooperativo.com=railway"
    )
)
UPDATE_STRATEGY_MAP = _parse_host_value_map(
    os.environ.get("UPDATE_STRATEGY_MAP")
    or (
        "avancoop.org=git-pull,"
        "www.avancoop.org=git-pull,"
        "cajapolotitlan.circulocooperativo.com=git-pull,"
        "sipet.circulocooperativo.com=manual"
    )
)


def is_superadmin(request: Request) -> bool:
    return get_current_role(request) == "superadministrador"


def _get_user_app_access(request: Request) -> list:
    """Return the app_access list for the current session user (from colab meta JSON)."""
    try:
        if is_superadmin(request):
            return list(get_active_app_access_names())
        username = getattr(request.state, "user_name", None) or ""
        if not username:
            return []
        lookup_hash = _sensitive_lookup_hash(username)
        db = SessionLocal()
        try:
            user = db.query(Usuario).filter(Usuario.usuario_hash == lookup_hash).first()
            if not user:
                return []
            user_id = str(user.id)
        finally:
            db.close()
        import json as _json
        import os as _os
        _APP_ENV_L = (_os.environ.get("APP_ENV") or _os.environ.get("ENVIRONMENT") or "development").strip().lower()
        _SIPET_DATA_DIR = (_os.environ.get("SIPET_DATA_DIR") or _os.path.expanduser("~/.sipet/data")).strip()
        _RT_DIR = (_os.environ.get("RUNTIME_STORE_DIR") or _os.path.join(_SIPET_DATA_DIR, "runtime_store", _APP_ENV_L)).strip()
        _META_PATH = _os.environ.get("COLAB_META_PATH") or _os.path.join(_RT_DIR, "colaboradores_meta.json")
        if not _os.path.exists(_META_PATH):
            return []
        raw = _json.loads(open(_META_PATH, encoding="utf-8").read())
        if not isinstance(raw, dict):
            return []
        entry = raw.get(user_id, {})
        if not isinstance(entry, dict):
            return []
        visible = []
        seen = set()
        direct_access = entry.get("app_access", [])
        if isinstance(direct_access, list):
            for item in direct_access:
                name = str(item).strip()
                if not name:
                    continue
                key = name.lower()
                if key in seen:
                    continue
                seen.add(key)
                visible.append(name)
        app_access_levels = entry.get("app_access_levels", {})
        if isinstance(app_access_levels, dict):
            for app_name, levels in app_access_levels.items():
                if not isinstance(levels, dict):
                    continue
                if any(bool(levels.get(level_key, False)) for level_key in (
                    "full_access",
                    "read_only",
                    "department_only",
                    "user_only",
                    "special_permissions",
                )):
                    name = str(app_name).strip()
                    if not name:
                        continue
                    key = name.lower()
                if key in seen:
                    continue
                seen.add(key)
                visible.append(name)
        return [name for name in visible if is_app_access_enabled(name)]
    except Exception:
        return []


def _get_user_strategy_submenu_access_levels(request: Request) -> dict:
    try:
        if is_superadmin(request):
            return {
                "Diagnóstico": {
                    "full_access": True,
                    "read_only": False,
                    "department_only": False,
                    "user_only": False,
                    "special_permissions": False,
                },
                "Plan estratégico": {
                    "full_access": True,
                    "read_only": False,
                    "department_only": False,
                    "user_only": False,
                    "special_permissions": False,
                },
                "POA": {
                    "full_access": True,
                    "read_only": False,
                    "department_only": False,
                    "user_only": False,
                    "special_permissions": False,
                },
                "Tablero de control": {
                    "full_access": True,
                    "read_only": False,
                    "department_only": False,
                    "user_only": False,
                    "special_permissions": False,
                },
                "IA estrategia": {
                    "full_access": True,
                    "read_only": False,
                    "department_only": False,
                    "user_only": False,
                    "special_permissions": False,
                },
            }
        username = getattr(request.state, "user_name", None) or ""
        if not username:
            return {}
        lookup_hash = _sensitive_lookup_hash(username)
        db = SessionLocal()
        try:
            user = db.query(Usuario).filter(Usuario.usuario_hash == lookup_hash).first()
            if not user:
                return {}
            user_id = str(user.id)
        finally:
            db.close()
        import json as _json
        import os as _os
        _APP_ENV_L = (_os.environ.get("APP_ENV") or _os.environ.get("ENVIRONMENT") or "development").strip().lower()
        _SIPET_DATA_DIR = (_os.environ.get("SIPET_DATA_DIR") or _os.path.expanduser("~/.sipet/data")).strip()
        _RT_DIR = (_os.environ.get("RUNTIME_STORE_DIR") or _os.path.join(_SIPET_DATA_DIR, "runtime_store", _APP_ENV_L)).strip()
        _META_PATH = _os.environ.get("COLAB_META_PATH") or _os.path.join(_RT_DIR, "colaboradores_meta.json")
        if not _os.path.exists(_META_PATH):
            return {}
        raw = _json.loads(open(_META_PATH, encoding="utf-8").read())
        if not isinstance(raw, dict):
            return {}
        entry = raw.get(user_id, {})
        levels = entry.get("strategy_submenu_access_levels", {}) if isinstance(entry, dict) else {}
        return levels if isinstance(levels, dict) else {}
    except Exception:
        return {}


def _get_user_strategy_submenu_access_level(request: Request, submenu_name: str) -> str:
    if is_admin_or_superadmin(request):
        return "full_access"
    label = str(submenu_name or "").strip()
    if not label:
        return ""
    access_map = _get_user_strategy_submenu_access_levels(request)
    levels = access_map.get(label, {}) if isinstance(access_map, dict) else {}
    if isinstance(levels, dict):
        for level_key in ("full_access", "read_only", "department_only", "user_only", "special_permissions"):
            if bool(levels.get(level_key, False)):
                return level_key
    if "Estrategia y táctica" in _get_user_app_access(request):
        return "full_access"
    return ""


def _has_strategy_submenu_access(request: Request, submenu_name: str) -> bool:
    return bool(_get_user_strategy_submenu_access_level(request, submenu_name))


def _get_user_backend_roles(request: Request) -> list:
    """Return the backend_roles list for the current session user (from colab meta JSON)."""
    try:
        username = getattr(request.state, "user_name", None) or ""
        if not username:
            return []
        lookup_hash = _sensitive_lookup_hash(username)
        db = SessionLocal()
        try:
            user = db.query(Usuario).filter(Usuario.usuario_hash == lookup_hash).first()
            if not user:
                return []
            user_id = str(user.id)
        finally:
            db.close()
        import json as _json
        import os as _os
        _APP_ENV_L = (_os.environ.get("APP_ENV") or _os.environ.get("ENVIRONMENT") or "development").strip().lower()
        _SIPET_DATA_DIR = (_os.environ.get("SIPET_DATA_DIR") or _os.path.expanduser("~/.sipet/data")).strip()
        _RT_DIR = (_os.environ.get("RUNTIME_STORE_DIR") or _os.path.join(_SIPET_DATA_DIR, "runtime_store", _APP_ENV_L)).strip()
        _META_PATH = _os.environ.get("COLAB_META_PATH") or _os.path.join(_RT_DIR, "colaboradores_meta.json")
        if not _os.path.exists(_META_PATH):
            return []
        raw = _json.loads(open(_META_PATH, encoding="utf-8").read())
        return raw.get(user_id, {}).get("backend_roles", []) if isinstance(raw, dict) else []
    except Exception:
        return []


def is_admin(request: Request) -> bool:
    return get_current_role(request) == "administrador"


def is_multiempresa_admin(request: Request) -> bool:
    return get_current_role(request) == "administrador_multiempresa"


def is_admin_or_superadmin(request: Request) -> bool:
    return is_superadmin(request) or is_multiempresa_admin(request) or is_admin(request)


def require_superadmin(request: Request) -> None:
    if not is_superadmin(request):
        raise HTTPException(status_code=403, detail="Acceso restringido a superadministrador")


def require_admin_or_superadmin(request: Request) -> None:
    if not is_admin_or_superadmin(request):
        raise HTTPException(status_code=403, detail="Acceso restringido a administradores")


def can_assign_role(request: Request, role_name: str) -> bool:
    normalized = (role_name or "").strip().lower()
    if not normalized:
        return True
    if is_superadmin(request):
        return True
    if is_admin(request):
        return normalized != "superadministrador"
    return False


def get_visible_role_names(request: Request) -> List[str]:
    from fastapi_modulo.modulos.personalizacion.controladores.roles import DEFAULT_SYSTEM_ROLES

    if is_superadmin(request):
        return [name for name, _ in DEFAULT_SYSTEM_ROLES]
    if is_admin(request):
        return [name for name, _ in DEFAULT_SYSTEM_ROLES if name != "superadministrador"]
    return []


def _sensitive_secret_bytes() -> bytes:
    return hashlib.sha256(SENSITIVE_DATA_SECRET.encode("utf-8")).digest()


def _sensitive_fernet() -> Fernet:
    key = base64.urlsafe_b64encode(_sensitive_secret_bytes())
    return Fernet(key)


def _sensitive_lookup_hash(value: str) -> str:
    normalized = (value or "").strip().lower()
    return hmac.new(_sensitive_secret_bytes(), normalized.encode("utf-8"), hashlib.sha256).hexdigest()


def _auth_client_key(request: Request) -> str:
    forwarded_for = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if forwarded_for:
        return forwarded_for
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _is_login_rate_limited(request: Request) -> bool:
    key = _auth_client_key(request)
    now = time.time()
    window_start = now - max(1, LOGIN_RATE_LIMIT_WINDOW_SECONDS)
    attempts = [ts for ts in _LOGIN_ATTEMPTS.get(key, []) if ts >= window_start]
    _LOGIN_ATTEMPTS[key] = attempts
    return len(attempts) >= max(1, LOGIN_RATE_LIMIT_MAX_ATTEMPTS)


def _register_failed_login_attempt(request: Request) -> None:
    key = _auth_client_key(request)
    now = time.time()
    window_start = now - max(1, LOGIN_RATE_LIMIT_WINDOW_SECONDS)
    attempts = [ts for ts in _LOGIN_ATTEMPTS.get(key, []) if ts >= window_start]
    attempts.append(now)
    _LOGIN_ATTEMPTS[key] = attempts


def _clear_failed_login_attempts(request: Request) -> None:
    _LOGIN_ATTEMPTS.pop(_auth_client_key(request), None)


def _is_same_origin_request(request: Request) -> bool:
    host = (request.headers.get("host") or "").strip().lower()
    forwarded_host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip().lower()
    effective_host = forwarded_host or host
    if not effective_host:
        return False
    forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
    effective_scheme = forwarded_proto or request.url.scheme
    current_origin = f"{effective_scheme}://{effective_host}"

    origin = (request.headers.get("origin") or "").strip().rstrip("/")
    if origin:
        origin_normalized = origin.lower()
        if origin_normalized == current_origin:
            return True
        try:
            parsed_origin = urlparse(origin_normalized)
            parsed_current = urlparse(current_origin)
            # Detrás de proxy puede diferir el esquema interno/externo.
            return parsed_origin.netloc == parsed_current.netloc and parsed_origin.scheme in {"http", "https"}
        except Exception:
            return False

    referer = (request.headers.get("referer") or "").strip()
    if referer:
        parsed = urlparse(referer)
        referer_origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/").lower()
        if referer_origin == current_origin:
            return True
        parsed_current = urlparse(current_origin)
        return parsed.netloc.lower() == parsed_current.netloc and parsed.scheme in {"http", "https"}

    return False


def _encrypt_sensitive(value: Optional[str]) -> Optional[str]:
    raw = (value or "").strip()
    if not raw:
        return value
    if raw.startswith("enc$"):
        return raw
    token = _sensitive_fernet().encrypt(raw.encode("utf-8")).decode("utf-8")
    return f"enc${token}"


def _decrypt_sensitive(value: Optional[str]) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if not raw.startswith("enc$"):
        return raw
    token = raw[4:]
    try:
        return _sensitive_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""


def _ensure_login_identity_paths() -> None:
    os.makedirs(IDENTIDAD_LOGIN_IMAGE_DIR, exist_ok=True)


def _ensure_store_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _load_login_identity() -> Dict[str, str]:
    data = DEFAULT_LOGIN_IDENTITY.copy()
    if os.path.exists(IDENTIDAD_LOGIN_CONFIG_PATH):
        try:
            with open(IDENTIDAD_LOGIN_CONFIG_PATH, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                data.update({k: v for k, v in loaded.items() if isinstance(v, str)})
        except (OSError, json.JSONDecodeError):
            pass
    return data


def _save_login_identity(data: Dict[str, str]) -> None:
    _ensure_store_parent_dir(IDENTIDAD_LOGIN_CONFIG_PATH)
    with open(IDENTIDAD_LOGIN_CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def _get_upload_ext(upload: UploadFile) -> str:
    filename = (upload.filename or "").lower()
    ext = os.path.splitext(filename)[1]
    if ext in {".png", ".jpg", ".jpeg", ".backendp", ".svg"}:
        return ext
    content_type = (upload.content_type or "").lower()
    if "svg" in content_type:
        return ".svg"
    if "backendp" in content_type:
        return ".backendp"
    if "jpeg" in content_type or "jpg" in content_type:
        return ".jpg"
    return ".png"


def _remove_login_image_if_custom(filename: Optional[str]) -> None:
    if not filename or filename in {
        DEFAULT_LOGIN_IDENTITY["favicon_filename"],
        DEFAULT_LOGIN_IDENTITY["logo_filename"],
        DEFAULT_LOGIN_IDENTITY["desktop_bg_filename"],
        DEFAULT_LOGIN_IDENTITY["mobile_bg_filename"],
    }:
        return
    path = os.path.join(IDENTIDAD_LOGIN_IMAGE_DIR, filename)
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


async def _store_login_image(upload: UploadFile, prefix: str) -> Optional[str]:
    if not upload or not upload.filename:
        return None
    content_type = (upload.content_type or "").lower().strip()
    filename = (upload.filename or "").lower()
    ext = os.path.splitext(filename)[1]
    allowed_exts = {".png", ".jpg", ".jpeg", ".backendp", ".svg"}
    # Algunos navegadores/proxys envían application/octet-stream para imágenes válidas.
    if content_type and not content_type.startswith("image/") and ext not in allowed_exts:
        raise HTTPException(status_code=400, detail="Solo se permiten imágenes para identidad institucional")
    data = await upload.read()
    if not data:
        return None
    if len(data) > max(1, IDENTITY_UPLOAD_MAX_BYTES):
        raise HTTPException(status_code=413, detail="La imagen supera el tamaño máximo permitido")
    _ensure_login_identity_paths()
    ext = _get_upload_ext(upload)
    # Optimizar imagen: redimensionar y convertir a backendP según el tipo de asset
    from fastapi_modulo.image_utils import optimize_image, profile_for_prefix
    optimized, ext = optimize_image(data, ext, profile=profile_for_prefix(prefix))
    new_filename = f"{prefix}_{secrets.token_hex(6)}{ext}"
    image_path = os.path.join(IDENTIDAD_LOGIN_IMAGE_DIR, new_filename)
    with open(image_path, "wb") as fh:
        fh.write(optimized)
    return new_filename


def _sanitize_document_name(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "_", (value or "").strip())
    return normalized.strip("._") or "documento"


def _ensure_documents_dir() -> None:
    os.makedirs(DOCUMENTS_UPLOAD_DIR, exist_ok=True)


async def _store_evidence_file(upload: UploadFile) -> Dict[str, Any]:
    if not upload or not upload.filename:
        raise HTTPException(status_code=400, detail="Archivo requerido")

    data = await upload.read()
    if not data:
        raise HTTPException(status_code=400, detail="El archivo está vacío")
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="El archivo supera 25MB")

    _ensure_documents_dir()
    ext = os.path.splitext(upload.filename or "")[1].lower()
    safe_MAIN = _sanitize_document_name(os.path.splitext(upload.filename or "documento")[0])
    final_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{safe_MAIN}_{secrets.token_hex(4)}{ext}"
    final_path = os.path.join(DOCUMENTS_UPLOAD_DIR, final_name)
    with open(final_path, "wb") as f:
        f.write(data)

    return {
        "filename": upload.filename,
        "path": final_path,
        "mime": (upload.content_type or "").strip() or "application/octet-stream",
        "size": len(data),
    }


def _delete_evidence_file(path: Optional[str]) -> None:
    if not path:
        return
    safe_root = os.path.abspath(DOCUMENTS_UPLOAD_DIR)
    target = os.path.abspath(path)
    if not target.startswith(safe_root):
        return
    if os.path.exists(target):
        os.remove(target)


def _build_login_asset_url(filename: Optional[str], default_filename: str) -> str:
    selected = filename or default_filename
    selected_path = os.path.join(IDENTIDAD_LOGIN_IMAGE_DIR, selected)
    if not os.path.exists(selected_path):
        selected = default_filename
        selected_path = os.path.join(IDENTIDAD_LOGIN_IMAGE_DIR, selected)
    version = int(os.path.getmtime(selected_path)) if os.path.exists(selected_path) else 0
    return f"/templates/imagenes/{selected}?v={version}"


def _resolve_sidebar_logo_url(login_identity: Dict[str, str]) -> str:
    identity_data = _load_login_identity()
    identity_logo_filename = str(identity_data.get("logo_filename") or "").strip()
    identity_logo_url = str(login_identity.get("login_logo_url") or "").strip()

    # Si el administrador configuró un logo en Identidad institucional, tiene prioridad.
    if identity_logo_filename and identity_logo_filename != DEFAULT_LOGIN_IDENTITY["logo_filename"]:
        return identity_logo_url or "/templates/icon/icon.png"

    # Si Identidad institucional no está personalizado, usa el logo por defecto de Ajustes/Colores.
    from fastapi_modulo.modulos.personalizacion.controladores.personalizar import resolve_logo_empresa_url

    default_logo_url = resolve_logo_empresa_url()
    if default_logo_url:
        return default_logo_url
    return identity_logo_url or "/templates/icon/icon.png"


def _get_login_identity_context() -> Dict[str, str]:
    data = _load_login_identity()
    return {
        "login_favicon_url": _build_login_asset_url(
            data.get("favicon_filename"),
            DEFAULT_LOGIN_IDENTITY["favicon_filename"],
        ),
        "login_logo_url": _build_login_asset_url(
            data.get("logo_filename"),
            DEFAULT_LOGIN_IDENTITY["logo_filename"],
        ),
        "login_bg_desktop_url": _build_login_asset_url(
            data.get("desktop_bg_filename"),
            DEFAULT_LOGIN_IDENTITY["desktop_bg_filename"],
        ),
        "login_bg_mobile_url": _build_login_asset_url(
            data.get("mobile_bg_filename"),
            DEFAULT_LOGIN_IDENTITY["mobile_bg_filename"],
        ),
        "login_company_short_name": data.get("company_short_name") or DEFAULT_LOGIN_IDENTITY["company_short_name"],
        "login_message": data.get("login_message") or DEFAULT_LOGIN_IDENTITY["login_message"],
        "menu_position": data.get("menu_position") or DEFAULT_LOGIN_IDENTITY["menu_position"],
    }


def build_view_buttons_html(view_buttons: Optional[List[Dict]]) -> str:
    if not view_buttons:
        return ""
    icon_map = {
        "form": "/templates/icon/form.svg",
        "lista": "/templates/icon/list.svg",
        "kanban": "/templates/icon/kanban.svg",
        "cuadricula": "/templates/icon/grid.svg",
        "organigrama": "/templates/icon/organigrama.svg",
        "grafica": "/templates/icon/grafica.svg",
    }
    pieces = []
    for button in view_buttons:
        label = button.get("label", "").strip()
        if not label:
            continue
        normalized_label = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode("ascii").strip().lower()
        icon = button.get("icon") or icon_map.get(normalized_label)
        view = button.get("view")
        url = button.get("url")
        classes = "view-pill"
        if button.get("active"):
            classes += " active"
        attrs = []
        if view:
            attrs.append(f'data-view="{view}"')
        if url:
            attrs.append(f'data-url="{url}"')
        attr_str = f' {" ".join(attrs)}' if attrs else ""
        icon_html = ""
        if icon:
            icon_html = (
                f'<span class="view-pill-icon-mask" aria-hidden="true" '
                f'style="--view-pill-icon-url:url(\'{icon}\')"></span>'
            )
        pieces.append(f'<button class="{classes}" type="button"{attr_str}>{icon_html}<span class="view-pill-label">{label}</span></button>')
    return "".join(pieces)


DATAMAIN_URL = core_db.DATAMAIN_URL
IS_SQLITE_DATAMAIN = DATAMAIN_URL.startswith("sqlite:///")
PRIMARY_DB_PATH = core_db.get_current_dataMAIN_info().get("path") or None
APP_ENV = APP_ENV_DEFAULT
SESSION_MAX_AGE_SECONDS = int((os.environ.get("SESSION_MAX_AGE_SECONDS") or "28800").strip() or "28800")
COOKIE_SECURE = (os.environ.get("COOKIE_SECURE") or "").strip().lower() in {"1", "true", "yes", "on"} or APP_ENV in {
    "production",
    "prod",
}
ALLOW_LEGACY_PLAINTEXT_PASSWORDS = (os.environ.get("ALLOW_LEGACY_PLAINTEXT_PASSWORDS") or "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
ENABLE_API_DOCS = (os.environ.get("ENABLE_API_DOCS") or "").strip().lower() in {"1", "true", "yes", "on"} or APP_ENV not in {
    "production",
    "prod",
}
HEALTH_INCLUDE_DETAILS = (os.environ.get("HEALTH_INCLUDE_DETAILS") or "").strip().lower() in {"1", "true", "yes", "on"}
DEMO_ADMIN_SEED_ENABLED = (os.environ.get("DEMO_ADMIN_SEED_ENABLED") or "true").strip().lower() in {"1", "true", "yes", "on"}
CSRF_PROTECTION_ENABLED = (os.environ.get("CSRF_PROTECTION_ENABLED") or "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
UPDATE_CHECK_TIMEOUT_SECONDS = float((os.environ.get("UPDATE_CHECK_TIMEOUT_SECONDS") or "6").strip() or "6")
UPDATE_LOG_DIR = os.path.abspath(
    (os.environ.get("UPDATE_LOG_DIR") or os.path.join(RUNTIME_STORE_DIR, "updates")).strip()
)
AUTO_UPDATE_ENABLED = (os.environ.get("AUTO_UPDATE_ENABLED") or "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
MAIN = declarative_base()
engine = core_db.engine
SessionLocal = core_db.SessionLocal

class Colores(MAIN):
    __tablename__ = "colores"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(String)

# --- NUEVO: Modelos para roles y usuarios ---
class Rol(MAIN):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True)
    descripcion = Column(String)

class Usuario(MAIN):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column("full_name", String)
    usuario = Column("username", String, unique=True, index=True)
    usuario_hash = Column(String, index=True)
    correo = Column("email", String, unique=True, index=True)
    correo_hash = Column(String, index=True)
    celular = Column(String)
    contrasena = Column("password", String)
    departamento = Column(String)
    puesto = Column(String)
    jefe = Column(String)
    jefe_inmediato_id = Column(Integer, ForeignKey("users.id"), index=True)
    coach = Column(String)
    rol_id = Column(Integer)
    imagen = Column(String)
    role = Column(String)
    is_active = Column(Boolean, default=True)
    backendauthn_credential_id = Column(String, unique=True, index=True)
    backendauthn_public_key = Column(String)
    backendauthn_sign_count = Column(Integer, default=0)
    totp_secret = Column(String)
    totp_enabled = Column(Boolean, default=False)
    jefe_inmediato = relationship("Usuario", remote_side=[id], backref="subordinados")


class StrategicAxisConfig(MAIN):
    __tablename__ = "strategic_axes_config"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, default="default")
    fiscal_year = Column(Integer, index=True, default=lambda: datetime.utcnow().year)
    nombre = Column(String, nullable=False)
    codigo = Column(String, default="")
    lider_departamento = Column(String, default="")
    responsabilidad_directa = Column(String, default="")
    fecha_inicial = Column(Date)
    fecha_final = Column(Date)
    descripcion = Column(String, default="")
    orden = Column(Integer, default=0, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    objetivos = relationship(
        "StrategicObjectiveConfig",
        back_populates="eje",
        cascade="all, delete-orphan",
        order_by="StrategicObjectiveConfig.orden",
    )


class StrategicObjectiveConfig(MAIN):
    __tablename__ = "strategic_objectives_config"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, default="default")
    fiscal_year = Column(Integer, index=True, default=lambda: datetime.utcnow().year)
    eje_id = Column(Integer, ForeignKey("strategic_axes_config.id"), nullable=False, index=True)
    codigo = Column(String, default="")
    nombre = Column(String, nullable=False)
    hito = Column(String, default="")
    lider = Column(String, default="")
    fecha_inicial = Column(Date)
    fecha_final = Column(Date)
    descripcion = Column(String, default="")
    orden = Column(Integer, default=0, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    eje = relationship("StrategicAxisConfig", back_populates="objetivos")


class POAActivity(MAIN):
    __tablename__ = "poa_activities"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, default="default")
    fiscal_year = Column(Integer, index=True, default=lambda: datetime.utcnow().year)
    objective_id = Column(Integer, ForeignKey("strategic_objectives_config.id"), nullable=False, index=True)
    nombre = Column(String, nullable=False)
    codigo = Column(String, default="")
    responsable = Column(String, nullable=False)
    entregable = Column(String, default="")
    fecha_inicial = Column(Date)
    fecha_final = Column(Date)
    inicio_forzado = Column(Boolean, default=False)
    descripcion = Column(String, default="")
    recurrente = Column(Boolean, default=False)
    periodicidad = Column(String, default="")
    cada_xx_dias = Column(Integer)
    entrega_estado = Column(String, default="ninguna")
    entrega_solicitada_por = Column(String, default="")
    entrega_solicitada_at = Column(DateTime)
    entrega_aprobada_por = Column(String, default="")
    entrega_aprobada_at = Column(DateTime)
    created_by = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class POASubactivity(MAIN):
    __tablename__ = "poa_subactivities"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, default="default")
    fiscal_year = Column(Integer, index=True, default=lambda: datetime.utcnow().year)
    activity_id = Column(Integer, ForeignKey("poa_activities.id"), nullable=False, index=True)
    parent_subactivity_id = Column(Integer, ForeignKey("poa_subactivities.id"), index=True)
    nivel = Column(Integer, default=1, index=True)
    nombre = Column(String, nullable=False)
    codigo = Column(String, default="")
    responsable = Column(String, nullable=False)
    entregable = Column(String, default="")
    fecha_inicial = Column(Date)
    fecha_final = Column(Date)
    descripcion = Column(String, default="")
    recurrente = Column(Boolean, default=False)
    periodicidad = Column(String, default="")
    cada_xx_dias = Column(Integer)
    assigned_by = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class POADeliverableApproval(MAIN):
    __tablename__ = "poa_deliverable_approvals"

    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(Integer, ForeignKey("poa_activities.id"), nullable=False, index=True)
    objective_id = Column(Integer, ForeignKey("strategic_objectives_config.id"), nullable=False, index=True)
    process_owner = Column(String, nullable=False)
    requester = Column(String, nullable=False)
    status = Column(String, default="pendiente")
    comment = Column(String, default="")
    resolved_by = Column(String, default="")
    resolved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DocumentoEvidencia(MAIN):
    __tablename__ = "documentos_evidencia"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, default="default")
    titulo = Column(String, nullable=False)
    descripcion = Column(String)
    proceso = Column(String, default="envio")
    estado = Column(String, default="borrador")
    version = Column(Integer, default=1)
    archivo_nombre = Column(String, nullable=False)
    archivo_ruta = Column(String, nullable=False)
    archivo_tipo = Column(String)
    archivo_tamano = Column(Integer, default=0)
    observaciones = Column(String)
    creado_por = Column(String)
    enviado_por = Column(String)
    autorizado_por = Column(String)
    actualizado_por = Column(String)
    creado_at = Column(DateTime, default=datetime.utcnow)
    enviado_at = Column(DateTime)
    autorizado_at = Column(DateTime)
    actualizado_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserNotificationRead(MAIN):
    __tablename__ = "user_notification_reads"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_key", "notification_id", name="uq_notification_read_scope"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True, default="default")
    user_key = Column(String, nullable=False, index=True)
    notification_id = Column(String, nullable=False, index=True)
    read_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PublicLandingVisit(MAIN):
    __tablename__ = "public_landing_visits"

    id = Column(Integer, primary_key=True, index=True)
    page = Column(String, index=True, default="funcionalidades")
    ip_address = Column(String, index=True)
    user_agent = Column(String)
    referrer = Column(String)
    country = Column(String, index=True)
    region = Column(String, index=True)
    city = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class PublicLeadRequest(MAIN):
    __tablename__ = "public_lead_requests"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    organizacion = Column(String)
    cargo = Column(String)
    email = Column(String, nullable=False, index=True)
    telefono = Column(String)
    mensaje = Column(String, nullable=False)
    source_page = Column(String, index=True, default="funcionalidades")
    ip_address = Column(String, index=True)
    user_agent = Column(String)
    country = Column(String, index=True)
    region = Column(String, index=True)
    city = Column(String, index=True)
    status = Column(String, default="nuevo", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class PublicQuizSubmission(MAIN):
    __tablename__ = "public_quiz_submissions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, default="default")
    nombre = Column(String, nullable=False)
    cooperativa = Column(String, nullable=False)
    pais = Column(String, nullable=False)
    celular = Column(String, nullable=False)
    correctas = Column(Integer, default=0, index=True)
    descuento = Column(Integer, default=0, index=True)
    total_preguntas = Column(Integer, default=10)
    answers = Column(JSON, default=dict)
    ip_address = Column(String, index=True)
    user_agent = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


DEFAULT_SUPERADMIN_USERNAME_B64 = "T2tvbm9taXlha2k="  # Okonomiyaki
DEFAULT_SUPERADMIN_PASSWORD_B64 = "WFgsJCwyNixzaXBldCwyNiwkLFhY"  # XX,$,26,sipet,26,$,XX
DEFAULT_SUPERADMIN_EMAIL_B64 = "YWxvcGV6QGF2YW5jb29wLm9yZw=="  # alopez@avancoop.org
DEFAULT_DEMO_EMAIL = "demo@sipet.local"


def ensure_default_roles() -> None:
    Rol.__table__.create(bind=engine, checkfirst=True)
    db = SessionLocal()
    try:
        from fastapi_modulo.modulos.personalizacion.controladores.roles import DEFAULT_SYSTEM_ROLES

        for role_name, role_description in DEFAULT_SYSTEM_ROLES:
            existing = db.query(Rol).filter(Rol.nombre == role_name).first()
            if existing:
                if (existing.descripcion or "").strip() != role_description:
                    existing.descripcion = role_description
                    db.add(existing)
                continue
            db.add(Rol(nombre=role_name, descripcion=role_description))
        db.commit()
    finally:
        db.close()


def _decode_b64(value: str) -> str:
    return base64.b64decode(value.encode("utf-8")).decode("utf-8")


def _hash_password_pbkdf2(password: str) -> str:
    iterations = 120_000
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


def ensure_system_superadmin_user() -> None:
    username = (os.environ.get("SYSTEM_SUPERADMIN_USERNAME") or _decode_b64(DEFAULT_SUPERADMIN_USERNAME_B64)).strip()
    password = (os.environ.get("SYSTEM_SUPERADMIN_PASSWORD") or _decode_b64(DEFAULT_SUPERADMIN_PASSWORD_B64))
    email = (os.environ.get("SYSTEM_SUPERADMIN_EMAIL") or _decode_b64(DEFAULT_SUPERADMIN_EMAIL_B64)).strip()
    if not username or not password or not email:
        return

    db = SessionLocal()
    try:
        superadmin_role = db.query(Rol).filter(func.lower(Rol.nombre) == "superadministrador").first()
        if not superadmin_role:
            return

        username_hash = _sensitive_lookup_hash(username)
        email_hash = _sensitive_lookup_hash(email)
        existing = (
            db.query(Usuario)
            .filter((Usuario.usuario_hash == username_hash) | (Usuario.correo_hash == email_hash))
            .first()
        )
        if not existing:
            existing = (
                db.query(Usuario)
                .filter(
                    (func.lower(Usuario.usuario) == username.lower())
                    | (func.lower(Usuario.correo) == email.lower())
                )
                .first()
            )
        if existing:
            existing.full_name = existing.full_name or "Super Administrador"
            existing.usuario = _encrypt_sensitive(_decrypt_sensitive(existing.usuario) or username)
            existing.correo = _encrypt_sensitive(_decrypt_sensitive(existing.correo) or email)
            existing.usuario_hash = _sensitive_lookup_hash(_decrypt_sensitive(existing.usuario) or username)
            existing.correo_hash = _sensitive_lookup_hash(_decrypt_sensitive(existing.correo) or email)
            existing.rol_id = superadmin_role.id
            existing.role = "superadministrador"
            existing.is_active = True
            if not (existing.contrasena or "").strip():
                existing.contrasena = _hash_password_pbkdf2(password)
            db.add(existing)
            db.commit()
            return

        db.add(
            Usuario(
                full_name="Super Administrador",
                usuario=_encrypt_sensitive(username),
                usuario_hash=username_hash,
                correo=_encrypt_sensitive(email),
                correo_hash=email_hash,
                contrasena=_hash_password_pbkdf2(password),
                rol_id=superadmin_role.id,
                role="superadministrador",
                is_active=True,
            )
        )
        db.commit()
    finally:
        db.close()


def ensure_demo_admin_user_seed() -> None:
    if not DEMO_ADMIN_SEED_ENABLED:
        return

    username = (os.environ.get("DEMO_ADMIN_USERNAME") or "demo").strip()
    password = os.environ.get("DEMO_ADMIN_PASSWORD") or "demodemo"
    email = (os.environ.get("DEMO_ADMIN_EMAIL") or DEFAULT_DEMO_EMAIL).strip().lower()
    if not username or not password:
        return
    if not email:
        email = DEFAULT_DEMO_EMAIL

    db = SessionLocal()
    try:
        admin_role = db.query(Rol).filter(func.lower(Rol.nombre) == "administrador").first()
        if not admin_role:
            return

        username_hash = _sensitive_lookup_hash(username)
        email_hash = _sensitive_lookup_hash(email)
        existing = (
            db.query(Usuario)
            .filter((Usuario.usuario_hash == username_hash) | (Usuario.correo_hash == email_hash))
            .first()
        )
        if not existing:
            existing = (
                db.query(Usuario)
                .filter(
                    (func.lower(Usuario.usuario) == username.lower())
                    | (func.lower(Usuario.correo) == email.lower())
                )
                .first()
            )

        password_hash = _hash_password_pbkdf2(password)
        if existing:
            existing.full_name = existing.full_name or "Usuario Demo"
            existing.usuario = _encrypt_sensitive(username)
            existing.correo = _encrypt_sensitive(email)
            existing.usuario_hash = username_hash
            existing.correo_hash = email_hash
            existing.contrasena = password_hash
            existing.rol_id = admin_role.id
            existing.role = "administrador"
            existing.is_active = True
            db.add(existing)
            db.commit()
            return

        db.add(
            Usuario(
                full_name="Usuario Demo",
                usuario=_encrypt_sensitive(username),
                usuario_hash=username_hash,
                correo=_encrypt_sensitive(email),
                correo_hash=email_hash,
                contrasena=password_hash,
                rol_id=admin_role.id,
                role="administrador",
                is_active=True,
            )
        )
        db.commit()
    finally:
        db.close()


def ensure_default_strategic_axes_data() -> None:
    ensure_strategic_axes_schema()
    default_axes = [
        (
            "Gobernanza y cumplimiento",
            "AX-01",
            "Fortalecer controles, normatividad y gestión de riesgos.",
            [
                ("OE-01", "Fortalecer la sostenibilidad financiera institucional."),
                ("OE-02", "Consolidar el marco de cumplimiento y auditoría."),
                ("OE-03", "Mejorar la gestión integral de riesgos."),
            ],
        ),
        (
            "Excelencia operativa",
            "AX-02",
            "Optimizar procesos críticos y tiempos de respuesta.",
            [
                ("OE-04", "Estandarizar procesos clave con enfoque en calidad."),
                ("OE-05", "Reducir tiempos de ciclo en servicios prioritarios."),
                ("OE-06", "Mejorar productividad y uso de recursos."),
                ("OE-07", "Incrementar satisfacción de clientes internos y externos."),
            ],
        ),
        (
            "Innovación y digitalización",
            "AX-03",
            "Acelerar transformación digital y uso de datos.",
            [
                ("OE-08", "Digitalizar procesos de alto impacto."),
                ("OE-09", "Fortalecer analítica e inteligencia de negocio."),
            ],
        ),
        (
            "Desarrollo del talento",
            "AX-04",
            "Potenciar capacidades del equipo y cultura de mejora.",
            [
                ("OE-10", "Fortalecer competencias estratégicas del personal."),
                ("OE-11", "Aumentar compromiso y clima organizacional."),
                ("OE-12", "Consolidar liderazgo y sucesión."),
            ],
        ),
    ]

    db = SessionLocal()
    try:
        has_axes = db.query(StrategicAxisConfig).first()
        if has_axes:
            return
        for axis_idx, (axis_name, axis_code, axis_desc, objectives) in enumerate(default_axes, start=1):
            axis = StrategicAxisConfig(nombre=axis_name, codigo=axis_code, descripcion=axis_desc, orden=axis_idx)
            db.add(axis)
            db.flush()
            for objective_idx, (code, objective_name) in enumerate(objectives, start=1):
                db.add(
                    StrategicObjectiveConfig(
                        eje_id=axis.id,
                        codigo=code,
                        nombre=objective_name,
                        orden=objective_idx,
                    )
                )
        db.commit()
    finally:
        db.close()


def protect_sensitive_user_fields() -> None:
    if not IS_SQLITE_DATAMAIN or not PRIMARY_DB_PATH:
        return
    with sqlite3.connect(PRIMARY_DB_PATH) as conn:
        cols = {row[1] for row in conn.execute('PRAGMA table_info("users")').fetchall()}
        if "usuario_hash" not in cols:
            conn.execute('ALTER TABLE "users" ADD COLUMN "usuario_hash" VARCHAR')
        if "correo_hash" not in cols:
            conn.execute('ALTER TABLE "users" ADD COLUMN "correo_hash" VARCHAR')
        conn.execute('CREATE INDEX IF NOT EXISTS "ix_users_usuario_hash" ON "users" ("usuario_hash")')
        conn.execute('CREATE INDEX IF NOT EXISTS "ix_users_correo_hash" ON "users" ("correo_hash")')
        conn.commit()

    db = SessionLocal()
    try:
        users = db.query(Usuario).all()
        for user in users:
            username_plain = _decrypt_sensitive(user.usuario)
            email_plain = _decrypt_sensitive(user.correo)

            if username_plain:
                user.usuario_hash = _sensitive_lookup_hash(username_plain)
                user.usuario = _encrypt_sensitive(username_plain)
            if email_plain:
                user.correo_hash = _sensitive_lookup_hash(email_plain)
                user.correo = _encrypt_sensitive(email_plain)
            db.add(user)
        db.commit()
    finally:
        db.close()


def ensure_passkey_user_schema() -> None:
    if not IS_SQLITE_DATAMAIN or not PRIMARY_DB_PATH:
        return
    with sqlite3.connect(PRIMARY_DB_PATH) as conn:
        cols = {row[1] for row in conn.execute('PRAGMA table_info("users")').fetchall()}
        if "backendauthn_credential_id" not in cols:
            conn.execute('ALTER TABLE "users" ADD COLUMN "backendauthn_credential_id" VARCHAR')
        if "backendauthn_public_key" not in cols:
            conn.execute('ALTER TABLE "users" ADD COLUMN "backendauthn_public_key" VARCHAR')
        if "backendauthn_sign_count" not in cols:
            conn.execute('ALTER TABLE "users" ADD COLUMN "backendauthn_sign_count" INTEGER DEFAULT 0')
        if "totp_secret" not in cols:
            conn.execute('ALTER TABLE "users" ADD COLUMN "totp_secret" VARCHAR')
        if "totp_enabled" not in cols:
            conn.execute('ALTER TABLE "users" ADD COLUMN "totp_enabled" BOOLEAN DEFAULT 0')
        conn.execute(
            'CREATE UNIQUE INDEX IF NOT EXISTS "ix_users_backendauthn_credential_id" ON "users" ("backendauthn_credential_id")'
        )
        conn.commit()


def ensure_strategic_axes_schema() -> None:
    if not IS_SQLITE_DATAMAIN or not PRIMARY_DB_PATH:
        return
    current_year = datetime.utcnow().year
    with sqlite3.connect(PRIMARY_DB_PATH) as conn:
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='strategic_axes_config'"
        ).fetchone()
        if not table_exists:
            return
        cols = {row[1] for row in conn.execute('PRAGMA table_info("strategic_axes_config")').fetchall()}
        if "tenant_id" not in cols:
            conn.execute('ALTER TABLE "strategic_axes_config" ADD COLUMN "tenant_id" VARCHAR DEFAULT "default"')
            conn.execute('UPDATE "strategic_axes_config" SET tenant_id = "default" WHERE tenant_id IS NULL OR tenant_id = ""')
        conn.execute(
            'CREATE INDEX IF NOT EXISTS "ix_strategic_axes_config_tenant_id" ON "strategic_axes_config" ("tenant_id")'
        )
        if "codigo" not in cols:
            conn.execute('ALTER TABLE "strategic_axes_config" ADD COLUMN "codigo" VARCHAR DEFAULT ""')
        if "lider_departamento" not in cols:
            conn.execute('ALTER TABLE "strategic_axes_config" ADD COLUMN "lider_departamento" VARCHAR DEFAULT ""')
        if "responsabilidad_directa" not in cols:
            conn.execute('ALTER TABLE "strategic_axes_config" ADD COLUMN "responsabilidad_directa" VARCHAR DEFAULT ""')
        if "fecha_inicial" not in cols:
            conn.execute('ALTER TABLE "strategic_axes_config" ADD COLUMN "fecha_inicial" DATE')
        if "fecha_final" not in cols:
            conn.execute('ALTER TABLE "strategic_axes_config" ADD COLUMN "fecha_final" DATE')
        if "fiscal_year" not in cols:
            conn.execute('ALTER TABLE "strategic_axes_config" ADD COLUMN "fiscal_year" INTEGER')
            conn.execute(
                'UPDATE "strategic_axes_config" '
                f'SET fiscal_year = COALESCE(CAST(strftime("%Y", fecha_inicial) AS INTEGER), CAST(strftime("%Y", fecha_final) AS INTEGER), {current_year}) '
                'WHERE fiscal_year IS NULL OR fiscal_year = 0'
            )
        conn.execute(
            'CREATE INDEX IF NOT EXISTS "ix_strategic_axes_config_fiscal_year" ON "strategic_axes_config" ("fiscal_year")'
        )
        objectives_table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='strategic_objectives_config'"
        ).fetchone()
        if objectives_table_exists:
            obj_cols = {row[1] for row in conn.execute('PRAGMA table_info("strategic_objectives_config")').fetchall()}
            if "tenant_id" not in obj_cols:
                conn.execute('ALTER TABLE "strategic_objectives_config" ADD COLUMN "tenant_id" VARCHAR DEFAULT "default"')
                conn.execute(
                    'UPDATE "strategic_objectives_config" SET tenant_id = COALESCE((SELECT tenant_id FROM strategic_axes_config a WHERE a.id = strategic_objectives_config.eje_id), "default") WHERE tenant_id IS NULL OR tenant_id = ""'
                )
            conn.execute(
                'CREATE INDEX IF NOT EXISTS "ix_strategic_objectives_config_tenant_id" ON "strategic_objectives_config" ("tenant_id")'
            )
            if "hito" not in obj_cols:
                conn.execute('ALTER TABLE "strategic_objectives_config" ADD COLUMN "hito" VARCHAR DEFAULT ""')
            if "lider" not in obj_cols:
                conn.execute('ALTER TABLE "strategic_objectives_config" ADD COLUMN "lider" VARCHAR DEFAULT ""')
            if "fecha_inicial" not in obj_cols:
                conn.execute('ALTER TABLE "strategic_objectives_config" ADD COLUMN "fecha_inicial" DATE')
            if "fecha_final" not in obj_cols:
                conn.execute('ALTER TABLE "strategic_objectives_config" ADD COLUMN "fecha_final" DATE')
            if "fiscal_year" not in obj_cols:
                conn.execute('ALTER TABLE "strategic_objectives_config" ADD COLUMN "fiscal_year" INTEGER')
                conn.execute(
                    'UPDATE "strategic_objectives_config" '
                    f'SET fiscal_year = COALESCE(CAST(strftime("%Y", fecha_inicial) AS INTEGER), CAST(strftime("%Y", fecha_final) AS INTEGER), (SELECT a.fiscal_year FROM strategic_axes_config a WHERE a.id = strategic_objectives_config.eje_id), {current_year}) '
                    'WHERE fiscal_year IS NULL OR fiscal_year = 0'
                )
            conn.execute(
                'CREATE INDEX IF NOT EXISTS "ix_strategic_objectives_config_fiscal_year" ON "strategic_objectives_config" ("fiscal_year")'
            )
        poa_activities_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='poa_activities'"
        ).fetchone()
        if poa_activities_exists:
            poa_cols = {row[1] for row in conn.execute('PRAGMA table_info("poa_activities")').fetchall()}
            if "tenant_id" not in poa_cols:
                conn.execute('ALTER TABLE "poa_activities" ADD COLUMN "tenant_id" VARCHAR DEFAULT "default"')
                conn.execute(
                    'UPDATE "poa_activities" SET tenant_id = COALESCE((SELECT tenant_id FROM strategic_objectives_config o WHERE o.id = poa_activities.objective_id), "default") WHERE tenant_id IS NULL OR tenant_id = ""'
                )
            conn.execute(
                'CREATE INDEX IF NOT EXISTS "ix_poa_activities_tenant_id" ON "poa_activities" ("tenant_id")'
            )
            if "fecha_inicial" not in poa_cols:
                conn.execute('ALTER TABLE "poa_activities" ADD COLUMN "fecha_inicial" DATE')
            if "fecha_final" not in poa_cols:
                conn.execute('ALTER TABLE "poa_activities" ADD COLUMN "fecha_final" DATE')
            if "inicio_forzado" not in poa_cols:
                conn.execute('ALTER TABLE "poa_activities" ADD COLUMN "inicio_forzado" BOOLEAN DEFAULT 0')
            if "entrega_estado" not in poa_cols:
                conn.execute('ALTER TABLE "poa_activities" ADD COLUMN "entrega_estado" VARCHAR DEFAULT "ninguna"')
            if "entrega_solicitada_por" not in poa_cols:
                conn.execute('ALTER TABLE "poa_activities" ADD COLUMN "entrega_solicitada_por" VARCHAR DEFAULT ""')
            if "entrega_solicitada_at" not in poa_cols:
                conn.execute('ALTER TABLE "poa_activities" ADD COLUMN "entrega_solicitada_at" DATETIME')
            if "entrega_aprobada_por" not in poa_cols:
                conn.execute('ALTER TABLE "poa_activities" ADD COLUMN "entrega_aprobada_por" VARCHAR DEFAULT ""')
            if "entrega_aprobada_at" not in poa_cols:
                conn.execute('ALTER TABLE "poa_activities" ADD COLUMN "entrega_aprobada_at" DATETIME')
            if "recurrente" not in poa_cols:
                conn.execute('ALTER TABLE "poa_activities" ADD COLUMN "recurrente" BOOLEAN DEFAULT 0')
            if "periodicidad" not in poa_cols:
                conn.execute('ALTER TABLE "poa_activities" ADD COLUMN "periodicidad" VARCHAR DEFAULT ""')
            if "cada_xx_dias" not in poa_cols:
                conn.execute('ALTER TABLE "poa_activities" ADD COLUMN "cada_xx_dias" INTEGER')
            if "fiscal_year" not in poa_cols:
                conn.execute('ALTER TABLE "poa_activities" ADD COLUMN "fiscal_year" INTEGER')
                conn.execute(
                    'UPDATE "poa_activities" '
                    f'SET fiscal_year = COALESCE(CAST(strftime("%Y", fecha_inicial) AS INTEGER), CAST(strftime("%Y", fecha_final) AS INTEGER), (SELECT o.fiscal_year FROM strategic_objectives_config o WHERE o.id = poa_activities.objective_id), {current_year}) '
                    'WHERE fiscal_year IS NULL OR fiscal_year = 0'
                )
            conn.execute(
                'CREATE INDEX IF NOT EXISTS "ix_poa_activities_fiscal_year" ON "poa_activities" ("fiscal_year")'
            )
        poa_subactivities_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='poa_subactivities'"
        ).fetchone()
        if poa_subactivities_exists:
            poa_sub_cols = {row[1] for row in conn.execute('PRAGMA table_info("poa_subactivities")').fetchall()}
            if "tenant_id" not in poa_sub_cols:
                conn.execute('ALTER TABLE "poa_subactivities" ADD COLUMN "tenant_id" VARCHAR DEFAULT "default"')
                conn.execute(
                    'UPDATE "poa_subactivities" SET tenant_id = COALESCE((SELECT tenant_id FROM poa_activities a WHERE a.id = poa_subactivities.activity_id), "default") WHERE tenant_id IS NULL OR tenant_id = ""'
                )
            conn.execute(
                'CREATE INDEX IF NOT EXISTS "ix_poa_subactivities_tenant_id" ON "poa_subactivities" ("tenant_id")'
            )
            if "fecha_inicial" not in poa_sub_cols:
                conn.execute('ALTER TABLE "poa_subactivities" ADD COLUMN "fecha_inicial" DATE')
            if "fecha_final" not in poa_sub_cols:
                conn.execute('ALTER TABLE "poa_subactivities" ADD COLUMN "fecha_final" DATE')
            if "parent_subactivity_id" not in poa_sub_cols:
                conn.execute('ALTER TABLE "poa_subactivities" ADD COLUMN "parent_subactivity_id" INTEGER')
            if "nivel" not in poa_sub_cols:
                conn.execute('ALTER TABLE "poa_subactivities" ADD COLUMN "nivel" INTEGER DEFAULT 1')
            conn.execute('CREATE INDEX IF NOT EXISTS "ix_poa_subactivities_parent_subactivity_id" ON "poa_subactivities" ("parent_subactivity_id")')
            conn.execute('CREATE INDEX IF NOT EXISTS "ix_poa_subactivities_nivel" ON "poa_subactivities" ("nivel")')
            if "fiscal_year" not in poa_sub_cols:
                conn.execute('ALTER TABLE "poa_subactivities" ADD COLUMN "fiscal_year" INTEGER')
                conn.execute(
                    'UPDATE "poa_subactivities" '
                    f'SET fiscal_year = COALESCE(CAST(strftime("%Y", fecha_inicial) AS INTEGER), CAST(strftime("%Y", fecha_final) AS INTEGER), (SELECT a.fiscal_year FROM poa_activities a WHERE a.id = poa_subactivities.activity_id), {current_year}) '
                    'WHERE fiscal_year IS NULL OR fiscal_year = 0'
                )
            conn.execute('CREATE INDEX IF NOT EXISTS "ix_poa_subactivities_fiscal_year" ON "poa_subactivities" ("fiscal_year")')
        conn.commit()


def ensure_documentos_schema() -> None:
    if not IS_SQLITE_DATAMAIN or not PRIMARY_DB_PATH:
        return
    with sqlite3.connect(PRIMARY_DB_PATH) as conn:
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='documentos_evidencia'"
        ).fetchone()
        if not table_exists:
            return
        cols = {row[1] for row in conn.execute('PRAGMA table_info(\"documentos_evidencia\")').fetchall()}
        if "tenant_id" not in cols:
            conn.execute('ALTER TABLE \"documentos_evidencia\" ADD COLUMN \"tenant_id\" VARCHAR DEFAULT \"default\"')
            conn.execute('UPDATE \"documentos_evidencia\" SET tenant_id = \"default\" WHERE tenant_id IS NULL OR tenant_id = \"\"')
        conn.execute(
            'CREATE INDEX IF NOT EXISTS \"ix_documentos_evidencia_tenant_id\" ON \"documentos_evidencia\" (\"tenant_id\")'
        )
        conn.commit()


def ensure_forms_schema() -> None:
    if not IS_SQLITE_DATAMAIN or not PRIMARY_DB_PATH:
        return
    with sqlite3.connect(PRIMARY_DB_PATH) as conn:
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='form_definitions'"
        ).fetchone()
        if not table_exists:
            return
        cols = {row[1] for row in conn.execute('PRAGMA table_info(\"form_definitions\")').fetchall()}
        if "tenant_id" not in cols:
            conn.execute('ALTER TABLE \"form_definitions\" ADD COLUMN \"tenant_id\" VARCHAR DEFAULT \"default\"')
            conn.execute('UPDATE \"form_definitions\" SET tenant_id = \"default\" WHERE tenant_id IS NULL OR tenant_id = \"\"')
        if "allowed_roles" not in cols:
            conn.execute('ALTER TABLE \"form_definitions\" ADD COLUMN \"allowed_roles\" JSON DEFAULT \"[]\"')
            conn.execute('UPDATE \"form_definitions\" SET allowed_roles = \"[]\" WHERE allowed_roles IS NULL OR trim(allowed_roles) = \"\"')
        conn.execute(
            'CREATE INDEX IF NOT EXISTS \"ix_form_definitions_tenant_id\" ON \"form_definitions\" (\"tenant_id\")'
        )
        conn.commit()


def unify_users_table() -> None:
    """
    Unifica usuarios legacy (`usuarios`) dentro de la tabla canónica `users`.
    Mantiene compatibilidad agregando columnas opcionales usadas por el frontend.
    """
    if not IS_SQLITE_DATAMAIN or not PRIMARY_DB_PATH:
        return

    required_columns = {
        "celular": "VARCHAR",
        "departamento": "VARCHAR",
        "puesto": "VARCHAR",
        "jefe": "VARCHAR",
        "jefe_inmediato_id": "INTEGER",
        "coach": "VARCHAR",
        "rol_id": "INTEGER",
        "imagen": "VARCHAR",
    }

    with sqlite3.connect(PRIMARY_DB_PATH) as conn:
        users_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()
        if not users_exists:
            return

        existing_users_columns = {
            row[1] for row in conn.execute('PRAGMA table_info("users")').fetchall()
        }
        for col_name, col_type in required_columns.items():
            if col_name not in existing_users_columns:
                conn.execute(f'ALTER TABLE "users" ADD COLUMN "{col_name}" {col_type}')

        users_has_role = "role" in existing_users_columns
        users_has_is_active = "is_active" in existing_users_columns

        usuarios_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='usuarios'"
        ).fetchone()
        if not usuarios_exists:
            conn.commit()
            return

        role_by_id = {
            row[0]: (row[1] or "").strip().lower()
            for row in conn.execute('SELECT id, nombre FROM "roles"').fetchall()
        }

        legacy_rows = conn.execute(
            """
            SELECT
                id, nombre, usuario, correo, celular, contrasena,
                departamento, puesto, jefe, coach, rol_id, imagen
            FROM "usuarios"
            """
        ).fetchall()

        for row in legacy_rows:
            (
                legacy_id,
                nombre,
                usuario_login,
                correo,
                celular,
                contrasena,
                departamento,
                puesto,
                jefe,
                coach,
                rol_id,
                imagen,
            ) = row

            if not usuario_login and not correo:
                continue

            role_name = normalize_role_name(role_by_id.get(rol_id, "") if rol_id else "")
            params = [usuario_login or "", correo or ""]
            existing = conn.execute(
                """
                SELECT id FROM "users"
                WHERE (username IS NOT NULL AND lower(username)=lower(?))
                   OR (email IS NOT NULL AND lower(email)=lower(?))
                LIMIT 1
                """,
                params,
            ).fetchone()

            if existing:
                update_sql = """
                    UPDATE "users"
                    SET
                        full_name = COALESCE(NULLIF(?, ''), full_name),
                        username = COALESCE(NULLIF(?, ''), username),
                        email = COALESCE(NULLIF(?, ''), email),
                        celular = COALESCE(NULLIF(?, ''), celular),
                        password = CASE
                            WHEN password IS NULL OR trim(password) = ''
                            THEN COALESCE(NULLIF(?, ''), password)
                            ELSE password
                        END,
                        departamento = COALESCE(NULLIF(?, ''), departamento),
                        puesto = COALESCE(NULLIF(?, ''), puesto),
                        jefe = COALESCE(NULLIF(?, ''), jefe),
                        coach = COALESCE(NULLIF(?, ''), coach),
                        rol_id = COALESCE(?, rol_id),
                        imagen = COALESCE(NULLIF(?, ''), imagen)
                """
                update_params = [
                    nombre or "",
                    usuario_login or "",
                    correo or "",
                    celular or "",
                    contrasena or "",
                    departamento or "",
                    puesto or "",
                    jefe or "",
                    coach or "",
                    rol_id,
                    imagen or "",
                ]
                if users_has_role:
                    update_sql += ", role = COALESCE(NULLIF(?, ''), role)"
                    update_params.append(role_name)
                if users_has_is_active:
                    update_sql += ", is_active = COALESCE(is_active, 1)"
                update_sql += " WHERE id = ?"
                update_params.append(existing[0])
                conn.execute(update_sql, update_params)
                continue

            insert_columns = [
                "id",
                "full_name",
                "username",
                "email",
                "password",
                "celular",
                "departamento",
                "puesto",
                "jefe",
                "coach",
                "rol_id",
                "imagen",
            ]
            insert_values = [
                legacy_id,
                nombre,
                usuario_login,
                correo,
                contrasena,
                celular,
                departamento,
                puesto,
                jefe,
                coach,
                rol_id,
                imagen,
            ]
            if users_has_role:
                insert_columns.append("role")
                insert_values.append(role_name or "usuario")
            if users_has_is_active:
                insert_columns.append("is_active")
                insert_values.append(1)

            quoted_columns = ", ".join(f'"{col}"' for col in insert_columns)
            placeholders = ", ".join(["?"] * len(insert_values))
            conn.execute(
                f'INSERT OR IGNORE INTO "users" ({quoted_columns}) VALUES ({placeholders})',
                insert_values,
            )

        if users_has_role and "rol_id" in {row[1] for row in conn.execute('PRAGMA table_info("users")').fetchall()}:
            for role_id, role_name in role_by_id.items():
                normalized_role = normalize_role_name(role_name)
                conn.execute(
                    """
                    UPDATE "users"
                    SET rol_id = COALESCE(rol_id, ?),
                        role = COALESCE(NULLIF(role, ''), ?)
                    WHERE lower(COALESCE(role, '')) = lower(?)
                    """,
                    (role_id, normalized_role, normalized_role),
                )

        conn.commit()


MAIN.metadata.create_all(bind=engine)
ensure_documentos_schema()
ensure_forms_schema()
unify_users_table()
ensure_default_roles()
ensure_passkey_user_schema()
ensure_strategic_axes_schema()
protect_sensitive_user_fields()
ensure_system_superadmin_user()
ensure_demo_admin_user_seed()
ensure_default_strategic_axes_data()

app = FastAPI(
    title="Módulo de Planificación Estratégica y POA",
    docs_url="/docs" if ENABLE_API_DOCS else None,
    redoc_url="/redoc" if ENABLE_API_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_API_DOCS else None,
)
# Montar archivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory=["fastapi_modulo/templates", "fastapi_modulo"])
app.state.templates = templates
app.mount("/templates", StaticFiles(directory="fastapi_modulo/templates"), name="templates")
app.mount("/icon", StaticFiles(directory="fastapi_modulo/templates/icon"), name="icon")
app.mount(
    "/modulos/activo_fijo/static",
    StaticFiles(directory="fastapi_modulo/modulos/activo_fijo/static"),
    name="activo_fijo_static",
)
register_enabled_routers(app, phase="startup")


def _ensure_ia_config_columns():
    """Agrega columnas faltantes a ia_config de forma idempotente."""
    try:
        from fastapi_modulo.db import engine
        import sqlalchemy as _sa
        with engine.connect() as _conn:
            existing = {
                row[1]
                for row in _conn.execute(_sa.text("PRAGMA table_info(ia_config)")).fetchall()
            }
            migrations = [
                ("ai_system_prompt", "ALTER TABLE ia_config ADD COLUMN ai_system_prompt VARCHAR"),
                ("ai_temperature",   "ALTER TABLE ia_config ADD COLUMN ai_temperature REAL DEFAULT 0.7"),
                ("ai_top_p",         "ALTER TABLE ia_config ADD COLUMN ai_top_p REAL DEFAULT 0.9"),
                ("ai_num_predict",   "ALTER TABLE ia_config ADD COLUMN ai_num_predict INTEGER DEFAULT 700"),
            ]
            for col, stmt in migrations:
                if col not in existing:
                    _conn.execute(_sa.text(stmt))
                    print(f"[migration] ia_config: columna '{col}' agregada")
            _conn.commit()
    except Exception as exc:
        print(f"[migration] Error aplicando columnas ia_config: {exc}")


@app.on_event("startup")
async def seed_default_users_on_startup():
    _ensure_ia_config_columns()
    try:
        ensure_default_roles()
        ensure_system_superadmin_user()
        ensure_demo_admin_user_seed()
    except Exception as exc:
        print(f"[seed-startup] Error al sembrar usuarios por defecto: {exc}")


@app.get("/health")
def healthcheck(request: Request):
    payload = {"status": "ok"}
    if HEALTH_INCLUDE_DETAILS:
        db_info = _get_request_dataMAIN_info(request)
        payload.update(
            {
                "environment": APP_ENV,
                "dataMAIN_engine": db_info["engine"],
                "dataMAIN_name": db_info["name"],
                "dataMAIN_path": db_info["path"],
                "request_host": db_info["host"],
            }
        )
    return payload


@app.get("/healthz")
def healthcheck_liveness():
    return {"status": "ok", "service": "avancoop"}


def _not_found_context(request: Request, title: str = "Pagina no existe") -> Dict[str, str]:
    login_identity = _get_login_identity_context()
    colores = get_colores_context()
    sidebar_top_color = (colores.get("sidebar-top") or "#1f2a3d").strip()
    is_dark_bg = _is_dark_color(sidebar_top_color)
    return {
        "request": request,
        "title": title,
        "app_favicon_url": login_identity.get("login_favicon_url"),
        "company_logo_url": login_identity.get("login_logo_url"),
        "sidebar_top_color": sidebar_top_color,
        "not_found_text_color": "#ffffff" if is_dark_bg else "#2b2b2b",
        "not_found_highlight_color": "#ffffff" if is_dark_bg else "#1f1f1f",
    }


def _is_dark_color(value: str) -> bool:
    color = (value or "").strip().lower()
    if color.startswith("#"):
        hex_color = color[1:]
        if len(hex_color) == 3:
            hex_color = "".join(ch * 2 for ch in hex_color)
        if len(hex_color) == 6:
            try:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
                return luminance < 0.5
            except ValueError:
                return True
    return True


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    path = request.url.path
    if path.startswith("/api/"):
        return JSONResponse({"success": False, "error": exc.detail}, status_code=exc.status_code)
    if exc.status_code in {403, 404}:
        return templates.TemplateResponse(
            "not_found.html",
            _not_found_context(request),
            status_code=404,
        )
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


app.middleware("http")(enforce_backend_login)


def hash_password(password: str) -> str:
    iterations = 120_000
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    stored = (stored_hash or "").strip()
    if not stored:
        return False
    try:
        algo, iterations, salt, digest_hex = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            if ALLOW_LEGACY_PLAINTEXT_PASSWORDS:
                return hmac.compare_digest(password, stored)
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        if ALLOW_LEGACY_PLAINTEXT_PASSWORDS:
            return hmac.compare_digest(password, stored)
        return False


def _find_user_by_login(db, login_value: str) -> Optional[Usuario]:
    normalized_login = (login_value or "").strip().lower()
    if not normalized_login:
        return None
    login_hash = _sensitive_lookup_hash(normalized_login)
    user = db.query(Usuario).filter(Usuario.usuario_hash == login_hash).first()
    if not user:
        user = db.query(Usuario).filter(Usuario.correo_hash == login_hash).first()
    if not user:
        user = db.query(Usuario).filter(func.lower(Usuario.usuario) == normalized_login).first()
    if not user:
        user = db.query(Usuario).filter(func.lower(Usuario.correo) == normalized_login).first()
    return user


def _resolve_user_role_name(db, user: Usuario) -> str:
    role_name = "usuario"
    if user.rol_id:
        role = db.query(Rol).filter(Rol.id == user.rol_id).first()
        if role and role.nombre:
            role_name = normalize_role_name(role.nombre)
    elif user.role:
        role_name = normalize_role_name(user.role)
    return role_name


def _apply_auth_cookies(response: Response, request: Request, username: str, role_name: str) -> None:
    tenant_id = _normalize_tenant_id(request.cookies.get("tenant_id") or os.environ.get("DEFAULT_TENANT_ID", "default"))
    response.set_cookie(
        AUTH_COOKIE_NAME,
        _build_session_cookie(username, role_name, tenant_id),
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=SESSION_MAX_AGE_SECONDS,
    )
    response.set_cookie(
        "user_role",
        normalize_role_name(role_name),
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=SESSION_MAX_AGE_SECONDS,
    )
    response.set_cookie(
        "user_name",
        username,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=SESSION_MAX_AGE_SECONDS,
    )
    response.set_cookie(
        "tenant_id",
        tenant_id,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=SESSION_MAX_AGE_SECONDS,
    )


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    raw = (value or "").strip()
    if not raw:
        return b""
    raw += "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw.encode("ascii"))


def _passkey_rp_id(request: Request) -> str:
    host = (request.url.hostname or "").strip().lower()
    if host:
        return host
    host_header = (request.headers.get("host") or "").split(":")[0].strip().lower()
    return host_header or "localhost"


def _passkey_origin(request: Request) -> str:
    origin_header = (request.headers.get("origin") or "").strip()
    if origin_header:
        return origin_header
    return f"{request.url.scheme}://{request.url.netloc}"


def _build_passkey_token(action: str, user_id: int, challenge: str, rp_id: str, origin: str) -> str:
    payload_json = json.dumps(
        {
            "a": action,
            "u": int(user_id),
            "c": challenge,
            "r": rp_id,
            "o": origin,
            "exp": int(time.time()) + PASSKEY_CHALLENGE_TTL_SECONDS,
        },
        separators=(",", ":"),
        ensure_ascii=True,
    )
    payload = _b64url_encode(payload_json.encode("utf-8"))
    signature = hmac.new(
        AUTH_COOKIE_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{signature}"


def _read_passkey_token(token: str, expected_action: str) -> Optional[Dict[str, Any]]:
    if not token or "." not in token:
        return None
    payload, signature = token.rsplit(".", 1)
    expected_signature = hmac.new(
        AUTH_COOKIE_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return None
    try:
        data = json.loads(_b64url_decode(payload).decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("a") != expected_action:
        return None
    try:
        if int(data.get("exp", 0)) < int(time.time()):
            return None
        data["u"] = int(data.get("u"))
        data["c"] = str(data.get("c", ""))
        data["r"] = str(data.get("r", ""))
        data["o"] = str(data.get("o", ""))
    except (TypeError, ValueError):
        return None
    return data


def _build_mfa_gate_token(user_id: int) -> str:
    payload_json = json.dumps(
        {
            "u": int(user_id),
            "exp": int(time.time()) + PASSKEY_CHALLENGE_TTL_SECONDS,
        },
        separators=(",", ":"),
        ensure_ascii=True,
    )
    payload = _b64url_encode(payload_json.encode("utf-8"))
    signature = hmac.new(
        AUTH_COOKIE_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{signature}"


def _read_mfa_gate_token(token: str) -> Optional[int]:
    if not token or "." not in token:
        return None
    payload, signature = token.rsplit(".", 1)
    expected_signature = hmac.new(
        AUTH_COOKIE_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return None
    try:
        data = json.loads(_b64url_decode(payload).decode("utf-8"))
        if int(data.get("exp", 0)) < int(time.time()):
            return None
        return int(data.get("u", 0))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def _normalize_totp_secret(secret: str) -> str:
    return re.sub(r"[^A-Z2-7]", "", (secret or "").strip().upper())


def _totp_code_for_counter(secret: str, counter: int) -> str:
    normalized = _normalize_totp_secret(secret)
    if not normalized:
        return ""
    padded = normalized + "=" * ((8 - len(normalized) % 8) % 8)
    try:
        key = base64.b32decode(padded, casefold=True)
    except Exception:
        return ""
    digest = hmac.new(key, struct.pack(">Q", int(counter)), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = (
        ((digest[offset] & 0x7F) << 24)
        | ((digest[offset + 1] & 0xFF) << 16)
        | ((digest[offset + 2] & 0xFF) << 8)
        | (digest[offset + 3] & 0xFF)
    )
    return f"{binary % 1000000:06d}"


def _verify_totp_code(secret: str, code: str) -> bool:
    normalized_code = re.sub(r"\s+", "", (code or "").strip())
    if not re.fullmatch(r"\d{6}", normalized_code):
        return False
    period = max(1, TOTP_PERIOD_SECONDS)
    current_counter = int(time.time() // period)
    window = max(0, TOTP_ALLOWED_DRIFT_STEPS)
    for drift in range(-window, window + 1):
        if hmac.compare_digest(_totp_code_for_counter(secret, current_counter + drift), normalized_code):
            return True
    return False


def _get_user_totp_secret(user: Optional[Usuario], role_name: str) -> str:
    if normalize_role_name(role_name) != "autoridades":
        return ""
    user_secret = (getattr(user, "totp_secret", "") or "").strip()
    user_enabled = bool(getattr(user, "totp_enabled", False))
    if user_enabled and user_secret:
        return user_secret
    return (os.environ.get("AUTHORITIES_TOTP_SECRET") or "").strip()


def _parse_client_data(client_data_b64: str) -> Optional[Dict[str, Any]]:
    try:
        client_data_bytes = _b64url_decode(client_data_b64)
        payload = json.loads(client_data_bytes.decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    payload["_raw_bytes"] = client_data_bytes
    return payload


def _is_demo_account(username: str) -> bool:
    return (username or "").strip().lower() == "demo"


def _current_user_record(request: Request, db) -> Optional[Usuario]:
    session_username = (
        getattr(request.state, "user_name", None)
        or getattr(request.state, "username", None)
        or request.cookies.get("user_name")
        or request.cookies.get("username")
        or request.cookies.get("usuario")
        or request.cookies.get("email")
        or ""
    ).strip()
    if not session_username:
        session_token = request.cookies.get(AUTH_COOKIE_NAME, "")
        session_data = _read_session_cookie(session_token)
        if isinstance(session_data, dict):
            session_username = str(session_data.get("username") or "").strip()
    if not session_username:
        return None
    lookup_hash = _sensitive_lookup_hash(session_username)
    user = db.query(Usuario).filter(Usuario.usuario_hash == lookup_hash).first()
    if not user:
        user = db.query(Usuario).filter(Usuario.correo_hash == lookup_hash).first()
    if not user:
        normalized = session_username.lower()
        user = db.query(Usuario).filter(func.lower(Usuario.usuario) == normalized).first()
    if not user:
        user = db.query(Usuario).filter(func.lower(Usuario.correo) == session_username.lower()).first()
    return user


def _user_aliases(user: Optional[Usuario], session_username: str) -> Set[str]:
    aliases: Set[str] = set()
    for raw in [
        session_username,
        _decrypt_sensitive(user.full_name) if user else "",
        _decrypt_sensitive(user.correo) if user else "",
        (user.full_name if user else "") or "",
    ]:
        value = (raw or "").strip().lower()
        if value:
            aliases.add(value)
    return aliases


def _date_to_iso(value: Optional[Date]) -> str:
    if not value:
        return ""
    return value.isoformat()


def _parse_date_field(value: Any, field_name: str, required: bool = True) -> tuple[Optional[Date], Optional[str]]:
    raw = str(value or "").strip()
    if not raw:
        if required:
            return None, f"{field_name} es obligatoria"
        return None, None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date(), None
    except ValueError:
        return None, f"{field_name} debe tener formato YYYY-MM-DD"


def _validate_date_range(start_date: Optional[date], end_date: Optional[date], label: str) -> Optional[str]:
    if not start_date or not end_date:
        return f"{label}: fecha inicial y fecha final son obligatorias"
    if start_date > end_date:
        return f"{label}: la fecha inicial no puede ser mayor que la fecha final"
    return None


def _validate_child_date_range(
    child_start: date,
    child_end: date,
    parent_start: Optional[date],
    parent_end: Optional[date],
    child_label: str,
    parent_label: str,
) -> Optional[str]:
    if not parent_start or not parent_end:
        return f"{parent_label} no tiene fechas definidas para delimitar {child_label.lower()}"
    if child_start < parent_start or child_end > parent_end:
        return (
            f"{child_label} debe estar dentro del rango de {parent_label} "
            f"({parent_start.isoformat()} a {parent_end.isoformat()})"
        )
    return None


def _activity_status(activity: POAActivity, today: Optional[date] = None) -> str:
    delivery_state = (activity.entrega_estado or "").strip().lower()
    if delivery_state == "aprobada":
        return "Terminada"
    if delivery_state == "declarada":
        return "Terminada"
    if delivery_state == "pendiente":
        return "En revisión"
    current = today or datetime.utcnow().date()
    if activity.fecha_inicial and current < activity.fecha_inicial and not bool(activity.inicio_forzado):
        return "No iniciada"
    if activity.fecha_final and current > activity.fecha_final:
        return "Atrasada"
    return "En proceso"


def _resolve_process_owner_for_objective(objective: StrategicObjectiveConfig, axis: Optional[StrategicAxisConfig]) -> str:
    owner = (objective.lider or "").strip()
    if owner:
        return owner
    return (axis.lider_departamento or "").strip() if axis else ""


def _is_user_process_owner(request: Request, db, process_owner: str) -> bool:
    if is_admin_or_superadmin(request):
        return True
    owner = (process_owner or "").strip().lower()
    if not owner:
        return False
    session_username = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()
    user = _current_user_record(request, db)
    aliases = _user_aliases(user, session_username)
    if owner in aliases:
        return True
    user_department = (user.departamento or "").strip().lower() if user and user.departamento else ""
    return bool(user_department and user_department == owner)


def _notification_user_key(request: Request, db) -> str:
    session_username = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()
    user = _current_user_record(request, db)
    if user and getattr(user, "id", None):
        return f"user:{int(user.id)}"
    if session_username:
        return f"username:{session_username.lower()}"
    return ""


def _public_client_ip(request: Request) -> str:
    forwarded_for = (request.headers.get("x-forwarded-for") or "").strip()
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = (request.headers.get("x-real-ip") or "").strip()
    if real_ip:
        return real_ip
    return (request.client.host if request.client else "") or ""


def _is_public_ip_address(value: str) -> bool:
    raw = (value or "").strip()
    if not raw:
        return False
    try:
        ip_obj = ipaddress.ip_address(raw)
    except ValueError:
        return False
    if (
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
    ):
        return False
    return True


def _geoip_lookup_by_ip(ip_address: str) -> Dict[str, str]:
    ip_value = (ip_address or "").strip()
    if not _is_public_ip_address(ip_value):
        return {"country": "", "region": "", "city": ""}

    now_ts = int(time.time())
    cached = _GEOIP_CACHE.get(ip_value)
    if cached and int(cached.get("expires_at") or 0) > now_ts:
        return {
            "country": str(cached.get("country") or ""),
            "region": str(cached.get("region") or ""),
            "city": str(cached.get("city") or ""),
        }

    resolved = {"country": "", "region": "", "city": ""}
    provider_urls = [
        f"https://ipwho.is/{ip_value}",
        f"https://ipapi.co/{ip_value}/json/",
    ]
    timeout = httpx.Timeout(1.8, connect=1.0)
    for url in provider_urls:
        try:
            response = httpx.get(url, timeout=timeout)
            if response.status_code != 200:
                continue
            data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            if not isinstance(data, dict):
                continue
            if "ipwho.is" in url and data.get("success") is False:
                continue
            country = (
                str(data.get("country_code") or data.get("countryCode") or data.get("country") or "")
                .strip()
                .upper()
            )
            region = str(data.get("region") or data.get("regionName") or "").strip()
            city = str(data.get("city") or "").strip()
            if country or region or city:
                resolved = {"country": country, "region": region, "city": city}
                break
        except Exception:
            continue

    _GEOIP_CACHE[ip_value] = {
        "country": resolved["country"],
        "region": resolved["region"],
        "city": resolved["city"],
        "expires_at": now_ts + GEOIP_CACHE_TTL_SECONDS,
    }
    return resolved


def _public_client_location(request: Request) -> Dict[str, str]:
    country = (
        request.headers.get("cf-ipcountry")
        or request.headers.get("x-vercel-ip-country")
        or request.headers.get("x-country-code")
        or ""
    ).strip().upper()
    region = (
        request.headers.get("x-vercel-ip-country-region")
        or request.headers.get("x-region")
        or ""
    ).strip()
    city = (request.headers.get("x-vercel-ip-city") or request.headers.get("x-city") or "").strip()
    if country and (region or city):
        return {"country": country, "region": region, "city": city}

    resolved = _geoip_lookup_by_ip(_public_client_ip(request))
    if not country:
        country = (resolved.get("country") or "").strip().upper()
    if not region:
        region = (resolved.get("region") or "").strip()
    if not city:
        city = (resolved.get("city") or "").strip()
    return {"country": country, "region": region, "city": city}


def _sanitize_public_page(value: str) -> str:
    raw = (value or "").strip().lower()
    sanitized = re.sub(r"[^a-z0-9_-]+", "-", raw).strip("-")
    return sanitized or "funcionalidades"


QUIZ_CORRECT_ANSWERS: Dict[str, str] = {
    "q1": "b",
    "q2": "a",
    "q3": "c",
    "q4": "b",
    "q5": "d",
    "q6": "a",
    "q7": "c",
    "q8": "b",
    "q9": "a",
    "q10": "d",
}


def _quiz_discount_by_correct(correct_count: int) -> int:
    score = max(0, int(correct_count))
    if score >= 9:
        return 60
    if score == 8:
        return 50
    if score == 7:
        return 40
    if score == 6:
        return 30
    if score == 5:
        return 20
    if score >= 3:
        return 10
    return 0


def is_hidden_user(request: Request, username: Optional[str]) -> bool:
    if is_superadmin(request):
        return False
    return (username or "").strip().lower() in {u.lower() for u in HIDDEN_SYSTEM_USERS}


def _build_session_cookie(username: str, role: str, tenant_id: str) -> str:
    payload_json = json.dumps(
        {
            "u": username.strip(),
            "r": role.strip().lower(),
            "t": _normalize_tenant_id(tenant_id),
        },
        separators=(",", ":"),
        ensure_ascii=True,
    )
    payload = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("ascii").rstrip("=")
    signature = hmac.new(
        AUTH_COOKIE_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{signature}"


def _read_session_cookie(token: str) -> Optional[Dict[str, str]]:
    if not token or "." not in token:
        return None
    payload, signature = token.rsplit(".", 1)
    expected_signature = hmac.new(
        AUTH_COOKIE_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return None
    try:
        padding = "=" * (-len(payload) % 4)
        payload_json = base64.urlsafe_b64decode((payload + padding).encode("ascii")).decode("utf-8")
        data = json.loads(payload_json)
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    username = str(data.get("u", "")).strip()
    role = str(data.get("r", "")).strip().lower()
    if not username or not role:
        return None
    tenant_id = _normalize_tenant_id(str(data.get("t", "")).strip() or os.environ.get("DEFAULT_TENANT_ID", "default"))
    return {"username": username, "role": role, "tenant_id": tenant_id}

@app.post("/api/public/track-visit")
def track_public_visit(request: Request, data: dict = Body(default={})):
    page = _sanitize_public_page(str(data.get("page") or "funcionalidades"))
    db = SessionLocal()
    try:
        geo = _public_client_location(request)
        visit = PublicLandingVisit(
            page=page,
            ip_address=_public_client_ip(request),
            user_agent=request.headers.get("user-agent") or "",
            referrer=request.headers.get("referer") or "",
            country=geo["country"],
            region=geo["region"],
            city=geo["city"],
        )
        db.add(visit)
        db.commit()
        return JSONResponse({"success": True})
    except Exception as exc:
        db.rollback()
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)
    finally:
        db.close()


@app.get("/api/public/landing-metrics")
def public_landing_metrics(request: Request):
    page = _sanitize_public_page(request.query_params.get("page", "funcionalidades"))
    db = SessionLocal()
    try:
        total_visits = db.query(PublicLandingVisit).filter(PublicLandingVisit.page == page).count()
        unique_visitors = (
            db.query(func.count(func.distinct(PublicLandingVisit.ip_address)))
            .filter(PublicLandingVisit.page == page, PublicLandingVisit.ip_address.isnot(None))
            .scalar()
            or 0
        )
        today_start = datetime.combine(datetime.utcnow().date(), datetime.min.time())
        visits_today = (
            db.query(PublicLandingVisit)
            .filter(PublicLandingVisit.page == page, PublicLandingVisit.created_at >= today_start)
            .count()
        )
        recent_rows = (
            db.query(
                PublicLandingVisit.country,
                PublicLandingVisit.region,
                PublicLandingVisit.city,
                PublicLandingVisit.ip_address,
            )
            .filter(PublicLandingVisit.page == page)
            .order_by(PublicLandingVisit.created_at.desc())
            .limit(700)
            .all()
        )
        location_counts: Dict[str, int] = {}
        for row in recent_rows:
            country = (row.country or "").strip()
            region = (row.region or "").strip()
            city = (row.city or "").strip()
            if not (country or region or city):
                resolved = _geoip_lookup_by_ip(str(row.ip_address or "").strip())
                country = (resolved.get("country") or "").strip()
                region = (resolved.get("region") or "").strip()
                city = (resolved.get("city") or "").strip()
            if city and region:
                key = f"{city}, {region}"
            elif city and country:
                key = f"{city}, {country}"
            elif region and country:
                key = f"{region}, {country}"
            elif country:
                key = country
            else:
                key = "Ubicación no disponible"
            location_counts[key] = location_counts.get(key, 0) + 1
        top_locations = sorted(
            [{"label": key, "count": value} for key, value in location_counts.items()],
            key=lambda item: item["count"],
            reverse=True,
        )[:4]
        return JSONResponse(
            {
                "success": True,
                "data": {
                    "page": page,
                    "total_visits": int(total_visits),
                    "unique_visitors": int(unique_visitors),
                    "visits_today": int(visits_today),
                    "top_locations": top_locations,
                },
            }
        )
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)
    finally:
        db.close()


@app.post("/api/public/lead-request")
def public_lead_request(request: Request, data: dict = Body(default={})):
    nombre = (data.get("nombre") or "").strip()
    organizacion = (data.get("organizacion") or "").strip()
    cargo = (data.get("cargo") or "").strip()
    email = (data.get("email") or "").strip().lower()
    telefono = (data.get("telefono") or "").strip()
    mensaje = (data.get("mensaje") or "").strip()
    source_page = _sanitize_public_page(str(data.get("source_page") or "funcionalidades"))

    if len(nombre) < 2:
        return JSONResponse({"success": False, "error": "Nombre requerido"}, status_code=400)
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return JSONResponse({"success": False, "error": "Correo electrónico inválido"}, status_code=400)
    if len(mensaje) < 10:
        return JSONResponse({"success": False, "error": "Describe brevemente tu requerimiento"}, status_code=400)

    db = SessionLocal()
    try:
        geo = _public_client_location(request)
        record = PublicLeadRequest(
            nombre=nombre,
            organizacion=organizacion,
            cargo=cargo,
            email=email,
            telefono=telefono,
            mensaje=mensaje,
            source_page=source_page,
            ip_address=_public_client_ip(request),
            user_agent=request.headers.get("user-agent") or "",
            country=geo["country"],
            region=geo["region"],
            city=geo["city"],
        )
        db.add(record)
        db.commit()
        return JSONResponse(
            {
                "success": True,
                "message": "Gracias por tu interés. Nuestro equipo te contactará pronto.",
            }
        )
    except Exception as exc:
        db.rollback()
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)
    finally:
        db.close()


@app.post("/api/public/quiz-discount")
def public_quiz_discount(request: Request, data: dict = Body(default={})):
    nombre = (data.get("nombre") or "").strip()
    cooperativa = (data.get("cooperativa") or "").strip()
    pais = (data.get("pais") or "").strip()
    celular = (data.get("celular") or "").strip()
    raw_answers = data.get("answers") if isinstance(data.get("answers"), dict) else {}
    tenant_id = _normalize_tenant_id(str(data.get("tenant_id") or "default"))

    if len(nombre) < 2:
        return JSONResponse({"success": False, "error": "Nombre requerido"}, status_code=400)
    if len(cooperativa) < 2:
        return JSONResponse({"success": False, "error": "Cooperativa requerida"}, status_code=400)
    if len(pais) < 2:
        return JSONResponse({"success": False, "error": "País requerido"}, status_code=400)
    if len(celular) < 6:
        return JSONResponse({"success": False, "error": "Celular requerido"}, status_code=400)

    normalized_answers: Dict[str, str] = {}
    for key in QUIZ_CORRECT_ANSWERS.keys():
        value = str(raw_answers.get(key, "")).strip().lower()
        normalized_answers[key] = value
    answered = sum(1 for value in normalized_answers.values() if value)
    if answered < len(QUIZ_CORRECT_ANSWERS):
        return JSONResponse({"success": False, "error": "Responde las 10 preguntas"}, status_code=400)

    correct_count = sum(
        1 for key, expected in QUIZ_CORRECT_ANSWERS.items()
        if normalized_answers.get(key, "") == expected
    )
    discount = _quiz_discount_by_correct(correct_count)

    db = SessionLocal()
    try:
        current_count = db.query(PublicQuizSubmission).count()
        available_slots = max(0, 5 - int(current_count))
        promo_enabled = available_slots > 0
        if not promo_enabled:
            discount = 0

        record = PublicQuizSubmission(
            tenant_id=tenant_id,
            nombre=nombre,
            cooperativa=cooperativa,
            pais=pais,
            celular=celular,
            correctas=int(correct_count),
            descuento=int(discount),
            total_preguntas=len(QUIZ_CORRECT_ANSWERS),
            answers=normalized_answers,
            ip_address=_public_client_ip(request),
            user_agent=request.headers.get("user-agent") or "",
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return JSONResponse(
            {
                "success": True,
                "data": {
                    "id": record.id,
                    "correctas": int(correct_count),
                    "total": len(QUIZ_CORRECT_ANSWERS),
                    "descuento": int(discount),
                    "promo_aplicada": bool(promo_enabled),
                    "cupos_restantes": max(0, available_slots - 1),
                },
                "message": (
                    "Cuestionario enviado. Tu resultado fue calculado correctamente."
                    if promo_enabled
                    else "Cuestionario enviado. El cupo promocional de descuento ya fue cubierto."
                ),
            }
        )
    except Exception as exc:
        db.rollback()
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)
    finally:
        db.close()


# Frontend builder registrado DESPUÉS de /backend/login, /backend/404 y /backend/passkey/*
# para que el catch-all /backend/{slug} no intercepte rutas fijas del sistema.
register_enabled_routers(app, phase="late")


def get_colores_context() -> Dict[str, str]:
    from fastapi_modulo.modulos.personalizacion.modelos.theme_system import MAIN_THEME_KEYS, build_institutional_theme

    db = SessionLocal()
    try:
        stored_colors = {str(c.key or "").strip(): str(c.value or "").strip() for c in db.query(Colores).all()}
    finally:
        db.close()
    MAIN_colors = {key: stored_colors.get(key, "") for key in MAIN_THEME_KEYS}
    return build_institutional_theme(MAIN_colors)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# Almacenamiento simple en archivo para el contenido editable de Avance
AVANCE_CONTENT_FILE = "fastapi_modulo/avance_content.txt"
def get_avance_content():
    if os.path.exists(AVANCE_CONTENT_FILE):
        with open(AVANCE_CONTENT_FILE, "r", encoding="utf-8") as f:
            stored = f.read()
            if stored.strip():
                return stored
    return "<p>Sin contenido personalizado aún.</p><p>Inicio.<br>bienvenido al tablero</p>"

def set_avance_content(new_content: str):
    with open(AVANCE_CONTENT_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)

@app.get("/avan", response_class=HTMLResponse)
def avan(request: Request, edit: Optional[bool] = False):
    # Solo mostrar contenido, sin edición
    meta = {"title": "Avance", "subtitle": "Progreso y métricas clave", "description": "Resumen del estado del sistema"}
    content = get_avance_content()
    return backend_screen(
        request,
        title=meta["title"],
        subtitle=meta["subtitle"],
        description=meta["description"],
        content=content,
        floating_buttons=None,
        hide_floating_actions=True,
    )






@app.get("/perfil", response_class=HTMLResponse)
def perfil_page(request: Request):
    return RedirectResponse(url="/inicio/colaboradores?view=form&self=1", status_code=302)


def _render_no_access_module_page(request: Request, title: str, description: str, message: str = "Sin acceso, consulte con el administrador") -> HTMLResponse:
    login_identity = _get_login_identity_context()
    company_logo_url = _resolve_sidebar_logo_url(login_identity)
    safe_logo_url = escape(company_logo_url or "/templates/icon/icon.png")
    safe_message = escape(message)
    content = f"""
    <section style="width:100%;min-height:52vh;background:#ffffff;border:1px solid #dbe2ea;border-radius:24px;padding:24px;box-sizing:border-box;display:grid;grid-template-rows:auto 1fr;gap:16px;">
        <div style="display:flex;align-items:flex-start;justify-content:flex-start;">
            <img src="{safe_logo_url}" alt="Logo de la empresa" style="max-width:180px;max-height:72px;width:auto;height:auto;object-fit:contain;">
        </div>
        <div style="display:flex;align-items:center;justify-content:center;">
            <div style="text-align:center;max-width:640px;">
                <p style="margin:0;color:#0f172a;font-size:2rem;font-weight:800;letter-spacing:-0.03em;line-height:1.2;">{safe_message}</p>
            </div>
        </div>
    </section>
    """
    return render_backend_page(
        request,
        title=title,
        description=description,
        content=content,
        hide_floating_actions=True,
        show_page_header=True,
    )


def _has_app_access(request: Request, app_name: str) -> bool:
    if not is_app_access_enabled(app_name):
        return False
    if is_admin_or_superadmin(request):
        return True
    return app_name in _get_user_app_access(request)


@app.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse(url="/backend/inicio", status_code=308)


@app.head("/", response_class=HTMLResponse)
def root_head():
    return RedirectResponse(url="/backend/inicio", status_code=308)

# Área de configuración de imagen (menú)
@app.get("/configura-imagen", response_class=HTMLResponse)
def configura_imagen():
    # Aquí se usará un template en el futuro
    return "<h2>Configuración de imagen (template)</h2>"


def _render_database_tools_page(request: Request) -> HTMLResponse:
    from urllib.parse import quote_plus

    msg = (request.query_params.get("msg") or "").strip()
    status = (request.query_params.get("status") or "").strip().lower()
    flash_html = ""
    if msg:
        tone = "#166534" if status == "ok" else "#b91c1c"
        flash_html = f"<p style='margin:0 0 12px;color:{tone};font-weight:700'>{escape(msg)}</p>"
    sqlite_note = ""
    if not IS_SQLITE_DATABASE:
        sqlite_note = (
            "<p style='margin:0 0 12px;color:#92400e;font-weight:600'>"
            "La exportación/importación por archivo aplica para SQLite."
            "</p>"
        )

    content = f"""
    <section style="background:#fff;border:1px solid #dbe3ef;border-radius:14px;padding:16px;display:grid;gap:12px;max-width:760px;">
        <h3 style="margin:0;font-size:1.12rem;color:#0f172a;">Respaldo de base de datos</h3>
        <p style="margin:0;color:#475569;">Exporta e importa un archivo de base de datos para prevenir pérdida de información.</p>
        {flash_html}
        {sqlite_note}
        <div style="display:flex;flex-wrap:wrap;gap:10px;align-items:center;">
            <a href="/empresa/base-datos/exportar" style="display:inline-flex;align-items:center;justify-content:center;padding:10px 14px;border-radius:10px;border:1px solid #cbd5e1;background:#fff;color:#0f172a;text-decoration:none;font-weight:700;">
                Exportar BD
            </a>
            <form method="post" action="/empresa/base-datos/importar" enctype="multipart/form-data" style="display:inline-flex;gap:8px;align-items:center;flex-wrap:wrap;">
                <input type="file" name="db_file" accept=".db,.sqlite,.sqlite3,application/octet-stream" required style="padding:8px;border:1px solid #cbd5e1;border-radius:10px;">
                <button type="submit" style="padding:10px 14px;border-radius:10px;border:1px solid #0f172a;background:#0f172a;color:#fff;font-weight:700;cursor:pointer;">
                    Importar BD
                </button>
            </form>
        </div>
    </section>
    """
    return render_backend_page(
        request,
        title="Base de datos",
        description="Exporta e importa respaldos de la base de datos.",
        content=content,
        hide_floating_actions=True,
        show_page_header=True,
    )


def _format_bytes(size: int) -> str:
    if size <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    idx = 0
    value = float(size)
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024.0
        idx += 1
    return f"{value:.2f} {units[idx]}"


def _ensure_update_runtime_dir() -> Path:
    path = Path(UPDATE_LOG_DIR)
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        fallback = Path("/tmp") / "sipet_updates" / APP_ENV
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def _get_update_files(host: str) -> Dict[str, Path]:
    base_dir = _ensure_update_runtime_dir()
    safe_host = re.sub(r"[^a-z0-9._-]+", "-", (host or "default").lower()).strip("-") or "default"
    host_dir = base_dir / safe_host
    host_dir.mkdir(parents=True, exist_ok=True)
    return {
        "dir": host_dir,
        "history": host_dir / "history.json",
        "log": host_dir / "update.log",
        "manifest": host_dir / "last_manifest.json",
        "job": host_dir / "job.json",
        "backup_dir": host_dir / "backups",
    }


def _read_json_file(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _write_json_file(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def _append_update_history(host: str, entry: Dict[str, Any]) -> None:
    files = _get_update_files(host)
    history = _read_json_file(files["history"], [])
    if not isinstance(history, list):
        history = []
    history.append(entry)
    _write_json_file(files["history"], history[-20:])


def _version_parts(value: str) -> List[int]:
    parts: List[int] = []
    for token in re.findall(r"\d+", str(value or "")):
        try:
            parts.append(int(token))
        except ValueError:
            parts.append(0)
    return parts or [0]


def _is_version_newer(candidate: str, current: str) -> bool:
    left = _version_parts(candidate)
    right = _version_parts(current)
    max_len = max(len(left), len(right))
    left.extend([0] * (max_len - len(left)))
    right.extend([0] * (max_len - len(right)))
    return left > right


def _get_update_context(request: Request) -> Dict[str, Any]:
    db_info = _get_request_database_info(request)
    host = db_info["host"] or _normalize_host_identifier(request.headers.get("host") or request.url.hostname or "")
    manifest_url = UPDATE_SOURCE_MAP.get(host, "")
    channel = UPDATE_CHANNEL_MAP.get(host, host or "default")
    strategy = UPDATE_STRATEGY_MAP.get(host, "git-pull")
    files = _get_update_files(host or "default")
    last_manifest = _read_json_file(files["manifest"], {})
    last_job = _read_json_file(files["job"], {})
    history = _read_json_file(files["history"], [])
    return {
        "host": host,
        "db_info": db_info,
        "version": SIPET_VERSION,
        "manifest_url": manifest_url,
        "channel": channel,
        "strategy": strategy,
        "auto_update_enabled": AUTO_UPDATE_ENABLED,
        "railway": any(str(value or "").strip() for key, value in os.environ.items() if key.startswith("RAILWAY_")),
        "files": files,
        "last_manifest": last_manifest if isinstance(last_manifest, dict) else {},
        "last_job": last_job if isinstance(last_job, dict) else {},
        "history": history[-5:] if isinstance(history, list) else [],
    }


def _fetch_update_manifest(manifest_url: str) -> Dict[str, Any]:
    if not manifest_url:
        raise RuntimeError("No hay origen de actualización configurado para este sitio.")
    timeout = httpx.Timeout(UPDATE_CHECK_TIMEOUT_SECONDS, connect=min(3.0, UPDATE_CHECK_TIMEOUT_SECONDS))
    response = httpx.get(manifest_url, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("El manifest de actualización no es válido.")
    return payload


def _validate_update_manifest(context: Dict[str, Any], manifest: Dict[str, Any]) -> Dict[str, Any]:
    allowed_hosts = manifest.get("allowed_hosts") or []
    if isinstance(allowed_hosts, str):
        allowed_hosts = [allowed_hosts]
    normalized_allowed_hosts = {_normalize_host_identifier(item) for item in allowed_hosts if str(item or "").strip()}
    if normalized_allowed_hosts and context["host"] not in normalized_allowed_hosts:
        raise RuntimeError("El manifest no autoriza este host.")
    manifest_channel = str(manifest.get("channel") or "").strip()
    if manifest_channel and manifest_channel != context["channel"]:
        raise RuntimeError("El canal del manifest no corresponde a este sitio.")
    declared_strategy = str(manifest.get("strategy") or context["strategy"]).strip() or context["strategy"]
    if declared_strategy != context["strategy"]:
        raise RuntimeError("La estrategia del manifest no coincide con la estrategia permitida para este host.")
    latest_version = str(manifest.get("version") or "").strip()
    if not latest_version:
        raise RuntimeError("El manifest no incluye una versión destino.")
    return {
        "version": latest_version,
        "strategy": declared_strategy,
        "branch": str(manifest.get("branch") or "main").strip() or "main",
        "notes": str(manifest.get("notes") or "").strip(),
        "package_url": str(manifest.get("package_url") or "").strip(),
        "raw": manifest,
        "update_available": _is_version_newer(latest_version, context["version"]),
    }


def _snapshot_update_state(context: Dict[str, Any], manifest_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    latest_version = ""
    update_available = False
    if manifest_info:
        latest_version = manifest_info["version"]
        update_available = bool(manifest_info["update_available"])
    elif isinstance(context["last_manifest"], dict):
        latest_version = str(context["last_manifest"].get("version") or "").strip()
        if latest_version:
            update_available = _is_version_newer(latest_version, context["version"])
    return {
        "host": context["host"],
        "channel": context["channel"],
        "strategy": context["strategy"],
        "current_version": context["version"],
        "latest_version": latest_version,
        "update_available": update_available,
        "manifest_url": context["manifest_url"],
        "database_name": context["db_info"]["name"],
        "database_path": context["db_info"]["path"],
        "last_job": context["last_job"],
        "history": context["history"],
        "auto_update_enabled": context["auto_update_enabled"],
        "railway": context["railway"],
    }


def _start_update_job(context: Dict[str, Any], manifest_info: Dict[str, Any]) -> Dict[str, Any]:
    if not AUTO_UPDATE_ENABLED:
        raise RuntimeError("La actualización automática está deshabilitada en este entorno.")
    if context["railway"] or context["strategy"] == "manual":
        raise RuntimeError("Este sitio está configurado para actualización manual.")

    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    dirty_lines = [
        line.strip()
        for line in (status_result.stdout or "").splitlines()
        if line.strip() and not line.strip().endswith("uvicorn.log")
    ]
    if status_result.returncode != 0:
        raise RuntimeError("No se pudo validar el estado del repositorio local.")
    if dirty_lines:
        raise RuntimeError("Hay cambios locales sin confirmar. Limpia el repositorio antes de actualizar.")

    files = context["files"]
    files["backup_dir"].mkdir(parents=True, exist_ok=True)
    db_path = str(context["db_info"].get("path") or "").strip()
    backup_path = ""
    if context["db_info"]["engine"] == "sqlite" and db_path and os.path.exists(db_path):
        backup_name = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{os.path.basename(db_path)}"
        backup_path = str(files["backup_dir"] / backup_name)
        shutil.copy2(db_path, backup_path)

    job_id = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    log_path = files["log"]
    branch = manifest_info["branch"]
    env = os.environ.copy()
    env["RUN_ALEMBIC_ON_RESTART"] = "1"
    if db_path:
        env["SQLITE_DB_PATH"] = db_path
    # Este flujo ejecuta la actualizacion del workspace actual.
    # El deploy de AVANCOOP a produccion usa deploy-avancoop.sh y el servicio remoto.
    script = (
        f"cd {shlex.quote(PROJECT_ROOT)} && "
        "if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi && "
        f"git pull --ff-only origin {shlex.quote(branch)} && "
        "if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && "
        "bash reiniciar.sh"
    )
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(
            f"\n[{datetime.utcnow().isoformat()}] Inicio actualización {job_id} -> {manifest_info['version']}\n"
        )
        process = subprocess.Popen(
            ["bash", "-lc", script],
            cwd=PROJECT_ROOT,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,
        )

    job_payload = {
        "job_id": job_id,
        "status": "running",
        "started_at": datetime.utcnow().isoformat(),
        "target_version": manifest_info["version"],
        "current_version": context["version"],
        "branch": branch,
        "channel": context["channel"],
        "manifest_url": context["manifest_url"],
        "strategy": context["strategy"],
        "pid": process.pid,
        "log_path": str(log_path),
        "backup_path": backup_path,
    }
    _write_json_file(files["job"], job_payload)
    _append_update_history(
        context["host"],
        {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "started",
            "target_version": manifest_info["version"],
            "job_id": job_id,
            "backup_path": backup_path,
        },
    )
    return job_payload


def _render_ajustes_configuracion_page(request: Request) -> HTMLResponse:
    db = SessionLocal()
    db_info = _get_request_database_info(request)
    update_context = _get_update_context(request)
    current_engine = core_db.get_current_engine()
    db_name = db_info["name"] or "postgresql"
    db_file_path = os.path.abspath(db_info["path"]) if db_info["path"] else "N/A"
    db_size_bytes = 0
    tables_count = 0
    users_count = 0
    active_users_count = 0
    departments_count = 0
    runtime_store_path = os.path.abspath(RUNTIME_STORE_DIR)
    process_uptime_seconds = int(max(0, time.time() - PROCESS_STARTED_AT))
    try:
        users_count = db.query(Usuario).count()
        active_users_count = db.query(Usuario).filter(Usuario.is_active.is_(True)).count()
        departments_count = db.query(DepartamentoOrganizacional).count()
    except Exception:
        pass
    finally:
        db.close()

    try:
        tables_count = len(inspect(current_engine).get_table_names())
    except Exception:
        tables_count = 0

    if db_info["engine"] == "sqlite" and db_info["path"]:
        try:
            db_size_bytes = os.path.getsize(db_file_path) if os.path.exists(db_file_path) else 0
        except Exception:
            db_size_bytes = 0

    disk_total = disk_used = disk_free = 0
    try:
        target_path = db_file_path if (db_info["engine"] == "sqlite" and db_file_path != "N/A") else runtime_store_path
        usage = shutil.disk_usage(os.path.dirname(target_path) or ".")
        disk_total, disk_used, disk_free = usage.total, usage.used, usage.free
    except Exception:
        pass

    content = f"""
    <section style="background:#fff;border:1px solid #dbe3ef;border-radius:14px;padding:16px;display:grid;gap:12px;max-width:980px;">
        <h3 style="margin:0;font-size:1.12rem;color:#0f172a;">Configuración del sistema</h3>
        <p style="margin:0;color:#475569;">Datos principales de base de datos y salud operativa.</p>
        <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;">
            <article style="border:1px solid #e2e8f0;border-radius:10px;padding:10px;"><strong>SIPET Versión</strong><div>{escape(SIPET_VERSION)}</div></article>
            <article style="border:1px solid #e2e8f0;border-radius:10px;padding:10px;"><strong>Entorno</strong><div>{escape(APP_ENV)}</div></article>
            <article style="border:1px solid #e2e8f0;border-radius:10px;padding:10px;"><strong>Motor BD</strong><div>{escape(db_info["engine"].capitalize())}</div></article>
            <article style="border:1px solid #e2e8f0;border-radius:10px;padding:10px;"><strong>Nombre BD</strong><div>{escape(db_name)}</div></article>
            <article style="border:1px solid #e2e8f0;border-radius:10px;padding:10px;"><strong>Ruta BD</strong><div style="word-break:break-all;">{escape(db_file_path)}</div></article>
            <article style="border:1px solid #e2e8f0;border-radius:10px;padding:10px;"><strong>Tamaño BD</strong><div>{_format_bytes(db_size_bytes)}</div></article>
            <article style="border:1px solid #e2e8f0;border-radius:10px;padding:10px;"><strong>Tablas</strong><div>{tables_count}</div></article>
            <article style="border:1px solid #e2e8f0;border-radius:10px;padding:10px;"><strong>Usuarios</strong><div>{users_count} (activos: {active_users_count})</div></article>
            <article style="border:1px solid #e2e8f0;border-radius:10px;padding:10px;"><strong>Departamentos</strong><div>{departments_count}</div></article>
            <article style="border:1px solid #e2e8f0;border-radius:10px;padding:10px;"><strong>Uptime proceso</strong><div>{process_uptime_seconds} s</div></article>
            <article style="border:1px solid #e2e8f0;border-radius:10px;padding:10px;"><strong>Runtime store</strong><div style="word-break:break-all;">{escape(runtime_store_path)}</div></article>
            <article style="border:1px solid #e2e8f0;border-radius:10px;padding:10px;"><strong>Disco total</strong><div>{_format_bytes(disk_total)}</div></article>
            <article style="border:1px solid #e2e8f0;border-radius:10px;padding:10px;"><strong>Disco libre</strong><div>{_format_bytes(disk_free)}</div></article>
        </div>
    </section>
    <section style="background:#fff;border:1px solid #dbe3ef;border-radius:14px;padding:16px;display:grid;gap:12px;max-width:980px;margin-top:14px;">
        <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;">
            <div>
                <h3 style="margin:0;font-size:1.12rem;color:#0f172a;">Actualización de SIPET</h3>
                <p style="margin:4px 0 0;color:#475569;">Canal controlado por host para evitar mezclar código y base de datos.</p>
            </div>
            <div style="display:flex;gap:8px;flex-wrap:wrap;">
                <button id="sipet-update-check" type="button" style="display:inline-flex;align-items:center;justify-content:center;padding:10px 14px;border-radius:10px;border:1px solid #cbd5e1;background:#fff;color:#0f172a;font-weight:700;cursor:pointer;">
                    Verificar actualización
                </button>
                <button id="sipet-update-run" type="button" style="display:inline-flex;align-items:center;justify-content:center;padding:10px 14px;border-radius:10px;border:1px solid #0f172a;background:#0f172a;color:#fff;font-weight:700;cursor:pointer;">
                    Actualizar
                </button>
            </div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;">
            <article style="border:1px solid #e2e8f0;border-radius:10px;padding:10px;"><strong>Host</strong><div>{escape(update_context["host"] or "N/A")}</div></article>
            <article style="border:1px solid #e2e8f0;border-radius:10px;padding:10px;"><strong>Canal</strong><div>{escape(update_context["channel"])}</div></article>
            <article style="border:1px solid #e2e8f0;border-radius:10px;padding:10px;"><strong>Estrategia</strong><div>{escape(update_context["strategy"])}</div></article>
            <article style="border:1px solid #e2e8f0;border-radius:10px;padding:10px;"><strong>Origen</strong><div style="word-break:break-all;">{escape(update_context["manifest_url"] or "No configurado")}</div></article>
        </div>
        <div id="sipet-update-panel" style="border:1px solid #e2e8f0;border-radius:10px;padding:12px;background:#f8fafc;color:#0f172a;">
            <strong>Estado</strong>
            <div style="margin-top:6px;">Versión actual: {escape(SIPET_VERSION)}</div>
            <div>Última verificada: {escape(str(update_context["last_manifest"].get("version") or "No verificada"))}</div>
            <div>Último trabajo: {escape(str(update_context["last_job"].get("status") or "Sin ejecuciones"))}</div>
        </div>
        <script>
        (function () {{
          const panel = document.getElementById('sipet-update-panel');
          const checkBtn = document.getElementById('sipet-update-check');
          const runBtn = document.getElementById('sipet-update-run');

          function renderState(data) {{
            const lastJob = data.last_job || {{}};
            const history = Array.isArray(data.history) ? data.history : [];
            const historyHtml = history.length
              ? history.slice().reverse().map(function (item) {{
                  return '<li>' + (item.timestamp || '') + ' - ' + (item.status || '') + ' - ' + (item.target_version || '') + '</li>';
                }}).join('')
              : '<li>Sin historial</li>';
            panel.innerHTML =
              '<strong>Estado</strong>' +
              '<div style="margin-top:6px;">Version actual: ' + (data.current_version || '-') + '</div>' +
              '<div>Version disponible: ' + (data.latest_version || 'No verificada') + '</div>' +
              '<div>Actualizacion disponible: ' + (data.update_available ? 'Si' : 'No') + '</div>' +
              '<div>Canal: ' + (data.channel || '-') + '</div>' +
              '<div>BD: ' + (data.database_name || '-') + '</div>' +
              '<div>Ultimo trabajo: ' + (lastJob.status || 'Sin ejecuciones') + '</div>' +
              '<div>Log: ' + (lastJob.log_path || 'N/A') + '</div>' +
              '<div style="margin-top:8px;">Historial reciente:</div>' +
              '<ul style="margin:6px 0 0 18px;padding:0;">' + historyHtml + '</ul>';
          }}

          async function send(url, method) {{
            const response = await fetch(url, {{
              method: method || 'GET',
              credentials: 'same-origin',
              headers: {{ 'Accept': 'application/json' }}
            }});
            const data = await response.json();
            if (!response.ok || data.success === false) {{
              throw new Error(data.error || 'No se pudo completar la solicitud');
            }}
            return data;
          }}

          checkBtn.addEventListener('click', async function () {{
            panel.innerHTML = '<strong>Estado</strong><div style="margin-top:6px;">Verificando actualizacion...</div>';
            try {{
              const data = await send('/api/ajustes/actualizacion/verificar', 'POST');
              renderState(data);
            }} catch (error) {{
              panel.innerHTML = '<strong>Estado</strong><div style="margin-top:6px;color:#b91c1c;">' + error.message + '</div>';
            }}
          }});

          runBtn.addEventListener('click', async function () {{
            if (!window.confirm('Se generará un respaldo y se ejecutará la actualización de esta instancia. ¿Continuar?')) {{
              return;
            }}
            panel.innerHTML = '<strong>Estado</strong><div style="margin-top:6px;">Iniciando actualizacion...</div>';
            try {{
              const data = await send('/api/ajustes/actualizacion/aplicar', 'POST');
              renderState(data);
            }} catch (error) {{
              panel.innerHTML = '<strong>Estado</strong><div style="margin-top:6px;color:#b91c1c;">' + error.message + '</div>';
            }}
          }});
        }})();
        </script>
    </section>
    """
    return render_backend_page(
        request,
        title="Configuración",
        description="Parámetros principales de sistema y eficiencia operativa.",
        content=content,
        hide_floating_actions=True,
        show_page_header=True,
    )


# Placeholder para templates
# En el futuro, importar y usar templates para todas las respuestas

if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8005")))

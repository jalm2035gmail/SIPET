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
from fastapi_modulo import db as core_db
from fastapi_modulo.db import DepartamentoOrganizacional
from fastapi_modulo.personalizacion import personalizacion_router
from fastapi_modulo.membresia import membresia_router
from fastapi_modulo.modulos.proyectando.presupuesto import router as presupuesto_router
from fastapi_modulo.modulos.empleados.empleados import router as empleados_router
from fastapi_modulo.modulos.empleados.regiones import router as regiones_router
from fastapi_modulo.modulos.empleados.departamentos import router as departamentos_router
from fastapi_modulo.modulos.personalizacion.roles import (
    DEFAULT_SYSTEM_ROLES,
    ROLE_ALIASES,
    router as roles_router,
)
from fastapi_modulo.modulos.proyectando.tablero import router as proyectando_tablero_router
from fastapi_modulo.modulos.proyectando.datos_preliminares import router as proyectando_datos_preliminares_router
from fastapi_modulo.modulos.proyectando.crecimiento_general import router as proyectando_crecimiento_general_router
from fastapi_modulo.modulos.proyectando.sucursales import router as proyectando_sucursales_router
from fastapi_modulo.modulos.proyectando.no_acceso import router as proyectando_no_acceso_router
from fastapi_modulo.modulos.planificacion.ejes_poa import router as ejes_poa_router
from fastapi_modulo.modulos.planificacion.kpis import router as planificacion_kpis_router
from fastapi_modulo.modulos.planificacion.notificaciones import router as planificacion_notificaciones_router
from fastapi_modulo.modulos.planificacion.plan_estrategico import router as plan_estrategico_router
from fastapi_modulo.modulos.planificacion.poa import router as poa_router
from fastapi_modulo.modulos.control_interno.control import router as control_interno_router
from fastapi_modulo.modulos.control_interno.programa import router as ci_programa_router
from fastapi_modulo.modulos.control_interno.evidencia import router as ci_evidencia_router
from fastapi_modulo.modulos.control_interno.hallazgos import router as ci_hallazgos_router
from fastapi_modulo.modulos.control_interno.tablero import router as ci_tablero_router
from fastapi_modulo.modulos.control_interno.reportes_ci import router as ci_reportes_router
from fastapi_modulo.modulos.plantillas.plantillas_forms import router as plantillas_forms_router
from fastapi_modulo.modulos.diagnostico.diagnostico import router as diagnostico_router
from fastapi_modulo.modulos.kpis.kpis import router as kpis_router
from fastapi_modulo.modulos.frontend.frontend import router as frontend_router
from fastapi_modulo.modulos.intelicoop.intelicoop import router as intelicoop_router
from fastapi_modulo.modulos.crm.crm import router as crm_router
from fastapi_modulo.modulos.auditoria.auditoria import router as auditoria_router
from fastapi_modulo.modulos.activo_fijo.activo_fijo import router as activo_fijo_router
from fastapi_modulo.modulos.multiempresa.multiempresa import router as multiempresa_router
from fastapi_modulo.modulos.brujula.brujuia import router as brujula_router
from fastapi_modulo.modulos.capacitacion.capacitacion import router as capacitacion_router
from fastapi_modulo.ajustes_ia import router as ajustes_ia_router
from fastapi_modulo.modulos.ia_router import ia_router
from fastapi import Response, Form, Body
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi import Depends
from typing import Set

import struct
import ipaddress
import httpx
from reportes.reportes import (
    SYSTEM_REPORT_HEADER_TEMPLATE_ID,
    build_default_report_header_template,
    router as reportes_router,
)
templates = Jinja2Templates(directory="fastapi_modulo")
date = Date

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

HIDDEN_SYSTEM_USERS = {"0konomiyaki"}
PROCESS_STARTED_AT = time.time()
SIPET_VERSION = "1.00.00"
SYSTEM_APP_ACCESS_OPTIONS = (
    "Mi tablero",
    "Conversaciones",
    "BSC",
    "Organización",
    "Estrategia y táctica",
    "Datos financieros",
    "Control y seguimiento",
    "KPIs",
    "Reportes",
    "Empresa",
    "Intelicoop",
    "Brújula",
    "CRM",
    "Auditoria",
    "ActivoFijo",
    "Multiempresa",
    "Capacitacion",
)
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
PLANTILLAS_STORE_PATH = (os.environ.get("PLANTILLAS_STORE_PATH") or os.path.join(RUNTIME_STORE_DIR, "plantillas_store.json")).strip()
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
NON_DATA_FIELD_TYPES = {"header", "paragraph", "html", "divider", "pagebreak"}
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


def _get_request_database_info(request: Optional[Request] = None) -> Dict[str, str]:
    host = ""
    if request is not None:
        forwarded_host = request.headers.get("x-forwarded-host")
        host = (forwarded_host or request.headers.get("host") or request.url.hostname or "").strip()
    return core_db.get_current_database_info(host)


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
            return list(SYSTEM_APP_ACCESS_OPTIONS)
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
        return visible
    except Exception:
        return []


def _get_user_web_roles(request: Request) -> list:
    """Return the web_roles list for the current session user (from colab meta JSON)."""
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
        return raw.get(user_id, {}).get("web_roles", []) if isinstance(raw, dict) else []
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
    if ext in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
        return ext
    content_type = (upload.content_type or "").lower()
    if "svg" in content_type:
        return ".svg"
    if "webp" in content_type:
        return ".webp"
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
    allowed_exts = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
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
    # Optimizar imagen: redimensionar y convertir a WebP según el tipo de asset
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
    safe_base = _sanitize_document_name(os.path.splitext(upload.filename or "documento")[0])
    final_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{safe_base}_{secrets.token_hex(4)}{ext}"
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


def _resolve_personalizacion_logo_empresa_url() -> str:
    uploads_dir = os.path.join("fastapi_modulo", "modulos", "personalizacion", "uploads")
    candidates = sorted(
        glob.glob(os.path.join(uploads_dir, "logo_empresa.*")),
        key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0,
        reverse=True,
    )
    if not candidates:
        return ""
    selected_path = candidates[0]
    filename = os.path.basename(selected_path)
    version = int(os.path.getmtime(selected_path)) if os.path.exists(selected_path) else 0
    return f"/personalizar/uploads/{filename}?v={version}"


def _resolve_sidebar_logo_url(login_identity: Dict[str, str]) -> str:
    identity_data = _load_login_identity()
    identity_logo_filename = str(identity_data.get("logo_filename") or "").strip()
    identity_logo_url = str(login_identity.get("login_logo_url") or "").strip()

    # Si el administrador configuró un logo en Identidad institucional, tiene prioridad.
    if identity_logo_filename and identity_logo_filename != DEFAULT_LOGIN_IDENTITY["logo_filename"]:
        return identity_logo_url or "/templates/icon/icon.png"

    # Si Identidad institucional no está personalizado, usa el logo por defecto de Ajustes/Colores.
    default_logo_url = _resolve_personalizacion_logo_empresa_url()
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


def _load_plantillas_store() -> List[Dict[str, str]]:
    if not os.path.exists(PLANTILLAS_STORE_PATH):
        return _with_system_templates([])
    try:
        with open(PLANTILLAS_STORE_PATH, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return _with_system_templates([])
    if not isinstance(loaded, list):
        return _with_system_templates([])
    templates = []
    for item in loaded:
        if not isinstance(item, dict):
            continue
        templates.append(
            {
                "id": str(item.get("id") or "").strip(),
                "nombre": str(item.get("nombre") or "").strip(),
                "html": str(item.get("html") or ""),
                "css": str(item.get("css") or ""),
                "created_at": str(item.get("created_at") or ""),
                "updated_at": str(item.get("updated_at") or ""),
            }
        )
    return _with_system_templates([tpl for tpl in templates if tpl["id"] and tpl["nombre"]])


def _with_system_templates(templates: List[Dict[str, str]]) -> List[Dict[str, str]]:
    default_header = build_default_report_header_template()
    has_header = any(
        str(tpl.get("id", "")).strip() == SYSTEM_REPORT_HEADER_TEMPLATE_ID
        or str(tpl.get("nombre", "")).strip().lower() == "encabezado"
        for tpl in templates
    )
    if has_header:
        return templates
    return [default_header, *templates]


def _save_plantillas_store(templates: List[Dict[str, str]]) -> None:
    os.makedirs(os.path.dirname(PLANTILLAS_STORE_PATH), exist_ok=True)
    with open(PLANTILLAS_STORE_PATH, "w", encoding="utf-8") as fh:
        json.dump(templates, fh, ensure_ascii=False, indent=2)


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


def _render_backend_base(
    request: Request,
    title: str,
    subtitle: Optional[str] = None,
    description: Optional[str] = None,
    content: str = "",
    view_buttons: Optional[List[Dict]] = None,
    view_buttons_html: str = "",
    hide_floating_actions: bool = True,
    show_page_header: bool = True,
    page_title: Optional[str] = None,
    page_description: Optional[str] = None,
    section_title: Optional[str] = None,
    section_label: Optional[str] = None,
    floating_buttons: Optional[List[Dict]] = None,
    floating_actions_html: str = "",
    floating_actions_screen: str = "personalization",
) -> HTMLResponse:
    rendered_view_buttons = view_buttons_html or build_view_buttons_html(view_buttons)
    can_manage_personalization = is_superadmin(request)
    login_identity = _get_login_identity_context()
    sidebar_logo_url = _resolve_sidebar_logo_url(login_identity)
    resolved_title = (page_title or title or "Sin titulo").strip()
    resolved_description = (page_description or description or subtitle or "Descripcion pendiente").strip()
    context = {
        "request": request,
        "title": title,
        "subtitle": subtitle,
        "page_title": resolved_title,
        "page_description": resolved_description,
        "section_title": (section_title or "Contenido").strip(),
        "section_label": (section_label or "Seccion").strip(),
        "content": content,
        "view_buttons_html": rendered_view_buttons,
        "floating_buttons": floating_buttons,
        "floating_actions_html": floating_actions_html,
        "floating_actions_screen": floating_actions_screen,
        "hide_floating_actions": hide_floating_actions,
        "show_page_header": show_page_header,
        "colores": get_colores_context(),
        "can_manage_personalization": can_manage_personalization,
        "app_favicon_url": login_identity.get("login_favicon_url"),
        "login_logo_url": login_identity.get("login_logo_url"),
        "sidebar_logo_url": sidebar_logo_url,
        "user_app_access": _get_user_app_access(request),
        "app_env": APP_ENV,
        "is_superadmin_user": is_superadmin(request),
        "is_admin_or_superadmin_user": is_admin_or_superadmin(request),
    }
    return templates.TemplateResponse("base.html", context)


def backend_screen(
    request: Request,
    title: str,
    subtitle: Optional[str] = None,
    description: Optional[str] = None,
    content: str = "",
    view_buttons: Optional[List[Dict]] = None,
    view_buttons_html: str = "",
    floating_buttons: Optional[List[Dict]] = None,
    hide_floating_actions: bool = False,
    show_page_header: bool = True,
    page_title: Optional[str] = None,
    page_description: Optional[str] = None,
    section_title: Optional[str] = None,
    section_label: Optional[str] = None,
):
    """
    Helper para renderizar una pantalla backend con panel flotante y botones de vistas.
    - view_buttons: lista de dicts {label, view?, url, icon}
    - floating_buttons: lista de dicts {label, onclick}
    """
    return _render_backend_base(
        request=request,
        title=title,
        subtitle=subtitle,
        description=description,
        content=content,
        view_buttons=view_buttons,
        view_buttons_html=view_buttons_html,
        hide_floating_actions=hide_floating_actions,
        show_page_header=show_page_header,
        page_title=page_title,
        page_description=page_description,
        section_title=section_title,
        section_label=section_label,
        floating_buttons=floating_buttons,
    )

DATABASE_URL = core_db.DATABASE_URL
IS_SQLITE_DATABASE = DATABASE_URL.startswith("sqlite:///")
PRIMARY_DB_PATH = core_db.get_current_database_info().get("path") or None
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
Base = declarative_base()
engine = core_db.engine
SessionLocal = core_db.SessionLocal

class Colores(Base):
    __tablename__ = "colores"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(String)

# --- NUEVO: Modelos para roles y usuarios ---
class Rol(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True)
    descripcion = Column(String)

class Usuario(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column("full_name", String)
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
    webauthn_credential_id = Column(String, unique=True, index=True)
    webauthn_public_key = Column(String)
    webauthn_sign_count = Column(Integer, default=0)
    totp_secret = Column(String)
    totp_enabled = Column(Boolean, default=False)
    jefe_inmediato = relationship("Usuario", remote_side=[id], backref="subordinados")


class StrategicAxisConfig(Base):
    __tablename__ = "strategic_axes_config"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, default="default")
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


class StrategicObjectiveConfig(Base):
    __tablename__ = "strategic_objectives_config"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, default="default")
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


class POAActivity(Base):
    __tablename__ = "poa_activities"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, default="default")
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


class POASubactivity(Base):
    __tablename__ = "poa_subactivities"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, default="default")
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


class POADeliverableApproval(Base):
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


class FormDefinition(Base):
    __tablename__ = "form_definitions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    tenant_id = Column(String, index=True, default="default")
    description = Column(String)
    config = Column(JSON, default=dict)
    allowed_roles = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    fields = relationship("FormField", back_populates="form", cascade="all, delete-orphan")
    submissions = relationship("FormSubmission", back_populates="form", cascade="all, delete-orphan")


class FormField(Base):
    __tablename__ = "form_fields"

    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("form_definitions.id"), nullable=False, index=True)
    field_type = Column(String, nullable=False)
    label = Column(String, nullable=False)
    name = Column(String, nullable=False)
    placeholder = Column(String)
    help_text = Column(String)
    default_value = Column(String)
    is_required = Column(Boolean, default=False)
    validation_rules = Column(JSON, default=dict)
    options = Column(JSON, default=list)
    order = Column(Integer, default=0)
    conditional_logic = Column(JSON, default=dict)

    form = relationship("FormDefinition", back_populates="fields")


class FormSubmission(Base):
    __tablename__ = "form_submissions"

    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("form_definitions.id"), nullable=False, index=True)
    data = Column(JSON, default=dict)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String)
    user_agent = Column(String)

    form = relationship("FormDefinition", back_populates="submissions")


class DocumentoEvidencia(Base):
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


class UserNotificationRead(Base):
    __tablename__ = "user_notification_reads"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_key", "notification_id", name="uq_notification_read_scope"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True, default="default")
    user_key = Column(String, nullable=False, index=True)
    notification_id = Column(String, nullable=False, index=True)
    read_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PublicLandingVisit(Base):
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


class PublicLeadRequest(Base):
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


class PublicQuizSubmission(Base):
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
            existing.nombre = existing.nombre or "Super Administrador"
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
                nombre="Super Administrador",
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
            existing.nombre = existing.nombre or "Usuario Demo"
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
                nombre="Usuario Demo",
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
    if not IS_SQLITE_DATABASE or not PRIMARY_DB_PATH:
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
    if not IS_SQLITE_DATABASE or not PRIMARY_DB_PATH:
        return
    with sqlite3.connect(PRIMARY_DB_PATH) as conn:
        cols = {row[1] for row in conn.execute('PRAGMA table_info("users")').fetchall()}
        if "webauthn_credential_id" not in cols:
            conn.execute('ALTER TABLE "users" ADD COLUMN "webauthn_credential_id" VARCHAR')
        if "webauthn_public_key" not in cols:
            conn.execute('ALTER TABLE "users" ADD COLUMN "webauthn_public_key" VARCHAR')
        if "webauthn_sign_count" not in cols:
            conn.execute('ALTER TABLE "users" ADD COLUMN "webauthn_sign_count" INTEGER DEFAULT 0')
        if "totp_secret" not in cols:
            conn.execute('ALTER TABLE "users" ADD COLUMN "totp_secret" VARCHAR')
        if "totp_enabled" not in cols:
            conn.execute('ALTER TABLE "users" ADD COLUMN "totp_enabled" BOOLEAN DEFAULT 0')
        conn.execute(
            'CREATE UNIQUE INDEX IF NOT EXISTS "ix_users_webauthn_credential_id" ON "users" ("webauthn_credential_id")'
        )
        conn.commit()


def ensure_strategic_axes_schema() -> None:
    if not IS_SQLITE_DATABASE or not PRIMARY_DB_PATH:
        return
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
        conn.commit()


def ensure_documentos_schema() -> None:
    if not IS_SQLITE_DATABASE or not PRIMARY_DB_PATH:
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
    if not IS_SQLITE_DATABASE or not PRIMARY_DB_PATH:
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
    if not IS_SQLITE_DATABASE or not PRIMARY_DB_PATH:
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


Base.metadata.create_all(bind=engine)
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
templates = Jinja2Templates(directory="fastapi_modulo/templates")
app.state.templates = templates
app.mount("/templates", StaticFiles(directory="fastapi_modulo/templates"), name="templates")
app.mount("/icon", StaticFiles(directory="fastapi_modulo/templates/icon"), name="icon")

app.include_router(personalizacion_router)
app.include_router(membresia_router)
app.include_router(roles_router)
app.include_router(presupuesto_router, prefix="/proyectando")
app.include_router(empleados_router)
app.include_router(regiones_router)
app.include_router(departamentos_router)
app.include_router(proyectando_tablero_router)
app.include_router(proyectando_datos_preliminares_router)
app.include_router(proyectando_crecimiento_general_router)
app.include_router(proyectando_sucursales_router)
app.include_router(proyectando_no_acceso_router)
app.include_router(plan_estrategico_router)
app.include_router(poa_router)
app.include_router(planificacion_kpis_router)
app.include_router(planificacion_notificaciones_router)
app.include_router(ejes_poa_router)
app.include_router(control_interno_router)
app.include_router(ci_programa_router)
app.include_router(ci_evidencia_router)
app.include_router(ci_hallazgos_router)
app.include_router(ci_tablero_router)
app.include_router(ci_reportes_router)
app.include_router(plantillas_forms_router)
app.include_router(diagnostico_router)
app.include_router(intelicoop_router)
app.include_router(crm_router)
app.include_router(auditoria_router)
app.include_router(activo_fijo_router)
app.include_router(multiempresa_router)
app.include_router(brujula_router)
app.include_router(capacitacion_router)

app.include_router(reportes_router)
app.include_router(ajustes_ia_router)
app.include_router(ia_router)

from fastapi_modulo.modulos.notificaciones.notificaciones import router as notificaciones_router
app.include_router(kpis_router)
app.include_router(notificaciones_router)


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
        db_info = _get_request_database_info(request)
        payload.update(
            {
                "environment": APP_ENV,
                "database_engine": db_info["engine"],
                "database_name": db_info["name"],
                "database_path": db_info["path"],
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


def _is_public_frontend_page_path(path: str) -> bool:
    if not path.startswith("/web/"):
        return False
    slug = (path[len("/web/"):] or "").strip().strip("/")
    if not slug or "/" in slug:
        return False
    if slug in {"descripcion", "funcionalidades", "login", "404", "passkey"}:
        return False
    try:
        from fastapi_modulo.modulos.frontend.frontend_store import get_page_by_slug

        page = get_page_by_slug(slug, published_only=True)
        return bool(page)
    except Exception:
        return False


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


@app.middleware("http")
async def enforce_backend_login(request: Request, call_next):
    host_token = core_db.set_request_host(
        request.headers.get("x-forwarded-host")
        or request.headers.get("host")
        or request.url.hostname
    )
    path = request.url.path
    public_paths = {
        "/",
        "/web",
        "/web/descripcion",
        "/web/funcionalidades",
        "/web/404",
        "/web/login",
        "/logout",
        "/health",
        "/healthz",
        "/favicon.ico",
        "/api/web/me",
    }
    if ENABLE_API_DOCS:
        public_paths.update({"/docs", "/redoc", "/openapi.json"})
    if (
        request.method == "OPTIONS"
        or path in public_paths
        or _is_public_frontend_page_path(path)
        or path.startswith("/api/public/")
        or path.startswith("/web/passkey/")
        or path.startswith("/identidad-institucional")
        or path.startswith("/templates/")
        or path.startswith("/static/")
        or path.startswith("/icon/")
        or path.startswith("/imagenes/")
        or path.startswith("/docs/")
        or path.startswith("/redoc/")
    ):
        try:
            return await call_next(request)
        finally:
            core_db.reset_request_host(host_token)

    session_token = request.cookies.get(AUTH_COOKIE_NAME, "")
    session_data = _read_session_cookie(session_token)
    if not session_data:
        try:
            if path.startswith("/api/") or path.startswith("/guardar-colores"):
                return JSONResponse({"success": False, "error": "No autenticado"}, status_code=401)
            return templates.TemplateResponse(
                "not_found.html",
                _not_found_context(request),
                status_code=404,
            )
        finally:
            core_db.reset_request_host(host_token)

    try:
        request.state.user_name = session_data["username"]
        request.state.user_role = session_data["role"]
        request.state.tenant_id = _normalize_tenant_id(session_data.get("tenant_id"))

        if (
            CSRF_PROTECTION_ENABLED
            and request.method in {"POST", "PUT", "PATCH", "DELETE"}
            and not path.startswith("/web/passkey/")
            and not path.startswith("/identidad-institucional")
            and not _is_same_origin_request(request)
        ):
            if path.startswith("/api/") or path.startswith("/guardar-colores"):
                return JSONResponse({"success": False, "error": "CSRF validation failed"}, status_code=403)
            return templates.TemplateResponse(
                "not_found.html",
                _not_found_context(request, title="Solicitud no válida"),
                status_code=403,
            )

        return await call_next(request)
    finally:
        core_db.reset_request_host(host_token)


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
        _decrypt_sensitive(user.usuario) if user else "",
        _decrypt_sensitive(user.correo) if user else "",
        (user.nombre if user else "") or "",
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

@app.post("/guardar-colores")
async def guardar_colores(request: Request, data: dict = Body(...)):
    try:
        db = SessionLocal()
        for key, value in data.items():
            color = db.query(Colores).filter(Colores.key == key).first()
            if color:
                color.value = value
            else:
                color = Colores(key=key, value=value)
                db.add(color)
        db.commit()
        db.close()
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.get("/guardar-colores")
async def obtener_colores():
    try:
        db = SessionLocal()
        colores = db.query(Colores).all()
        db.close()
        data = {c.key: c.value for c in colores}
        return JSONResponse({"success": True, "data": data})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
@app.get("/api/web/me")
def api_web_me(request: Request):
    """Returns the current user's web roles for the admin bar on public pages."""
    # Read session manually — this endpoint is public so middleware skips auth
    session_token = request.cookies.get(AUTH_COOKIE_NAME, "")
    session_data = _read_session_cookie(session_token) if session_token else None
    if not session_data:
        return {"authenticated": False, "is_superadmin": False, "web_roles": [], "role": "", "username": ""}
    role = normalize_role_name(session_data.get("role") or "")
    username = (session_data.get("username") or "").strip()
    superadmin = role == "superadministrador"
    if not superadmin:
        # build a temporary request-like state to reuse helper
        request.state.user_name = username
        request.state.user_role = role
        web_roles = _get_user_web_roles(request)
    else:
        web_roles = ["editor", "designer"]
    can_use_bar = superadmin or bool(web_roles)
    # Read sidebar-bottom color from DB (same key used by personalización)
    bar_color = "#0f172a"
    try:
        _cdb = SessionLocal()
        _col = _cdb.query(Colores).filter(Colores.key == "sidebar-bottom").first()
        if _col and _col.value:
            bar_color = _col.value.strip()
        _cdb.close()
    except Exception:
        pass
    return {
        "authenticated": can_use_bar,
        "is_superadmin": superadmin,
        "web_roles": web_roles,
        "role": role,
        "username": username,
        "builder_url": "/frontend/builder",
        "bar_color": bar_color,
    }


@app.get("/web", response_class=HTMLResponse)
def web(request: Request):
    login_identity = _get_login_identity_context()
    return templates.TemplateResponse(
        "frontend/web_blank.html",
        {
            "request": request,
            "title": "SIPET",
            "app_favicon_url": login_identity.get("login_favicon_url"),
            "company_logo_url": login_identity.get("login_logo_url"),
            "login_company_short_name": login_identity.get("login_company_short_name"),
            "menu_position": login_identity.get("menu_position"),
        },
    )


@app.get("/web/descripcion", response_class=HTMLResponse)
def web_descripcion(request: Request):
    login_identity = _get_login_identity_context()
    return templates.TemplateResponse(
        "frontend/web.html",
        {
            "request": request,
            "title": "SIPET",
            "app_favicon_url": login_identity.get("login_favicon_url"),
            "company_logo_url": login_identity.get("login_logo_url"),
            "menu_position": login_identity.get("menu_position"),
        },
    )


@app.get("/web/funcionalidades", response_class=HTMLResponse)
def web_funcionalidades(request: Request):
    login_identity = _get_login_identity_context()
    return templates.TemplateResponse(
        "frontend/modulo_funcionalidades.html",
        {
            "request": request,
            "title": "Funcionalidades | SIPET",
            "app_favicon_url": login_identity.get("login_favicon_url"),
            "company_logo_url": login_identity.get("login_logo_url"),
            "menu_position": login_identity.get("menu_position"),
        },
    )


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


@app.get("/web/login", response_class=HTMLResponse)
def web_login(request: Request):
    login_identity = _get_login_identity_context()
    return templates.TemplateResponse(
        "web_login.html",
        {
            "request": request,
            "title": "Login",
            "login_error": "",
            **login_identity,
        },
    )


@app.get("/web/404", response_class=HTMLResponse)
def web_not_found(request: Request):
    return templates.TemplateResponse(
        "not_found.html",
        _not_found_context(request),
    )


@app.post("/web/login")
def web_login_submit(
    request: Request,
    usuario: str = Form(""),
    contrasena: str = Form(""),
    codigo_autenticador: str = Form(""),
):
    login_identity = _get_login_identity_context()
    if _is_login_rate_limited(request):
        return templates.TemplateResponse(
            "web_login.html",
            {
                "request": request,
                "title": "Login",
                "login_error": "Demasiados intentos. Intenta de nuevo en unos minutos.",
                **login_identity,
            },
            status_code=429,
        )
    username = usuario.strip()
    password = contrasena or ""
    if not username or not password:
        _register_failed_login_attempt(request)
        return templates.TemplateResponse(
            "web_login.html",
            {
                "request": request,
                "title": "Login",
                "login_error": "Datos incorrectos, vuelva a intentarlo",
                **login_identity,
            },
            status_code=401,
        )

    db = SessionLocal()
    has_passkey = False
    totp_secret = ""
    try:
        user = _find_user_by_login(db, username)
        if not user or not verify_password(password, user.contrasena or ""):
            _register_failed_login_attempt(request)
            return templates.TemplateResponse(
                "web_login.html",
                {
                    "request": request,
                    "title": "Login",
                    "login_error": "Datos incorrectos, vuelva a intentarlo",
                    **login_identity,
                },
                status_code=401,
            )

        role_name = _resolve_user_role_name(db, user)
        session_username = _decrypt_sensitive(user.usuario) or username
        has_passkey = bool(user.webauthn_credential_id and user.webauthn_public_key)
        totp_secret = _get_user_totp_secret(user, role_name)
    finally:
        db.close()

    _clear_failed_login_attempts(request)
    if role_name == "autoridades":
        code_value = re.sub(r"\s+", "", codigo_autenticador or "")
        if code_value:
            if not totp_secret:
                _register_failed_login_attempt(request)
                return templates.TemplateResponse(
                    "web_login.html",
                    {
                        "request": request,
                        "title": "Login",
                        "login_error": "El código autenticador no está configurado para este usuario.",
                        **login_identity,
                    },
                    status_code=403,
                )
            if not _verify_totp_code(totp_secret, code_value):
                _register_failed_login_attempt(request)
                return templates.TemplateResponse(
                    "web_login.html",
                    {
                        "request": request,
                        "title": "Login",
                        "login_error": "Código de autenticador inválido.",
                        **login_identity,
                    },
                    status_code=401,
                )
            response = RedirectResponse(url="/inicio", status_code=303)
            _apply_auth_cookies(response, request, session_username, role_name)
            response.delete_cookie(PASSKEY_COOKIE_MFA_GATE)
            return response

        if not has_passkey and not totp_secret:
            return templates.TemplateResponse(
                "web_login.html",
                {
                    "request": request,
                    "title": "Login",
                    "login_error": "El rol Autoridades requiere segundo factor (biometría o autenticador) configurado.",
                    **login_identity,
                },
                status_code=403,
            )
        if has_passkey:
            response = RedirectResponse(url=f"/web/login?mfa=required&usuario={quote(username)}", status_code=303)
            response.set_cookie(
                PASSKEY_COOKIE_MFA_GATE,
                _build_mfa_gate_token(user.id),
                httponly=True,
                samesite="lax",
                secure=COOKIE_SECURE,
                max_age=PASSKEY_CHALLENGE_TTL_SECONDS,
            )
            return response
        return templates.TemplateResponse(
            "web_login.html",
            {
                "request": request,
                "title": "Login",
                "login_error": "Ingresa tu código de autenticador para completar el acceso.",
                **login_identity,
            },
            status_code=401,
        )

    response = RedirectResponse(url="/inicio", status_code=303)
    _apply_auth_cookies(response, request, session_username, role_name)
    response.delete_cookie(PASSKEY_COOKIE_MFA_GATE)
    return response


@app.post("/web/passkey/register/options")
def passkey_register_options(
    request: Request,
    payload: dict = Body(default={}),
):
    username = str(payload.get("usuario", "")).strip()
    password = str(payload.get("contrasena", ""))
    if not username or not password:
        return JSONResponse({"success": False, "error": "Usuario y contraseña son obligatorios"}, status_code=400)
    if _is_demo_account(username):
        return JSONResponse(
            {"success": False, "error": "La biometría no está habilitada para el usuario demo"},
            status_code=403,
        )

    db = SessionLocal()
    try:
        user = _find_user_by_login(db, username)
        if not user or not verify_password(password, user.contrasena or ""):
            return JSONResponse({"success": False, "error": "Credenciales inválidas"}, status_code=401)
        username_plain = _decrypt_sensitive(user.usuario) or username
        display_name = (user.nombre or "").strip() or username_plain
        challenge = _b64url_encode(secrets.token_bytes(32))
        rp_id = _passkey_rp_id(request)
        origin = _passkey_origin(request)
        token = _build_passkey_token("register", user.id, challenge, rp_id, origin)
        options: Dict[str, Any] = {
            "challenge": challenge,
            "rp": {"name": "SIPET", "id": rp_id},
            "user": {
                "id": _b64url_encode(f"user:{user.id}".encode("utf-8")),
                "name": username_plain,
                "displayName": display_name,
            },
            "pubKeyCredParams": [{"type": "public-key", "alg": -7}],
            "timeout": 60000,
            "attestation": "none",
            "authenticatorSelection": {
                "authenticatorAttachment": "platform",
                "residentKey": "preferred",
                "userVerification": "preferred",
            },
        }
        if user.webauthn_credential_id:
            options["excludeCredentials"] = [
                {
                    "id": user.webauthn_credential_id,
                    "type": "public-key",
                    "transports": ["internal"],
                }
            ]
    finally:
        db.close()

    response = JSONResponse({"success": True, "options": options})
    response.set_cookie(
        PASSKEY_COOKIE_REGISTER,
        token,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=PASSKEY_CHALLENGE_TTL_SECONDS,
    )
    return response


@app.post("/web/passkey/register/verify")
def passkey_register_verify(
    request: Request,
    payload: dict = Body(default={}),
):
    token_data = _read_passkey_token(request.cookies.get(PASSKEY_COOKIE_REGISTER, ""), "register")
    if not token_data:
        return JSONResponse({"success": False, "error": "Solicitud biométrica expirada, inténtalo de nuevo"}, status_code=400)

    credential_id = str(payload.get("id", "")).strip()
    response_payload = payload.get("response") or {}
    if not credential_id or not isinstance(response_payload, dict):
        return JSONResponse({"success": False, "error": "Respuesta biométrica inválida"}, status_code=400)

    client_data = _parse_client_data(str(response_payload.get("clientDataJSON", "")))
    public_key_b64 = str(response_payload.get("publicKey", "")).strip()
    if not client_data or not public_key_b64:
        return JSONResponse({"success": False, "error": "No se pudo registrar la clave biométrica"}, status_code=400)
    if str(client_data.get("type", "")) != "webauthn.create":
        return JSONResponse({"success": False, "error": "Tipo de autenticación no válido"}, status_code=400)
    if str(client_data.get("challenge", "")) != token_data["c"]:
        return JSONResponse({"success": False, "error": "Desafío biométrico inválido"}, status_code=400)
    if str(client_data.get("origin", "")).rstrip("/") != token_data["o"].rstrip("/"):
        return JSONResponse({"success": False, "error": "Origen no permitido para biometría"}, status_code=400)

    try:
        public_key_der = _b64url_decode(public_key_b64)
        serialization.load_der_public_key(public_key_der)
    except Exception:
        return JSONResponse({"success": False, "error": "Llave pública biométrica inválida"}, status_code=400)

    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.id == token_data["u"]).first()
        if not user:
            return JSONResponse({"success": False, "error": "Usuario no encontrado"}, status_code=404)
        user.webauthn_credential_id = credential_id
        user.webauthn_public_key = _b64url_encode(public_key_der)
        user.webauthn_sign_count = 0
        db.add(user)
        db.commit()
    except Exception:
        db.rollback()
        return JSONResponse({"success": False, "error": "No se pudo guardar la biometría"}, status_code=500)
    finally:
        db.close()

    response = JSONResponse({"success": True, "message": "Biometría registrada correctamente"})
    response.delete_cookie(PASSKEY_COOKIE_REGISTER)
    return response


@app.post("/web/passkey/auth/options")
def passkey_auth_options(
    request: Request,
    payload: dict = Body(default={}),
):
    username = str(payload.get("usuario", "")).strip()
    if not username:
        return JSONResponse({"success": False, "error": "Ingresa tu usuario para autenticar con biometría"}, status_code=400)
    if _is_demo_account(username):
        return JSONResponse(
            {"success": False, "error": "La biometría no está habilitada para el usuario demo"},
            status_code=403,
        )

    db = SessionLocal()
    try:
        user = _find_user_by_login(db, username)
        if not user or not user.webauthn_credential_id or not user.webauthn_public_key:
            return JSONResponse({"success": False, "error": "Este usuario no tiene biometría registrada"}, status_code=404)
        role_name = _resolve_user_role_name(db, user)
        if role_name == "autoridades":
            gate_user_id = _read_mfa_gate_token(request.cookies.get(PASSKEY_COOKIE_MFA_GATE, ""))
            if not gate_user_id or gate_user_id != user.id:
                return JSONResponse(
                    {"success": False, "error": "Primero valida usuario y contraseña para continuar con doble autenticación"},
                    status_code=403,
                )
        challenge = _b64url_encode(secrets.token_bytes(32))
        rp_id = _passkey_rp_id(request)
        origin = _passkey_origin(request)
        token = _build_passkey_token("auth", user.id, challenge, rp_id, origin)
        options = {
            "challenge": challenge,
            "rpId": rp_id,
            "allowCredentials": [
                {
                    "id": user.webauthn_credential_id,
                    "type": "public-key",
                    "transports": ["internal"],
                }
            ],
            "timeout": 60000,
            "userVerification": "preferred",
        }
    finally:
        db.close()

    response = JSONResponse({"success": True, "options": options})
    response.set_cookie(
        PASSKEY_COOKIE_AUTH,
        token,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=PASSKEY_CHALLENGE_TTL_SECONDS,
    )
    return response


@app.post("/web/passkey/auth/verify")
def passkey_auth_verify(
    request: Request,
    payload: dict = Body(default={}),
):
    token_data = _read_passkey_token(request.cookies.get(PASSKEY_COOKIE_AUTH, ""), "auth")
    if not token_data:
        return JSONResponse({"success": False, "error": "Solicitud biométrica expirada, inténtalo de nuevo"}, status_code=400)

    credential_id = str(payload.get("id", "")).strip()
    response_payload = payload.get("response") or {}
    if not credential_id or not isinstance(response_payload, dict):
        return JSONResponse({"success": False, "error": "Respuesta biométrica inválida"}, status_code=400)

    client_data_b64 = str(response_payload.get("clientDataJSON", "")).strip()
    auth_data_b64 = str(response_payload.get("authenticatorData", "")).strip()
    signature_b64 = str(response_payload.get("signature", "")).strip()
    if not client_data_b64 or not auth_data_b64 or not signature_b64:
        return JSONResponse({"success": False, "error": "Datos biométricos incompletos"}, status_code=400)

    client_data = _parse_client_data(client_data_b64)
    if not client_data:
        return JSONResponse({"success": False, "error": "No se pudo leer la respuesta del autenticador"}, status_code=400)
    if str(client_data.get("type", "")) != "webauthn.get":
        return JSONResponse({"success": False, "error": "Tipo de autenticación no válido"}, status_code=400)
    if str(client_data.get("challenge", "")) != token_data["c"]:
        return JSONResponse({"success": False, "error": "Desafío biométrico inválido"}, status_code=400)
    if str(client_data.get("origin", "")).rstrip("/") != token_data["o"].rstrip("/"):
        return JSONResponse({"success": False, "error": "Origen no permitido para biometría"}, status_code=400)

    try:
        authenticator_data = _b64url_decode(auth_data_b64)
        signature = _b64url_decode(signature_b64)
    except ValueError:
        return JSONResponse({"success": False, "error": "Formato biométrico inválido"}, status_code=400)

    if len(authenticator_data) < 37:
        return JSONResponse({"success": False, "error": "AuthenticatorData inválido"}, status_code=400)

    expected_rp_hash = hashlib.sha256(token_data["r"].encode("utf-8")).digest()
    rp_hash = authenticator_data[:32]
    flags = authenticator_data[32]
    sign_count = int.from_bytes(authenticator_data[33:37], "big")
    if not hmac.compare_digest(rp_hash, expected_rp_hash):
        return JSONResponse({"success": False, "error": "RP ID inválido para biometría"}, status_code=400)
    if not (flags & 0x01):
        return JSONResponse({"success": False, "error": "Se requiere presencia del usuario"}, status_code=400)

    client_data_hash = hashlib.sha256(client_data["_raw_bytes"]).digest()
    signed_payload = authenticator_data + client_data_hash

    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.id == token_data["u"]).first()
        if not user or not user.webauthn_credential_id or not user.webauthn_public_key:
            return JSONResponse({"success": False, "error": "Usuario sin biometría registrada"}, status_code=404)
        if user.webauthn_credential_id != credential_id:
            return JSONResponse({"success": False, "error": "Credencial biométrica no coincide"}, status_code=401)

        try:
            public_key = serialization.load_der_public_key(_b64url_decode(user.webauthn_public_key))
        except Exception:
            return JSONResponse({"success": False, "error": "Llave biométrica inválida"}, status_code=400)

        try:
            if isinstance(public_key, ec.EllipticCurvePublicKey):
                public_key.verify(signature, signed_payload, ec.ECDSA(hashes.SHA256()))
            elif isinstance(public_key, rsa.RSAPublicKey):
                public_key.verify(signature, signed_payload, padding.PKCS1v15(), hashes.SHA256())
            else:
                return JSONResponse({"success": False, "error": "Tipo de llave biométrica no soportado"}, status_code=400)
        except InvalidSignature:
            return JSONResponse({"success": False, "error": "Firma biométrica inválida"}, status_code=401)

        stored_sign_count = int(user.webauthn_sign_count or 0)
        if sign_count > 0 and stored_sign_count > 0 and sign_count <= stored_sign_count:
            return JSONResponse({"success": False, "error": "Contador biométrico inválido"}, status_code=401)
        if sign_count > stored_sign_count:
            user.webauthn_sign_count = sign_count
            db.add(user)
            db.commit()

        role_name = _resolve_user_role_name(db, user)
        session_username = _decrypt_sensitive(user.usuario) or _decrypt_sensitive(user.correo) or f"user-{user.id}"
    finally:
        db.close()

    response = JSONResponse({"success": True, "redirect": "/inicio"})
    _apply_auth_cookies(response, request, session_username, role_name)
    response.delete_cookie(PASSKEY_COOKIE_AUTH)
    response.delete_cookie(PASSKEY_COOKIE_MFA_GATE)
    return response


@app.get("/logout")
@app.get("/logout/")
def logout():
    response = RedirectResponse(url="/web/login", status_code=303)
    response.delete_cookie(AUTH_COOKIE_NAME)
    response.delete_cookie("user_role")
    response.delete_cookie("user_name")
    response.delete_cookie("tenant_id")
    response.delete_cookie(PASSKEY_COOKIE_AUTH)
    response.delete_cookie(PASSKEY_COOKIE_REGISTER)
    response.delete_cookie(PASSKEY_COOKIE_MFA_GATE)
    return response


# Frontend builder registrado DESPUÉS de /web/login, /web/404 y /web/passkey/*
# para que el catch-all /web/{slug} no intercepte rutas fijas del sistema.
app.include_router(frontend_router)


def get_colores_context() -> Dict[str, str]:
    db = SessionLocal()
    colores = {c.key: c.value for c in db.query(Colores).all()}
    db.close()
    return colores


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def slugify_value(value: str) -> str:
    base = (value or "").strip().lower()
    base = re.sub(r"[^a-z0-9]+", "-", base)
    base = re.sub(r"-+", "-", base).strip("-")
    return base or secrets.token_hex(4)


class FormFieldCreateSchema(BaseModel):
    field_type: str
    label: str
    name: str
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    default_value: Optional[str] = None
    is_required: bool = False
    validation_rules: Dict[str, Any] = Field(default_factory=dict)
    options: List[Dict[str, Any]] = Field(default_factory=list)
    order: int = 0
    conditional_logic: Dict[str, Any] = Field(default_factory=dict)


class FormDefinitionCreateSchema(BaseModel):
    name: str
    description: Optional[str] = None
    slug: Optional[str] = None
    tenant_id: Optional[str] = None
    is_active: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)
    allowed_roles: List[str] = Field(default_factory=list)
    fields: List[FormFieldCreateSchema] = Field(default_factory=list)


class FormFieldResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    form_id: int
    field_type: str
    label: str
    name: str
    placeholder: Optional[str]
    help_text: Optional[str]
    default_value: Optional[str]
    is_required: bool
    validation_rules: Dict[str, Any]
    options: List[Dict[str, Any]]
    order: int
    conditional_logic: Dict[str, Any]


class FormDefinitionResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    tenant_id: str
    description: Optional[str]
    config: Dict[str, Any]
    allowed_roles: List[str]
    fields: List[FormFieldResponseSchema]
    is_active: bool


class FormRenderer:
    """Servicio para renderizar y validar formularios de manera dinámica."""

    @staticmethod
    def generate_pydantic_model(
        form_definition: FormDefinition,
        visible_field_names: Optional[Set[str]] = None,
    ):
        fields: Dict[str, Any] = {}
        for field in sorted(form_definition.fields, key=lambda item: item.order or 0):
            normalized_field_type = (field.field_type or "").strip().lower()
            if normalized_field_type in NON_DATA_FIELD_TYPES:
                continue
            field_type = FormRenderer._get_pydantic_type(field.field_type)
            is_visible = True if visible_field_names is None else field.name in visible_field_names
            if field.default_value not in (None, ""):
                default_value: Any = field.default_value
            elif field.is_required and is_visible:
                default_value = ...
            else:
                default_value = None
            fields[field.name] = (
                field_type,
                Field(default=default_value, description=field.help_text or ""),
            )

        model_name = f"FormModel_{form_definition.id}"
        return create_model(model_name, **fields)

    @staticmethod
    def _get_pydantic_type(field_type: str):
        type_map = {
            "text": str,
            "email": str,
            "password": str,
            "textarea": str,
            "number": float,
            "decimal": float,
            "integer": int,
            "checkbox": bool,
            "checkboxes": List[str],
            "select": str,
            "radio": str,
            "likert": int,
            "date": str,
            "time": str,
            "daterange": List[str],
            "signature": str,
            "url": str,
            "file": str,
            "header": str,
            "paragraph": str,
            "html": str,
            "divider": str,
            "pagebreak": str,
        }
        return type_map.get((field_type or "").strip().lower(), str)

    @staticmethod
    def _to_comparable(value: Any) -> Any:
        if isinstance(value, bool):
            return value
        if value is None:
            return None
        text = str(value).strip()
        low = text.lower()
        if low in {"true", "1", "yes", "si", "on"}:
            return True
        if low in {"false", "0", "no", "off"}:
            return False
        return text

    @staticmethod
    def _evaluate_single_condition(rule: Dict[str, Any], answers: Dict[str, Any]) -> bool:
        source_field = (
            rule.get("field")
            or rule.get("source")
            or rule.get("depends_on")
            or rule.get("name")
            or ""
        )
        source_field = str(source_field).strip()
        if not source_field:
            return True

        left = FormRenderer._to_comparable(answers.get(source_field))
        right = FormRenderer._to_comparable(rule.get("value"))
        operator = str(rule.get("operator") or rule.get("op") or "equals").strip().lower()

        if operator in {"equals", "eq", "=="}:
            return left == right
        if operator in {"not_equals", "neq", "!=", "<>"}:
            return left != right
        if operator in {"contains"}:
            if left is None:
                return False
            return str(right or "") in str(left)
        if operator in {"in"}:
            candidates = rule.get("values")
            if not isinstance(candidates, list):
                candidates = [rule.get("value")]
            normalized = [FormRenderer._to_comparable(item) for item in candidates]
            return left in normalized
        if operator in {"not_in"}:
            candidates = rule.get("values")
            if not isinstance(candidates, list):
                candidates = [rule.get("value")]
            normalized = [FormRenderer._to_comparable(item) for item in candidates]
            return left not in normalized
        if operator in {"truthy", "is_true"}:
            return bool(left)
        if operator in {"falsy", "is_false"}:
            return not bool(left)
        if operator in {"greater_than", "gt", ">"}:
            try:
                return float(left) > float(right)
            except (TypeError, ValueError):
                return False
        if operator in {"greater_or_equal", "gte", ">="}:
            try:
                return float(left) >= float(right)
            except (TypeError, ValueError):
                return False
        if operator in {"less_than", "lt", "<"}:
            try:
                return float(left) < float(right)
            except (TypeError, ValueError):
                return False
        if operator in {"less_or_equal", "lte", "<="}:
            try:
                return float(left) <= float(right)
            except (TypeError, ValueError):
                return False
        return True

    @staticmethod
    def evaluate_visibility(condition: Dict[str, Any], answers: Dict[str, Any]) -> bool:
        if not isinstance(condition, dict) or not condition:
            return True

        if "show_if" in condition and isinstance(condition.get("show_if"), dict):
            return FormRenderer.evaluate_visibility(condition["show_if"], answers)
        if "hide_if" in condition and isinstance(condition.get("hide_if"), dict):
            return not FormRenderer.evaluate_visibility(condition["hide_if"], answers)

        if isinstance(condition.get("all"), list):
            return all(
                FormRenderer.evaluate_visibility(item, answers)
                for item in condition["all"]
                if isinstance(item, dict)
            )
        if isinstance(condition.get("any"), list):
            return any(
                FormRenderer.evaluate_visibility(item, answers)
                for item in condition["any"]
                if isinstance(item, dict)
            )

        return FormRenderer._evaluate_single_condition(condition, answers)

    @staticmethod
    def visible_field_names(form_definition: FormDefinition, answers: Dict[str, Any]) -> Set[str]:
        visible: Set[str] = set()
        ordered_fields = sorted(form_definition.fields, key=lambda item: item.order or 0)
        # Evalua en orden para que las condiciones puedan depender de campos anteriores.
        for field in ordered_fields:
            condition = field.conditional_logic or {}
            if FormRenderer.evaluate_visibility(condition, answers):
                visible.add(field.name)
        return visible

    @staticmethod
    def _apply_custom_rules(
        form_definition: FormDefinition,
        data: Dict[str, Any],
        visible_field_names: Optional[Set[str]] = None,
    ) -> None:
        for field in form_definition.fields:
            if visible_field_names is not None and field.name not in visible_field_names:
                continue
            rules = field.validation_rules or {}
            value = data.get(field.name)
            if value is None:
                continue

            normalized_field_type = (field.field_type or "").strip().lower()
            if normalized_field_type in NON_DATA_FIELD_TYPES:
                continue
            if normalized_field_type == "daterange":
                if not isinstance(value, list):
                    raise ValueError(f"'{field.label}' debe ser un rango de fechas")
                cleaned = [str(item).strip() for item in value if str(item).strip()]
                if len(cleaned) != 2:
                    raise ValueError(f"'{field.label}' requiere fecha inicio y fecha fin")
                data[field.name] = cleaned
                value = cleaned
            elif normalized_field_type == "url":
                parsed = urlparse(str(value).strip())
                if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    raise ValueError(f"'{field.label}' debe ser una URL válida")
            elif normalized_field_type == "signature":
                signature_value = str(value).strip()
                if field.is_required and not signature_value:
                    raise ValueError(f"'{field.label}' es obligatoria")
                if signature_value and not (
                    signature_value.startswith("data:image/")
                    or signature_value.startswith("http://")
                    or signature_value.startswith("https://")
                ):
                    raise ValueError(f"'{field.label}' no tiene un formato de firma válido")

            if isinstance(value, str):
                if "min_length" in rules and len(value) < int(rules["min_length"]):
                    raise ValueError(f"'{field.label}' requiere longitud mínima de {rules['min_length']}")
                if "max_length" in rules and len(value) > int(rules["max_length"]):
                    raise ValueError(f"'{field.label}' supera la longitud máxima de {rules['max_length']}")
                pattern = rules.get("pattern")
                if pattern and not re.match(pattern, value):
                    raise ValueError(f"'{field.label}' tiene un formato inválido")
            elif isinstance(value, list):
                if "min_length" in rules and len(value) < int(rules["min_length"]):
                    raise ValueError(f"'{field.label}' requiere al menos {rules['min_length']} selección(es)")
                if "max_length" in rules and len(value) > int(rules["max_length"]):
                    raise ValueError(f"'{field.label}' supera el máximo de {rules['max_length']} selección(es)")

            if isinstance(value, (int, float)):
                if "min" in rules and value < float(rules["min"]):
                    raise ValueError(f"'{field.label}' es menor al mínimo permitido ({rules['min']})")
                if "max" in rules and value > float(rules["max"]):
                    raise ValueError(f"'{field.label}' excede el máximo permitido ({rules['max']})")

    @staticmethod
    def render_to_json(form_definition: FormDefinition) -> Dict[str, Any]:
        fields = []
        for field in sorted(form_definition.fields, key=lambda item: item.order or 0):
            fields.append(
                {
                    "type": field.field_type,
                    "name": field.name,
                    "label": field.label,
                    "placeholder": field.placeholder,
                    "helpText": field.help_text,
                    "required": field.is_required,
                    "defaultValue": field.default_value,
                    "validation": field.validation_rules or {},
                    "options": field.options if field.field_type in {"select", "radio", "checkboxes", "likert"} else [],
                    "conditional": field.conditional_logic or {},
                }
            )

        return {
            "id": form_definition.id,
            "name": form_definition.name,
            "slug": form_definition.slug,
            "tenant_id": _normalize_tenant_id(form_definition.tenant_id or "default"),
            "description": form_definition.description,
            "allowed_roles": form_definition.allowed_roles if isinstance(form_definition.allowed_roles, list) else [],
            "fields": fields,
            "config": form_definition.config or {},
        }


def _normalize_recipients(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        candidates = [part.strip() for part in re.split(r"[;,]", raw)]
    elif isinstance(raw, list):
        candidates = [str(item).strip() for item in raw]
    else:
        return []
    return [item for item in candidates if item and "@" in item]


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "si", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _notification_email_settings(form_definition: FormDefinition) -> Dict[str, Any]:
    config = form_definition.config or {}
    notifications = config.get("notifications") if isinstance(config.get("notifications"), dict) else {}
    email_cfg = notifications.get("email") if isinstance(notifications.get("email"), dict) else {}
    enabled = _to_bool(
        email_cfg.get("enabled"),
        default=bool(email_cfg or config.get("notification_emails") or os.environ.get("FORM_NOTIFICATION_TO")),
    )
    to_list = _normalize_recipients(
        email_cfg.get("to")
        or config.get("notification_emails")
        or os.environ.get("FORM_NOTIFICATION_TO")
    )
    cc_list = _normalize_recipients(email_cfg.get("cc"))
    subject = (
        str(email_cfg.get("subject") or "").strip()
        or f"[SIPET] Nuevo envío: {form_definition.name}"
    )
    return {
        "enabled": enabled,
        "to": to_list,
        "cc": cc_list,
        "subject": subject,
    }


def send_form_submission_email_notification(
    form_definition: FormDefinition,
    submission: FormSubmission,
) -> Dict[str, Any]:
    settings = _notification_email_settings(form_definition)
    if not settings["enabled"]:
        return {"sent": False, "reason": "not_enabled"}
    recipients = [*settings["to"], *settings["cc"]]
    if not recipients:
        return {"sent": False, "reason": "no_recipients"}

    smtp_host = (os.environ.get("SMTP_HOST") or "").strip()
    smtp_port = int(os.environ.get("SMTP_PORT") or 587)
    smtp_user = (os.environ.get("SMTP_USER") or "").strip()
    smtp_password = os.environ.get("SMTP_PASSWORD") or ""
    smtp_from = (os.environ.get("SMTP_FROM") or smtp_user or "no-reply@sipet.local").strip()
    smtp_use_ssl = _to_bool(os.environ.get("SMTP_USE_SSL"), default=False)
    smtp_use_tls = _to_bool(os.environ.get("SMTP_USE_TLS"), default=not smtp_use_ssl)
    if not smtp_host:
        return {"sent": False, "reason": "smtp_not_configured"}

    message = EmailMessage()
    message["Subject"] = settings["subject"]
    message["From"] = smtp_from
    message["To"] = ", ".join(settings["to"])
    if settings["cc"]:
        message["Cc"] = ", ".join(settings["cc"])
    payload_text = json.dumps(submission.data or {}, ensure_ascii=False, indent=2)
    message.set_content(
        "\n".join(
            [
                "Se recibió un nuevo envío de formulario.",
                f"Formulario: {form_definition.name} ({form_definition.slug})",
                f"Submission ID: {submission.id}",
                f"Fecha: {submission.submitted_at.isoformat() if submission.submitted_at else ''}",
                f"IP: {submission.ip_address or ''}",
                f"User-Agent: {submission.user_agent or ''}",
                "",
                "Datos enviados:",
                payload_text,
            ]
        )
    )

    try:
        if smtp_use_ssl:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10) as server:
                if smtp_user:
                    server.login(smtp_user, smtp_password)
                server.send_message(message)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                if smtp_use_tls:
                    server.starttls()
                if smtp_user:
                    server.login(smtp_user, smtp_password)
                server.send_message(message)
    except Exception as exc:
        return {"sent": False, "reason": "smtp_error", "detail": str(exc)}
        return {"sent": True}


def _normalize_form_submission_payload(
    form_definition: FormDefinition,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    normalized = dict(payload)
    fields_by_name = {field.name: field for field in form_definition.fields}
    for field_name, field in fields_by_name.items():
        if field_name not in normalized:
            continue
        raw_value = normalized[field_name]
        field_type = (field.field_type or "").strip().lower()
        if field_type in NON_DATA_FIELD_TYPES:
            normalized.pop(field_name, None)
            continue

        if field_type == "file":
            if isinstance(raw_value, UploadFile):
                normalized[field_name] = raw_value.filename or ""
            elif isinstance(raw_value, list):
                filenames = []
                for item in raw_value:
                    if isinstance(item, UploadFile):
                        filenames.append(item.filename or "")
                    elif item is not None:
                        filenames.append(str(item))
                normalized[field_name] = filenames[0] if len(filenames) == 1 else filenames
            elif raw_value is None:
                normalized[field_name] = ""
            else:
                normalized[field_name] = str(raw_value)
            continue

        if field_type in {"checkboxes", "daterange"}:
            if isinstance(raw_value, list):
                normalized[field_name] = [str(item).strip() for item in raw_value if str(item).strip()]
            elif raw_value is None:
                normalized[field_name] = []
            else:
                cleaned = str(raw_value).strip()
                normalized[field_name] = [cleaned] if cleaned else []
            continue

        if isinstance(raw_value, list):
            normalized[field_name] = str(raw_value[0]) if raw_value else ""
        elif isinstance(raw_value, UploadFile):
            normalized[field_name] = raw_value.filename or ""
        elif raw_value is None:
            normalized[field_name] = ""
        else:
            normalized[field_name] = str(raw_value) if not isinstance(raw_value, (int, float, bool, dict)) else raw_value
    return normalized


def _normalize_webhook_configs(form_definition: FormDefinition) -> List[Dict[str, Any]]:
    config = form_definition.config or {}
    notifications = config.get("notifications") if isinstance(config.get("notifications"), dict) else {}
    raw_webhooks = notifications.get("webhooks", config.get("webhooks"))
    items: List[Any]
    if isinstance(raw_webhooks, list):
        items = raw_webhooks
    elif isinstance(raw_webhooks, dict):
        items = [raw_webhooks]
    elif isinstance(raw_webhooks, str):
        items = [raw_webhooks]
    else:
        items = []

    if not items:
        env_hook = (os.environ.get("FORM_WEBHOOK_URL") or "").strip()
        if env_hook:
            items = [env_hook]

    normalized: List[Dict[str, Any]] = []
    for item in items:
        if isinstance(item, str):
            url = item.strip()
            if not url:
                continue
            normalized.append(
                {
                    "url": url,
                    "method": "POST",
                    "headers": {},
                    "timeout": 10,
                    "payload_mode": "full",
                }
            )
            continue
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        method = str(item.get("method") or "POST").strip().upper()
        if method not in {"POST", "PUT", "PATCH", "GET"}:
            method = "POST"
        headers = item.get("headers") if isinstance(item.get("headers"), dict) else {}
        timeout_raw = item.get("timeout")
        try:
            timeout = float(timeout_raw) if timeout_raw is not None else 10.0
        except (TypeError, ValueError):
            timeout = 10.0
        payload_mode = str(item.get("payload_mode") or "full").strip().lower()
        if payload_mode not in {"full", "data_only"}:
            payload_mode = "full"
        normalized.append(
            {
                "url": url,
                "method": method,
                "headers": headers,
                "timeout": timeout,
                "payload_mode": payload_mode,
            }
        )
    return normalized


def send_form_submission_webhooks(
    form_definition: FormDefinition,
    submission: FormSubmission,
) -> Dict[str, Any]:
    hooks = _normalize_webhook_configs(form_definition)
    if not hooks:
        return {"attempted": 0, "succeeded": 0, "failed": 0, "results": []}

    base_payload = {
        "event": "form_submission.created",
        "form": {
            "id": form_definition.id,
            "name": form_definition.name,
            "slug": form_definition.slug,
        },
        "submission": {
            "id": submission.id,
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else "",
            "ip_address": submission.ip_address,
            "user_agent": submission.user_agent,
        },
        "data": submission.data or {},
    }

    results: List[Dict[str, Any]] = []
    succeeded = 0
    for hook in hooks:
        payload = (
            base_payload.get("data", {})
            if hook["payload_mode"] == "data_only"
            else base_payload
        )
        try:
            if hook["method"] == "GET":
                response = httpx.request(
                    method=hook["method"],
                    url=hook["url"],
                    params=payload if isinstance(payload, dict) else {},
                    headers=hook["headers"],
                    timeout=hook["timeout"],
                )
            else:
                response = httpx.request(
                    method=hook["method"],
                    url=hook["url"],
                    json=payload,
                    headers=hook["headers"],
                    timeout=hook["timeout"],
                )
            ok = 200 <= response.status_code < 300
            if ok:
                succeeded += 1
            results.append(
                {
                    "url": hook["url"],
                    "method": hook["method"],
                    "status_code": response.status_code,
                    "ok": ok,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "url": hook["url"],
                    "method": hook["method"],
                    "ok": False,
                    "error": str(exc),
                }
            )

    attempted = len(hooks)
    failed = attempted - succeeded
    return {"attempted": attempted, "succeeded": succeeded, "failed": failed, "results": results}


def _normalize_submission_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _build_submission_export_columns(
    form_definition: FormDefinition,
    submissions: List[FormSubmission],
) -> List[str]:
    field_names = [
        field.name
        for field in sorted(form_definition.fields, key=lambda item: item.order or 0)
        if field.name and (field.field_type or "").strip().lower() not in NON_DATA_FIELD_TYPES
    ]
    known = set(field_names)
    extra = []
    for submission in submissions:
        data = submission.data if isinstance(submission.data, dict) else {}
        for key in data.keys():
            if key and key not in known:
                known.add(key)
                extra.append(key)
    return [*field_names, *extra]


def render_backend_page(
    request: Request,
    title: str,
    description: str = "",
    content: str = "",
    subtitle: Optional[str] = None,
    hide_floating_actions: bool = True,
    view_buttons: Optional[List[Dict]] = None,
    view_buttons_html: str = "",
    floating_actions_html: str = "",
    floating_actions_screen: str = "personalization",
    show_page_header: bool = True,
    section_title: Optional[str] = None,
    section_label: Optional[str] = None,
) -> HTMLResponse:
    return _render_backend_base(
        request=request,
        title=title,
        subtitle=subtitle,
        description=description,
        content=content,
        view_buttons=view_buttons,
        view_buttons_html=view_buttons_html,
        hide_floating_actions=hide_floating_actions,
        show_page_header=show_page_header,
        page_title=title,
        page_description=description,
        section_title=section_title,
        section_label=section_label,
        floating_actions_html=floating_actions_html,
        floating_actions_screen=floating_actions_screen,
    )



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





PLAN_ESTRATEGICO_HTML = dedent("""
    <section class="pe-page">
      <style>
        .pe-page{
          --bg: #f6f8fc;
          --surface: rgba(255,255,255,.88);
          --card: #ffffff;
          --text: #0f172a;
          --muted: #64748b;
          --border: rgba(148,163,184,.38);
          --shadow: 0 18px 40px rgba(15,23,42,.08);
          --shadow-soft: 0 10px 22px rgba(15,23,42,.06);
          --radius: 18px;
          --primary: #0f3d2e;
          --primary-2: #1f6f52;
          --accent: #2563eb;
          --ok: #16a34a;
          --warn: #f59e0b;
          --crit: #ef4444;
          width: 100%;
          font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
          color: var(--text);
          background:
            radial-gradient(1200px 640px at 15% 0%, rgba(15,61,46,.10), transparent 58%),
            radial-gradient(1000px 540px at 90% 6%, rgba(37,99,235,.10), transparent 55%),
            var(--bg);
          border-radius: 18px;
        }
        .pe-wrap{
          width: 100%;
          margin: 0 auto;
          padding: 18px 0 34px;
        }
        .pe-btn{
          border-radius: 14px;
          padding: 10px 14px;
          font-weight: 800;
          border: 1px solid var(--border);
          background: rgba(255,255,255,.75);
          cursor:pointer;
          box-shadow: var(--shadow-soft);
          transition: transform .15s ease, box-shadow .15s ease, background .15s ease;
        }
        .pe-btn:hover{ transform: translateY(-1px); box-shadow: var(--shadow); background: rgba(255,255,255,.95); }
        .pe-btn--primary{ background: linear-gradient(135deg, var(--primary), var(--primary-2)); color:#fff; border-color: rgba(15,61,46,.35); }
        .pe-btn--ghost{ background: rgba(255,255,255,.78); }
        .pe-btn--soft{ background: rgba(15,61,46,.10); border-color: rgba(15,61,46,.18); color:#0b2a20; }
        .pe-kpis{
          display:grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 14px;
          margin: 16px 0 18px;
        }
        .pe-kpi{
          background: var(--surface);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          box-shadow: var(--shadow-soft);
          padding: 16px;
          backdrop-filter: blur(10px);
          -webkit-backdrop-filter: blur(10px);
          position: relative;
          overflow:hidden;
        }
        .pe-kpi:before{
          content:"";
          position:absolute;
          inset:-1px;
          background: linear-gradient(135deg, rgba(15,61,46,.12), transparent 35%, rgba(37,99,235,.10));
          opacity:.9;
          pointer-events:none;
        }
        .pe-kpi > *{ position: relative; }
        .pe-kpi__label{ color: var(--muted); font-size: 14px; font-weight: 600; }
        .pe-kpi__value{ margin-top: 10px; font-size: 34px; font-weight: 900; letter-spacing: -0.03em; }
        .pe-kpi__meta{ margin-top: 10px; display:flex; gap: 8px; flex-wrap: wrap; }
        .pe-chip{
          font-size: 12px;
          padding: 6px 10px;
          border-radius: 999px;
          background: rgba(15,23,42,.05);
          border: 1px solid rgba(15,23,42,.08);
          color: rgba(15,23,42,.72);
        }
        .pe-chip--info{ background: rgba(37,99,235,.10); border-color: rgba(37,99,235,.18); color: #1d4ed8; }
        .pe-chip--warn{ background: rgba(245,158,11,.12); border-color: rgba(245,158,11,.22); color: #92400e; }
        .pe-kpi--progress{ display:flex; flex-direction:column; }
        .pe-kpi__progress{ margin-top: 8px; display:flex; align-items:center; justify-content:flex-start; }
        .pe-ring{
          --p: 74;
          width: 86px;
          height: 86px;
          border-radius: 999px;
          background: conic-gradient(rgba(15,61,46,1) calc(var(--p) * 1%), rgba(148,163,184,.25) 0);
          display:grid;
          place-items:center;
          border: 1px solid rgba(148,163,184,.25);
          box-shadow: 0 12px 24px rgba(15,23,42,.06);
        }
        .pe-ring__inner{
          width: 66px;
          height: 66px;
          border-radius: 999px;
          background: rgba(255,255,255,.90);
          display:flex;
          flex-direction:column;
          align-items:center;
          justify-content:center;
          border: 1px solid rgba(148,163,184,.25);
        }
        .pe-ring__val{ font-weight: 900; font-size: 16px; letter-spacing: -0.02em; }
        .pe-ring__sub{ font-size: 11px; color: var(--muted); }
        .pe-grid{
          display:grid;
          grid-template-columns: 1fr;
          gap: 14px;
          align-items:start;
        }
        .pe-card{
          background: var(--surface);
          border: 1px solid var(--border);
          border-radius: 22px;
          box-shadow: var(--shadow-soft);
          padding: 16px;
          backdrop-filter: blur(10px);
          -webkit-backdrop-filter: blur(10px);
          overflow:hidden;
        }
        .pe-card__head{
          display:flex;
          align-items:flex-start;
          justify-content:space-between;
          gap: 12px;
          margin-bottom: 14px;
        }
        .pe-card__head h2{ margin:0; font-size: 20px; letter-spacing: -0.02em; }
        .pe-card__head p{ margin: 6px 0 0; color: var(--muted); font-size: 13px; }
        .pe-card__tools{ display:flex; align-items:center; gap: 10px; }
        .pe-pill{
          font-size: 12px;
          padding: 6px 10px;
          border-radius: 999px;
          background: rgba(255,255,255,.70);
          border: 1px solid var(--border);
          color: rgba(15,23,42,.72);
          white-space: nowrap;
        }
        .pe-pill--soft{ background: rgba(15,61,46,.10); border-color: rgba(15,61,46,.18); color: #0b2a20; }
        .pe-list{ display:flex; flex-direction:column; gap: 12px; }
        .pe-item{
          background: rgba(255,255,255,.80);
          border: 1px solid rgba(148,163,184,.30);
          border-radius: 18px;
          padding: 14px 14px 12px;
          box-shadow: 0 10px 20px rgba(15,23,42,.04);
          transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease;
        }
        .pe-item:hover{ transform: translateY(-1px); box-shadow: 0 16px 30px rgba(15,23,42,.07); border-color: rgba(37,99,235,.22); }
        .pe-item--active{ outline: 1px solid rgba(15,61,46,.22); background: rgba(15,61,46,.06); }
        .pe-item__top{ display:flex; align-items:flex-start; justify-content:space-between; gap: 12px; }
        .pe-item__title{ display:flex; gap: 10px; align-items:flex-start; line-height: 1.35; }
        .pe-code{
          font-weight: 900;
          color: #0b2a20;
          background: rgba(15,61,46,.10);
          border: 1px solid rgba(15,61,46,.18);
          padding: 6px 10px;
          border-radius: 999px;
          font-size: 12px;
          white-space: nowrap;
        }
        .pe-item__meta{ margin-top: 10px; display:flex; gap: 10px; flex-wrap:wrap; color: var(--muted); }
        .pe-mini{
          font-size: 12px;
          padding: 6px 10px;
          border-radius: 999px;
          background: rgba(15,23,42,.04);
          border: 1px solid rgba(15,23,42,.08);
        }
        .pe-status{
          font-size: 12px;
          font-weight: 800;
          padding: 6px 10px;
          border-radius: 999px;
          border: 1px solid var(--border);
          background: rgba(255,255,255,.70);
          color: rgba(15,23,42,.72);
          white-space: nowrap;
        }
        .pe-status--ok{ background: rgba(22,163,74,.10); border-color: rgba(22,163,74,.20); color: #166534; }
        .pe-status--warn{ background: rgba(245,158,11,.12); border-color: rgba(245,158,11,.22); color: #92400e; }
        .pe-status--neutral{ background: rgba(15,23,42,.05); border-color: rgba(15,23,42,.10); color: rgba(15,23,42,.70); }
        .pe-bar{
          margin-top: 12px;
          height: 10px;
          border-radius: 999px;
          background: rgba(148,163,184,.25);
          border: 1px solid rgba(148,163,184,.25);
          overflow:hidden;
        }
        .pe-bar__fill{ height: 100%; width: 50%; border-radius: 999px; background: linear-gradient(90deg, rgba(37,99,235,1), rgba(96,165,250,1)); }
        .pe-bar__fill--ok{ background: linear-gradient(90deg, rgba(15,61,46,1), rgba(31,111,82,1)); }
        .pe-bar__fill--warn{ background: linear-gradient(90deg, rgba(245,158,11,1), rgba(253,230,138,1)); }
        .pe-axis{ display:flex; flex-direction:column; gap: 12px; }
        .pe-axis__btn{
          width:100%;
          text-align:left;
          border: 1px solid rgba(148,163,184,.30);
          background: rgba(255,255,255,.80);
          border-radius: 18px;
          padding: 14px;
          display:flex;
          align-items:center;
          gap: 12px;
          cursor:pointer;
          box-shadow: 0 10px 20px rgba(15,23,42,.04);
          transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease;
        }
        .pe-axis__btn:hover{ transform: translateY(-1px); box-shadow: 0 16px 30px rgba(15,23,42,.07); border-color: rgba(37,99,235,.22); }
        .pe-axis__btn--active{ background: rgba(15,61,46,.06); outline: 1px solid rgba(15,61,46,.22); }
        .pe-axis__dot{ width: 10px; height: 10px; border-radius: 999px; background: var(--primary); box-shadow: 0 0 0 6px rgba(15,61,46,.10); }
        .pe-axis__dot--alt{ background: #2563eb; box-shadow: 0 0 0 6px rgba(37,99,235,.12); }
        .pe-axis__dot--alt2{ background: #7c3aed; box-shadow: 0 0 0 6px rgba(124,58,237,.12); }
        .pe-axis__dot--alt3{ background: #f59e0b; box-shadow: 0 0 0 6px rgba(245,158,11,.12); }
        .pe-axis__count{
          margin-left:auto;
          font-weight: 900;
          color: rgba(15,23,42,.72);
          background: rgba(15,23,42,.04);
          border: 1px solid rgba(15,23,42,.08);
          padding: 6px 10px;
          border-radius: 999px;
        }
        .pe-sidebox{
          margin-top: 14px;
          background: rgba(255,255,255,.80);
          border: 1px solid rgba(148,163,184,.30);
          border-radius: 18px;
          padding: 14px;
        }
        .pe-sidebox__head{ display:flex; align-items:center; justify-content:space-between; gap: 10px; }
        .pe-sidebox__grid{ margin-top: 12px; display:grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .pe-metric{
          background: rgba(15,23,42,.03);
          border: 1px solid rgba(15,23,42,.08);
          border-radius: 16px;
          padding: 12px;
        }
        .pe-metric__k{ font-size: 12px; color: var(--muted); font-weight: 700; }
        .pe-metric__v{ margin-top: 6px; font-size: 18px; font-weight: 900; letter-spacing: -0.02em; }
        .pe-metric__v--warn{ color: #92400e; }
        .pe-roadmap{ margin-top: 14px; }
        .pe-timeline{ display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 12px; }
        .pe-tlcol{
          background: rgba(255,255,255,.70);
          border: 1px solid rgba(148,163,184,.30);
          border-radius: 18px;
          padding: 12px;
        }
        .pe-tlcol__head{
          font-weight: 900;
          color: rgba(15,23,42,.78);
          padding: 8px 10px;
          border-radius: 999px;
          background: rgba(15,23,42,.04);
          border: 1px solid rgba(15,23,42,.08);
          display:inline-block;
          margin-bottom: 10px;
        }
        .pe-tlitem{
          background: rgba(255,255,255,.82);
          border: 1px solid rgba(148,163,184,.30);
          border-radius: 16px;
          padding: 12px;
          box-shadow: 0 10px 20px rgba(15,23,42,.04);
          margin-bottom: 10px;
        }
        .pe-tlitem:last-child{ margin-bottom: 0; }
        .pe-tlitem__top{ display:flex; align-items:flex-start; justify-content:space-between; gap: 10px; }
        .pe-tlitem p{ margin: 8px 0 0; color: var(--muted); font-size: 12.5px; line-height: 1.4; }
        .pe-tlmeta{ margin-top: 10px; display:flex; gap: 8px; flex-wrap:wrap; }
        .pe-tlitem--ok{ outline: 1px solid rgba(22,163,74,.18); background: rgba(22,163,74,.06); }
        .pe-tlitem--warn{ outline: 1px solid rgba(245,158,11,.18); background: rgba(245,158,11,.07); }
        .pe-tlitem--soft{ background: rgba(15,61,46,.06); outline: 1px solid rgba(15,61,46,.18); }
        @media (max-width: 1100px){
          .pe-kpis{ grid-template-columns: repeat(2, minmax(0,1fr)); }
          .pe-grid{ grid-template-columns: 1fr; }
          .pe-timeline{ grid-template-columns: repeat(2, minmax(0,1fr)); }
        }
        @media (max-width: 640px){
          .pe-kpis{ grid-template-columns: 1fr; }
          .pe-timeline{ grid-template-columns: 1fr; }
        }
      </style>

      <div class="pe-wrap">
        __CREATE_PLAN_BUTTON__
        <section class="pe-kpis">
          <article class="pe-kpi">
            <div class="pe-kpi__label">Objetivos estratégicos</div>
            <div class="pe-kpi__value">12</div>
            <div class="pe-kpi__meta"><span class="pe-chip pe-chip--info">4 por eje</span></div>
          </article>
          <article class="pe-kpi">
            <div class="pe-kpi__label">Iniciativas activas</div>
            <div class="pe-kpi__value">24</div>
            <div class="pe-kpi__meta"><span class="pe-chip">18 en ejecución</span></div>
          </article>
          <article class="pe-kpi">
            <div class="pe-kpi__label">Indicadores vinculados</div>
            <div class="pe-kpi__value">36</div>
            <div class="pe-kpi__meta"><span class="pe-chip pe-chip--warn">6 sin línea base</span></div>
          </article>
          <article class="pe-kpi pe-kpi--progress">
            <div class="pe-kpi__label">Avance del plan</div>
            <div class="pe-kpi__progress">
              <div class="pe-ring" style="--p:74;">
                <div class="pe-ring__inner">
                  <div class="pe-ring__val">74%</div>
                  <div class="pe-ring__sub">global</div>
                </div>
              </div>
            </div>
          </article>
        </section>

        <section class="pe-grid">
          <article class="pe-card">
            <div class="pe-card__head">
              <div>
                <h2>Objetivos priorizados</h2>
                <p>Portafolio vigente con estado y trazabilidad.</p>
              </div>
              <div class="pe-card__tools">
                <span class="pe-pill pe-pill--soft">12 objetivos</span>
              </div>
            </div>

            <div class="pe-list">
              <article class="pe-item pe-item--active">
                <div class="pe-item__top">
                  <div class="pe-item__title"><span class="pe-code">OE-01</span><strong>Fortalecer la sostenibilidad financiera institucional.</strong></div>
                  <span class="pe-status pe-status--ok">En meta</span>
                </div>
                <div class="pe-item__meta"><span class="pe-mini">3 iniciativas</span><span class="pe-mini">8 KPIs</span><span class="pe-mini">Líder: Dirección</span></div>
                <div class="pe-bar"><div class="pe-bar__fill pe-bar__fill--ok" style="width:81%"></div></div>
              </article>

              <article class="pe-item">
                <div class="pe-item__top">
                  <div class="pe-item__title"><span class="pe-code">OE-02</span><strong>Mejorar la satisfacción de clientes y usuarios finales.</strong></div>
                  <span class="pe-status pe-status--warn">En riesgo</span>
                </div>
                <div class="pe-item__meta"><span class="pe-mini">2 iniciativas</span><span class="pe-mini">9 KPIs</span><span class="pe-mini">Líder: Servicios</span></div>
                <div class="pe-bar"><div class="pe-bar__fill pe-bar__fill--warn" style="width:63%"></div></div>
              </article>

              <article class="pe-item">
                <div class="pe-item__top">
                  <div class="pe-item__title"><span class="pe-code">OE-03</span><strong>Optimizar procesos críticos y tiempos de respuesta.</strong></div>
                  <span class="pe-status pe-status--neutral">Seguimiento</span>
                </div>
                <div class="pe-item__meta"><span class="pe-mini">4 iniciativas</span><span class="pe-mini">11 KPIs</span><span class="pe-mini">Líder: Operaciones</span></div>
                <div class="pe-bar"><div class="pe-bar__fill" style="width:71%"></div></div>
              </article>
            </div>
          </article>

          <aside class="pe-card">
            <div class="pe-card__head">
              <div>
                <h2>Ejes estratégicos</h2>
                <p>Distribución del portafolio por eje.</p>
              </div>
            </div>

            <div class="pe-axis">
              <button class="pe-axis__btn pe-axis__btn--active" type="button" onclick="window.location.href='/ejes-estrategicos'"><span class="pe-axis__dot"></span><span>Gobernanza y cumplimiento</span><span class="pe-axis__count">3</span></button>
              <button class="pe-axis__btn" type="button" onclick="window.location.href='/ejes-estrategicos'"><span class="pe-axis__dot pe-axis__dot--alt"></span><span>Excelencia operativa</span><span class="pe-axis__count">4</span></button>
              <button class="pe-axis__btn" type="button" onclick="window.location.href='/ejes-estrategicos'"><span class="pe-axis__dot pe-axis__dot--alt2"></span><span>Innovación y digitalización</span><span class="pe-axis__count">2</span></button>
              <button class="pe-axis__btn" type="button" onclick="window.location.href='/ejes-estrategicos'"><span class="pe-axis__dot pe-axis__dot--alt3"></span><span>Desarrollo del talento</span><span class="pe-axis__count">3</span></button>
            </div>

            <div class="pe-sidebox">
              <div class="pe-sidebox__head"><strong>Resumen rápido</strong><span class="pe-pill">Corte mensual</span></div>
              <div class="pe-sidebox__grid">
                <div class="pe-metric"><div class="pe-metric__k">Hitos del trimestre</div><div class="pe-metric__v">28</div></div>
                <div class="pe-metric"><div class="pe-metric__k">Desviaciones</div><div class="pe-metric__v pe-metric__v--warn">6</div></div>
                <div class="pe-metric"><div class="pe-metric__k">Cumplimiento</div><div class="pe-metric__v">74%</div></div>
                <div class="pe-metric"><div class="pe-metric__k">Acciones correctivas</div><div class="pe-metric__v">9</div></div>
              </div>
            </div>
          </aside>
        </section>

        <article class="pe-card pe-roadmap">
          <div class="pe-card__head">
            <div>
              <h2>Hoja de ruta anual</h2>
              <p>Fases clave del ciclo estratégico.</p>
            </div>
            <div class="pe-card__tools">
              <button class="pe-btn pe-btn--soft" type="button">Exportar</button>
              <button class="pe-btn pe-btn--ghost" type="button">Vista Gantt</button>
            </div>
          </div>

          <div class="pe-timeline">
            <div class="pe-tlcol">
              <div class="pe-tlcol__head">Q1</div>
              <article class="pe-tlitem pe-tlitem--ok">
                <div class="pe-tlitem__top"><strong>Diagnóstico estratégico</strong><span class="pe-status pe-status--ok">Completo</span></div>
                <p>Actualización de línea base y priorización inicial.</p>
                <div class="pe-tlmeta"><span class="pe-mini">8 entregables</span><span class="pe-mini">Líder PMO</span></div>
              </article>
            </div>

            <div class="pe-tlcol">
              <div class="pe-tlcol__head">Q2</div>
              <article class="pe-tlitem pe-tlitem--warn">
                <div class="pe-tlitem__top"><strong>Definición de metas</strong><span class="pe-status pe-status--warn">Ajuste</span></div>
                <p>Alineación final de KPIs y responsables por objetivo.</p>
                <div class="pe-tlmeta"><span class="pe-mini">6 entregables</span><span class="pe-mini">Comité</span></div>
              </article>
            </div>

            <div class="pe-tlcol">
              <div class="pe-tlcol__head">Q3</div>
              <article class="pe-tlitem pe-tlitem--soft">
                <div class="pe-tlitem__top"><strong>Implementación</strong><span class="pe-status pe-status--neutral">En curso</span></div>
                <p>Ejecución de iniciativas con control de hitos mensuales.</p>
                <div class="pe-tlmeta"><span class="pe-mini">10 entregables</span><span class="pe-mini">Áreas</span></div>
              </article>
            </div>

            <div class="pe-tlcol">
              <div class="pe-tlcol__head">Q4</div>
              <article class="pe-tlitem">
                <div class="pe-tlitem__top"><strong>Cierre y evaluación</strong><span class="pe-status pe-status--neutral">Programado</span></div>
                <p>Lecciones aprendidas y propuesta de ajustes para el siguiente ciclo.</p>
                <div class="pe-tlmeta"><span class="pe-mini">4 entregables</span><span class="pe-mini">Dirección</span></div>
              </article>
            </div>
          </div>
        </article>
      </div>
    </section>
""")

INICIO_BSC_HTML = dedent("""
    <section class="poa-dashboard">
        <style>
            :root{
              --bg: #f6f8fc;
              --surface: rgba(255,255,255,.86);
              --card: #ffffff;
              --text: #0f172a;
              --muted: #64748b;
              --border: rgba(148,163,184,.35);
              --shadow: 0 18px 40px rgba(15,23,42,.08);
              --shadow-soft: 0 10px 22px rgba(15,23,42,.06);
              --radius: 18px;

              --primary: #2563eb;
              --primary-2: #60a5fa;
              --ok: #16a34a;
              --warn: #f59e0b;
              --crit: #ef4444;

              --chip: rgba(37,99,235,.10);
              --chip-text: #1d4ed8;
            }

            .poa-dashboard * { box-sizing: border-box; }
            .poa-dashboard{
              font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
              color: var(--text);
              background:
                radial-gradient(1200px 600px at 20% 0%, rgba(37,99,235,.10), transparent 60%),
                radial-gradient(1000px 500px at 90% 10%, rgba(96,165,250,.12), transparent 55%),
                var(--bg);
              border-radius: 18px;
              padding: 14px;
            }

            .wrap{
              width: 100%;
              padding: 18px 18px 28px;
            }

            .topbar{
              display:flex;
              gap: 12px;
              align-items:center;
              flex-wrap: wrap;
              justify-content:space-between;
              margin-bottom: 14px;
            }
            .title{
              display:flex;
              flex-direction:column;
              gap: 4px;
            }
            .title h1{
              font-size: 18px;
              margin:0;
              letter-spacing: -0.02em;
            }
            .title p{
              margin:0;
              color: var(--muted);
              font-size: 13px;
            }

            .actions{
              display:flex;
              gap:10px;
              align-items:center;
              flex-wrap: wrap;
            }
            .btn{
              border: 1px solid var(--border);
              background: rgba(255,255,255,.7);
              padding: 10px 12px;
              border-radius: 12px;
              color: var(--text);
              display:flex;
              gap:10px;
              align-items:center;
              flex-wrap: wrap;
              box-shadow: var(--shadow-soft);
              cursor:pointer;
              user-select:none;
              transition: transform .15s ease, box-shadow .15s ease, background .15s ease;
            }
            .btn:hover{ transform: translateY(-1px); box-shadow: var(--shadow); background: rgba(255,255,255,.95); }
            .btn .dot{
              width: 10px; height:10px; border-radius:50%;
              background: var(--primary);
              box-shadow: 0 0 0 6px rgba(37,99,235,.12);
            }

            .kpis{
              display:grid;
              grid-template-columns: repeat(4, minmax(0, 1fr));
              gap: 12px;
              margin: 12px 0 16px;
            }
            .kpi{
              background: var(--surface);
              border: 1px solid var(--border);
              border-radius: var(--radius);
              box-shadow: var(--shadow-soft);
              padding: 14px 14px 12px;
              backdrop-filter: blur(10px);
              -webkit-backdrop-filter: blur(10px);
              position: relative;
              overflow:hidden;
            }
            .kpi:before{
              content:"";
              position:absolute;
              inset:-1px;
              background: linear-gradient(135deg, rgba(37,99,235,.10), transparent 35%, rgba(96,165,250,.12));
              pointer-events:none;
              opacity:.8;
            }
            .kpi > *{ position: relative; }
            .kpi .label{
              font-size: 13px;
              color: var(--muted);
              margin-bottom: 10px;
              display:flex;
              align-items:center;
              justify-content:space-between;
              flex-wrap: wrap;
              gap:10px;
            }
            .kpi .value{
              font-size: 32px;
              font-weight: 700;
              letter-spacing: -0.03em;
              line-height: 1.05;
            }
            .kpi .sub{
              margin-top: 8px;
              font-size: 12px;
              color: var(--muted);
              display:flex;
              justify-content:space-between;
              flex-wrap: wrap;
              gap:10px;
            }

            .pill{
              font-size: 12px;
              padding: 6px 10px;
              border-radius: 999px;
              background: var(--chip);
              color: var(--chip-text);
              border: 1px solid rgba(37,99,235,.18);
              white-space: nowrap;
            }

            .state{
              display:inline-flex;
              gap:8px;
              align-items:center;
              font-size: 12px;
              padding: 6px 10px;
              border-radius: 999px;
              border: 1px solid var(--border);
              background: rgba(255,255,255,.65);
              color: var(--muted);
            }
            .state i{ width:8px; height:8px; border-radius:50%; display:inline-block; }
            .ok i{ background: var(--ok); box-shadow: 0 0 0 6px rgba(22,163,74,.10); }
            .warn i{ background: var(--warn); box-shadow: 0 0 0 6px rgba(245,158,11,.12); }
            .crit i{ background: var(--crit); box-shadow: 0 0 0 6px rgba(239,68,68,.12); }

            .grid{
              display:grid;
              grid-template-columns: 1.2fr 1fr;
              gap: 12px;
              align-items:start;
            }

            .panel{
              background: var(--surface);
              border: 1px solid var(--border);
              border-radius: var(--radius);
              box-shadow: var(--shadow-soft);
              padding: 14px;
              backdrop-filter: blur(10px);
              -webkit-backdrop-filter: blur(10px);
              overflow:hidden;
            }

            .panel-header{
              display:flex;
              align-items:center;
              justify-content:space-between;
              flex-wrap: wrap;
              gap: 10px;
              margin-bottom: 12px;
            }
            .panel-title{
              display:flex;
              flex-direction:column;
              gap: 4px;
            }
            .panel-title h2{
              margin:0;
              font-size: 16px;
              letter-spacing: -0.02em;
            }
            .panel-title small{
              color: var(--muted);
              font-size: 12px;
            }

            .meta-pill{
              display:inline-flex;
              align-items:center;
              gap: 8px;
              padding: 6px 10px;
              border-radius: 999px;
              background: rgba(2,132,199,.10);
              border: 1px solid rgba(2,132,199,.18);
              color: #0369a1;
              font-size: 12px;
              white-space:nowrap;
            }

            .rows{
              display:flex;
              flex-direction:column;
              gap: 10px;
            }
            .row{
              background: rgba(255,255,255,.75);
              border: 1px solid var(--border);
              border-radius: 14px;
              padding: 10px 12px;
              display:flex;
              flex-direction:column;
              gap: 10px;
              box-shadow: 0 10px 20px rgba(15,23,42,.04);
            }
            .row-top{
              display:flex;
              align-items:center;
              justify-content:space-between;
              flex-wrap: wrap;
              gap: 12px;
            }
            .row-label{
              font-weight: 600;
              font-size: 13px;
              color: #0b1220;
            }
            .row-value{
              font-weight: 700;
              font-size: 13px;
              color: #0b1220;
              white-space:nowrap;
            }
            .hint{
              font-size: 12px;
              color: var(--muted);
            }

            .progress{
              width: 100%;
              height: 10px;
              border-radius: 999px;
              background: rgba(148,163,184,.25);
              overflow:hidden;
              border: 1px solid rgba(148,163,184,.25);
            }
            .bar{
              height: 100%;
              width: 50%;
              border-radius: 999px;
              background: linear-gradient(90deg, var(--primary), var(--primary-2));
            }
            .bar.ok{ background: linear-gradient(90deg, #16a34a, #86efac); }
            .bar.warn{ background: linear-gradient(90deg, #f59e0b, #fde68a); }
            .bar.crit{ background: linear-gradient(90deg, #ef4444, #fecaca); }

            .charts{
              display:grid;
              grid-template-columns: 1fr 1fr;
              gap: 12px;
              margin-top: 12px;
            }
            .chart-card{
              background: rgba(255,255,255,.75);
              border: 1px solid var(--border);
              border-radius: 16px;
              padding: 12px;
              box-shadow: 0 10px 20px rgba(15,23,42,.04);
              min-height: 240px;
              display:flex;
              flex-direction:column;
              gap: 10px;
            }
            .chart-card h3{
              margin:0;
              font-size: 13px;
              color: #0b1220;
              letter-spacing: -0.01em;
              display:flex;
              align-items:center;
              justify-content:space-between;
              gap: 10px;
            }
            .chart-card h3 span{
              font-weight: 500;
              color: var(--muted);
              font-size: 12px;
            }
            .poa-dashboard canvas{ width:100% !important; height: 180px !important; }

            @media (max-width: 1100px){
              .wrap{ width: 90%; }
              .kpis{ grid-template-columns: repeat(2, minmax(0, 1fr)); }
              .grid{ grid-template-columns: 1fr; }
            }
            @media (max-width: 900px){
              .wrap{
                width: 100%;
                padding: 14px 10px 22px;
              }
              .poa-dashboard{
                border-radius: 14px;
                padding: 10px;
              }
              .title h1{
                font-size: 16px;
              }
              .title p{
                font-size: 12px;
              }
              .panel{
                padding: 12px;
              }
            }
            @media (max-width: 560px){
              .kpis{ grid-template-columns: 1fr; }
              .charts{ grid-template-columns: 1fr; }
              .kpi .value{ font-size: 28px; }
              .btn{
                width: 100%;
                justify-content: flex-start;
                padding: 10px;
              }
              .actions{
                width: 100%;
              }
              .chart-card{
                min-height: 210px;
              }
              .poa-dashboard canvas{
                height: 165px !important;
              }
            }
        </style>

        <div class="wrap">
            <div class="topbar">
              <div class="title">
                <h1>Tablero POA / BSC</h1>
                <p>Seguimiento ejecutivo con metas, desviaciones y tendencias (estilo premium).</p>
              </div>
              <div class="actions">
                <div class="btn" title="Filtrar">
                  <span class="dot"></span>
                  <strong style="font-size:13px;">Filtros</strong>
                  <span style="color:var(--muted);font-size:12px;">(Mes / Área)</span>
                </div>
                <div class="btn" title="Exportar">
                  <span class="dot" style="background:#16a34a; box-shadow:0 0 0 6px rgba(22,163,74,.12);"></span>
                  <strong style="font-size:13px;">Exportar</strong>
                  <span style="color:var(--muted);font-size:12px;">PDF/Excel</span>
                </div>
              </div>
            </div>

            <section class="kpis">
              <article class="kpi">
                <div class="label">
                  <span>Cumplimiento global POA</span>
                  <span class="state ok"><i></i>En rango</span>
                </div>
                <div class="value">78%</div>
                <div class="sub">
                  <span class="pill">Meta: 85%</span>
                  <span class="hint">+2.1 pts vs mes anterior</span>
                </div>
              </article>

              <article class="kpi">
                <div class="label">
                  <span>Objetivos estratégicos en meta</span>
                  <span class="state ok"><i></i>Estable</span>
                </div>
                <div class="value">9 <span style="font-weight:600;color:var(--muted);font-size:18px;">/ 12</span></div>
                <div class="sub">
                  <span class="pill">Pendientes: 3</span>
                  <span class="hint">2 en riesgo (alerta)</span>
                </div>
              </article>

              <article class="kpi">
                <div class="label">
                  <span>Iniciativas activas</span>
                  <span class="state warn"><i></i>Alta carga</span>
                </div>
                <div class="value">24</div>
                <div class="sub">
                  <span class="pill">Capacidad: 20</span>
                  <span class="hint">Reasignar responsables</span>
                </div>
              </article>

              <article class="kpi">
                <div class="label">
                  <span>Desviaciones críticas</span>
                  <span class="state crit"><i></i>Prioridad</span>
                </div>
                <div class="value">3</div>
                <div class="sub">
                  <span class="pill">SLA: 7 días</span>
                  <span class="hint">2 sin plan de acción</span>
                </div>
              </article>
            </section>

            <section class="grid">
              <div class="panel">
                <div class="panel-header">
                  <div class="panel-title">
                    <h2>Perspectiva Financiera</h2>
                    <small>Resultados financieros, ejecución y disciplina presupuestaria</small>
                  </div>
                  <div class="meta-pill">Meta 85%</div>
                </div>

                <div class="rows">
                  <div class="row">
                    <div class="row-top">
                      <div class="row-label">Ejecución presupuestaria</div>
                      <div class="row-value">81%</div>
                    </div>
                    <div class="progress"><div class="bar ok" style="width:81%"></div></div>
                    <div class="hint">En rango; falta optimizar calendario de gasto.</div>
                  </div>

                  <div class="row">
                    <div class="row-top">
                      <div class="row-label">Reducción de costos operativos</div>
                      <div class="row-value">6.2%</div>
                    </div>
                    <div class="progress"><div class="bar warn" style="width:62%"></div></div>
                    <div class="hint">En avance; validar quick wins y renegociaciones.</div>
                  </div>

                  <div class="row">
                    <div class="row-top">
                      <div class="row-label">Proyectos dentro de presupuesto</div>
                      <div class="row-value">14 / 18</div>
                    </div>
                    <div class="progress"><div class="bar" style="width:78%"></div></div>
                    <div class="hint">4 con sobrecosto: revisar alcance y compras.</div>
                  </div>
                </div>

                <div class="charts">
                  <div class="chart-card">
                    <h3>Trend: Cumplimiento POA <span>ultimos 6 meses</span></h3>
                    <canvas id="chartCumplimiento"></canvas>
                  </div>
                  <div class="chart-card">
                    <h3>Distribucion de desviaciones <span>por severidad</span></h3>
                    <canvas id="chartDesviaciones"></canvas>
                  </div>
                </div>
              </div>

              <div class="panel">
                <div class="panel-header">
                  <div class="panel-title">
                    <h2>Clientes / Usuarios</h2>
                    <small>Calidad de servicio, satisfaccion y tiempos de atencion</small>
                  </div>
                  <div class="meta-pill">Meta 90%</div>
                </div>

                <div class="rows">
                  <div class="row">
                    <div class="row-top">
                      <div class="row-label">Satisfaccion general</div>
                      <div class="row-value">88%</div>
                    </div>
                    <div class="progress"><div class="bar ok" style="width:88%"></div></div>
                    <div class="hint">Muy cerca de meta; reforzar calidad y comunicacion.</div>
                  </div>

                  <div class="row">
                    <div class="row-top">
                      <div class="row-label">Tiempo de respuesta a solicitudes</div>
                      <div class="row-value">42h</div>
                    </div>
                    <div class="progress"><div class="bar warn" style="width:70%"></div></div>
                    <div class="hint">Meta sugerida: <= 36h. Ajustar colas y SLA por tipo.</div>
                  </div>

                  <div class="row">
                    <div class="row-top">
                      <div class="row-label">Servicios con nivel alto</div>
                      <div class="row-value">11 / 13</div>
                    </div>
                    <div class="progress"><div class="bar" style="width:85%"></div></div>
                    <div class="hint">2 servicios en medio: plan de mejora y auditoria.</div>
                  </div>
                </div>

                <div class="charts">
                  <div class="chart-card" style="grid-column: 1 / -1;">
                    <h3>Atencion: Volumen vs SLA <span>por semana</span></h3>
                    <canvas id="chartSLA"></canvas>
                  </div>
                </div>
              </div>

              <div class="panel">
                <div class="panel-header">
                  <div class="panel-title">
                    <h2>Procesos Internos</h2>
                    <small>Estandarizacion, hitos, control operativo</small>
                  </div>
                  <div class="meta-pill">Meta 80%</div>
                </div>

                <div class="rows">
                  <div class="row">
                    <div class="row-top">
                      <div class="row-label">Procesos criticos estandarizados</div>
                      <div class="row-value">73%</div>
                    </div>
                    <div class="progress"><div class="bar warn" style="width:73%"></div></div>
                    <div class="hint">Priorizar procesos de alto impacto y riesgos.</div>
                  </div>

                  <div class="row">
                    <div class="row-top">
                      <div class="row-label">Hitos del POA cumplidos en fecha</div>
                      <div class="row-value">31 / 40</div>
                    </div>
                    <div class="progress"><div class="bar" style="width:78%"></div></div>
                    <div class="hint">Reforzar seguimiento semanal y responsables.</div>
                  </div>
                </div>
              </div>

              <div class="panel">
                <div class="panel-header">
                  <div class="panel-title">
                    <h2>Aprendizaje y Crecimiento</h2>
                    <small>Capacitacion, competencias y cultura</small>
                  </div>
                  <div class="meta-pill">Meta 75%</div>
                </div>

                <div class="rows">
                  <div class="row">
                    <div class="row-top">
                      <div class="row-label">Capacitaciones ejecutadas</div>
                      <div class="row-value">18 / 22</div>
                    </div>
                    <div class="progress"><div class="bar ok" style="width:82%"></div></div>
                    <div class="hint">Buen avance; asegurar evidencia y evaluacion.</div>
                  </div>

                  <div class="row">
                    <div class="row-top">
                      <div class="row-label">Competencias criticas certificadas</div>
                      <div class="row-value">69%</div>
                    </div>
                    <div class="progress"><div class="bar warn" style="width:69%"></div></div>
                    <div class="hint">Definir ruta de certificacion por rol y prioridad.</div>
                  </div>
                </div>
              </div>
            </section>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
        <script>
            (function () {
                if (!window.Chart) return;
                const baseOpts = {
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    legend: { display: false },
                    tooltip: { mode: 'index', intersect: false }
                  },
                  interaction: { mode: 'index', intersect: false },
                  scales: {
                    x: { grid: { display: false }, ticks: { maxRotation: 0 } },
                    y: { grid: { color: 'rgba(148,163,184,.25)' }, ticks: { precision: 0 } }
                  }
                };

                if (document.getElementById('chartCumplimiento')) {
                    new Chart(document.getElementById('chartCumplimiento'), {
                      type: 'line',
                      data: {
                        labels: ['Ago','Sep','Oct','Nov','Dic','Ene'],
                        datasets: [{
                          label: 'Cumplimiento',
                          data: [70, 72, 74, 76, 77, 78],
                          borderWidth: 2,
                          tension: 0.35,
                          pointRadius: 3,
                          fill: true,
                          backgroundColor: 'rgba(37,99,235,.12)'
                        }]
                      },
                      options: {
                        ...baseOpts,
                        scales: {
                          ...baseOpts.scales,
                          y: { ...baseOpts.scales.y, min: 0, max: 100 }
                        }
                      }
                    });
                }

                if (document.getElementById('chartDesviaciones')) {
                    new Chart(document.getElementById('chartDesviaciones'), {
                      type: 'doughnut',
                      data: {
                        labels: ['Criticas','Advertencias','Menores'],
                        datasets: [{
                          data: [3, 6, 11],
                          borderWidth: 1
                        }]
                      },
                      options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: true, position: 'bottom' } },
                        cutout: '68%'
                      }
                    });
                }

                if (document.getElementById('chartSLA')) {
                    new Chart(document.getElementById('chartSLA'), {
                      type: 'bar',
                      data: {
                        labels: ['S1','S2','S3','S4','S5','S6'],
                        datasets: [
                          { label: 'Solicitudes', data: [120, 138, 110, 150, 162, 140], borderWidth: 1 },
                          { label: 'Fuera de SLA', data: [14, 18, 12, 22, 26, 19], borderWidth: 1 }
                        ]
                      },
                      options: {
                        ...baseOpts,
                        plugins: { legend: { display: true, position: 'bottom' } }
                      }
                    });
                }
            })();
        </script>
    </section>
""")


@app.post("/api/usuarios/registro-seguro")
def crear_usuario_seguro(request: Request, data: dict = Body(...)):
    require_admin_or_superadmin(request)
    nombre = (data.get("nombre") or "").strip()
    usuario_login = (data.get("usuario") or "").strip()
    correo = (data.get("correo") or "").strip()
    imagen = (data.get("imagen") or "").strip()
    password = data.get("contrasena") or ""
    rol_nombre = normalize_role_name(data.get("rol"))

    if not nombre or not usuario_login or not correo or not password:
        return JSONResponse(
            {"success": False, "error": "nombre, usuario, correo y contrasena son obligatorios"},
            status_code=400,
        )
    if len(password) < 8:
        return JSONResponse(
            {"success": False, "error": "La contraseña debe tener al menos 8 caracteres"},
            status_code=400,
        )

    db = SessionLocal()
    try:
        login_hash = _sensitive_lookup_hash(usuario_login)
        email_hash = _sensitive_lookup_hash(correo)
        exists_login = db.query(Usuario).filter(Usuario.usuario_hash == login_hash).first()
        if not exists_login:
            exists_login = db.query(Usuario).filter(Usuario.usuario == usuario_login).first()
        if exists_login:
            return JSONResponse({"success": False, "error": "El usuario ya existe"}, status_code=409)
        exists_email = db.query(Usuario).filter(Usuario.correo_hash == email_hash).first()
        if not exists_email:
            exists_email = db.query(Usuario).filter(Usuario.correo == correo).first()
        if exists_email:
            return JSONResponse({"success": False, "error": "El correo ya existe"}, status_code=409)

        rol_id = None
        if not rol_nombre:
            rol_nombre = "usuario"
        if not can_assign_role(request, rol_nombre):
            rol_nombre = "usuario"
        if rol_nombre:
            rol = db.query(Rol).filter(Rol.nombre == rol_nombre).first()
            if not rol:
                return JSONResponse({"success": False, "error": "Rol no encontrado"}, status_code=404)
            rol_id = rol.id

        nuevo = Usuario(
            nombre=nombre,
            usuario=_encrypt_sensitive(usuario_login),
            usuario_hash=login_hash,
            correo=_encrypt_sensitive(correo),
            correo_hash=email_hash,
            contrasena=hash_password(password),
            rol_id=rol_id,
            imagen=imagen or None,
            role=rol_nombre,
            is_active=True,
        )
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
        return JSONResponse(
            {
                "success": True,
                "data": {
                    "id": nuevo.id,
                    "nombre": nuevo.nombre,
                    "correo": correo,
                    "imagen": nuevo.imagen,
                    "rol_id": nuevo.rol_id,
                },
            }
        )
    finally:
        db.close()


@app.put("/api/usuarios/{user_id}")
def actualizar_usuario_seguro(request: Request, user_id: int, data: dict = Body(...)):
    require_admin_or_superadmin(request)
    nombre = (data.get("nombre") or "").strip()
    usuario_login = (data.get("usuario") or "").strip()
    correo = (data.get("correo") or "").strip()
    imagen = (data.get("imagen") or "").strip()
    password = data.get("contrasena") or ""
    rol_nombre = normalize_role_name(data.get("rol"))

    if not nombre or not usuario_login or not correo:
        return JSONResponse(
            {"success": False, "error": "nombre, usuario y correo son obligatorios"},
            status_code=400,
        )
    if password and len(password) < 8:
        return JSONResponse(
            {"success": False, "error": "La contraseña debe tener al menos 8 caracteres"},
            status_code=400,
        )

    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.id == user_id).first()
        if not user:
            return JSONResponse({"success": False, "error": "Usuario no encontrado"}, status_code=404)

        login_hash = _sensitive_lookup_hash(usuario_login)
        email_hash = _sensitive_lookup_hash(correo)
        exists_login = (
            db.query(Usuario)
            .filter(Usuario.id != user_id, Usuario.usuario_hash == login_hash)
            .first()
        )
        if exists_login:
            return JSONResponse({"success": False, "error": "El usuario ya existe"}, status_code=409)
        exists_email = (
            db.query(Usuario)
            .filter(Usuario.id != user_id, Usuario.correo_hash == email_hash)
            .first()
        )
        if exists_email:
            return JSONResponse({"success": False, "error": "El correo ya existe"}, status_code=409)

        if not rol_nombre:
            rol_nombre = "usuario"
        if not can_assign_role(request, rol_nombre):
            rol_nombre = "usuario"
        rol = db.query(Rol).filter(Rol.nombre == rol_nombre).first()
        if not rol:
            return JSONResponse({"success": False, "error": "Rol no encontrado"}, status_code=404)

        user.nombre = nombre
        user.usuario = _encrypt_sensitive(usuario_login)
        user.usuario_hash = login_hash
        user.correo = _encrypt_sensitive(correo)
        user.correo_hash = email_hash
        user.rol_id = rol.id
        user.role = rol_nombre
        user.imagen = imagen or None
        if password:
            user.contrasena = hash_password(password)
        db.add(user)
        db.commit()
        db.refresh(user)

        return JSONResponse(
            {
                "success": True,
                "data": {
                    "id": user.id,
                    "nombre": user.nombre,
                    "correo": _decrypt_sensitive(user.correo),
                    "usuario": _decrypt_sensitive(user.usuario),
                    "imagen": user.imagen,
                    "rol": rol_nombre,
                },
            }
        )
    finally:
        db.close()


@app.get("/api/roles-disponibles")
def listar_roles_disponibles(request: Request):
    require_admin_or_superadmin(request)
    allowed = set(get_visible_role_names(request))
    db = SessionLocal()
    try:
        roles = (
            db.query(Rol)
            .filter(Rol.nombre.in_(allowed))
            .order_by(Rol.id.asc())
            .all()
        )
        data = [
            {
                "id": role.id,
                "nombre": role.nombre,
                "descripcion": role.descripcion,
                "label": role.nombre.replace("_", " ").capitalize(),
            }
            for role in roles
        ]
        return JSONResponse({"success": True, "data": data})
    finally:
        db.close()


@app.get("/api/usuarios")
def listar_usuarios_sanitizados(request: Request):
    require_admin_or_superadmin(request)
    db = SessionLocal()
    try:
        roles = {r.id: r.nombre for r in db.query(Rol).all()}
        usuarios = db.query(Usuario).all()

        session_username = (getattr(request.state, "user_name", None) or "").strip()
        session_lookup_hash = _sensitive_lookup_hash(session_username) if session_username else ""
        session_user = None
        if session_username:
            session_user = (
                db.query(Usuario)
                .filter(
                    (Usuario.usuario_hash == session_lookup_hash)
                    | (func.lower(Usuario.usuario) == session_username.lower())
                )
                .first()
            )

        def resolved_role(u: Usuario) -> str:
            if u.rol_id and roles.get(u.rol_id):
                return normalize_role_name(roles.get(u.rol_id))
            return normalize_role_name(u.role)

        session_role_from_db = resolved_role(session_user) if session_user else ""
        session_is_superadmin = is_superadmin(request) or session_role_from_db == "superadministrador"

        data = [
            {
                "id": u.id,
                "nombre": u.nombre,
                "usuario": _decrypt_sensitive(u.usuario),
                "correo": _decrypt_sensitive(u.correo),
                "rol": resolved_role(u),
                "imagen": u.imagen,
                "departamento": u.departamento or "",
                "estado": "Activo" if bool(u.is_active) else "Observando",
            }
            for u in usuarios
            if not is_hidden_user(request, _decrypt_sensitive(u.usuario))
            and (session_is_superadmin or resolved_role(u) != "superadministrador")
        ]
        return JSONResponse({"success": True, "data": data})
    finally:
        db.close()

@app.get("/inicio", response_class=HTMLResponse)
def inicio_page(request: Request):
    perspective_defs = [
        {
            "key": "financiera",
            "title": "Financiera",
            "meaning": "Sostenibilidad y crecimiento",
            "keywords": ["financ", "presupuesto", "ingreso", "sostenib", "liquidez", "rentabil", "gasto", "cartera"],
        },
        {
            "key": "socios_clientes",
            "title": "Socios",
            "meaning": "Valor social y satisfacción",
            "keywords": ["socio", "cliente", "usuario", "satisf", "servicio", "experien", "cobertura", "valor social"],
        },
        {
            "key": "procesos_internos",
            "title": "Procesos",
            "meaning": "Eficiencia operativa",
            "keywords": ["proceso", "operativ", "eficien", "control", "cumpl", "calidad", "riesgo", "mejora"],
        },
        {
            "key": "aprendizaje_innovacion",
            "title": "Aprendizaje",
            "meaning": "Desarrollo institucional",
            "keywords": ["innov", "aprendiz", "talento", "digital", "capacit", "desarrollo", "cultura", "tecnolog"],
        },
    ]
    perspective_lookup = {item["key"]: item for item in perspective_defs}
    perspective_title_map = {item["key"]: item["title"] for item in perspective_defs}
    status_chip_map = {
        "No iniciada": ("gris", "No iniciado"),
        "En proceso": ("amarillo", "En proceso"),
        "En revisión": ("naranja", "En revisión"),
        "Terminada": ("verde", "Terminada"),
        "Atrasada": ("rojo", "Atrasada"),
    }

    def classify_perspective(text: str) -> str:
        blob = (text or "").lower()
        for item in perspective_defs:
            if any(token in blob for token in item["keywords"]):
                return item["key"]
        return "procesos_internos"

    def add_months(anchor: Date, delta: int) -> Date:
        idx = (anchor.month - 1) + delta
        year = anchor.year + (idx // 12)
        month = (idx % 12) + 1
        return datetime(year, month, 1).date()

    def month_end(month_start: Date) -> Date:
        return add_months(month_start, 1) - timedelta(days=1)

    metrics = {
        item["key"]: {"objectives": 0, "activities": 0, "progress_values": []}
        for item in perspective_defs
    }
    total_progress_values: List[int] = []
    total_objectives = 0
    total_activities = 0
    status_counts = {key: 0 for key in status_chip_map.keys()}
    risk_objective_rows: List[Dict[str, Any]] = []
    critical_activity_rows: List[Dict[str, Any]] = []
    objective_name_by_id: Dict[int, str] = {}
    objective_axis_name_by_id: Dict[int, str] = {}

    db = SessionLocal()
    try:
        axes = (
            db.query(StrategicAxisConfig)
            .filter(StrategicAxisConfig.is_active == True)
            .all()
        )
        axis_by_id = {int(axis.id): axis for axis in axes}
        objectives = (
            db.query(StrategicObjectiveConfig)
            .filter(StrategicObjectiveConfig.is_active == True)
            .all()
        )
        objective_ids = [int(obj.id) for obj in objectives]
        activities = (
            db.query(POAActivity)
            .filter(POAActivity.objective_id.in_(objective_ids))
            .all()
            if objective_ids else []
        )
        activity_ids = [int(activity.id) for activity in activities]
        subactivities = (
            db.query(POASubactivity)
            .filter(POASubactivity.activity_id.in_(activity_ids))
            .all()
            if activity_ids else []
        )
        sub_by_activity: Dict[int, List[POASubactivity]] = {}
        for sub in subactivities:
            sub_by_activity.setdefault(int(sub.activity_id), []).append(sub)

        now = datetime.utcnow().date()
        activity_progress_by_id: Dict[int, int] = {}
        activity_status_by_id: Dict[int, str] = {}
        activity_progress_by_objective: Dict[int, List[int]] = {}

        for activity in activities:
            subs = sub_by_activity.get(int(activity.id), [])
            status = _activity_status(activity, now)
            if subs:
                done_subs = sum(1 for sub in subs if sub.fecha_final and sub.fecha_final <= now)
                progress = int(round((done_subs / len(subs)) * 100))
            else:
                progress = 100 if status == "Terminada" else 0
            activity_status_by_id[int(activity.id)] = status
            activity_progress_by_id[int(activity.id)] = progress
            status_counts[status] = status_counts.get(status, 0) + 1
            activity_progress_by_objective.setdefault(int(activity.objective_id), []).append(progress)

        for objective in objectives:
            axis = axis_by_id.get(int(objective.eje_id))
            axis_name = (axis.nombre if axis else "").strip() or "Sin eje"
            objective_name_by_id[int(objective.id)] = (objective.nombre or "").strip() or "Sin nombre"
            objective_axis_name_by_id[int(objective.id)] = axis_name
            blob = " ".join(
                [
                    str(objective.nombre or ""),
                    str(getattr(objective, "hito", "") or ""),
                    str(objective.descripcion or ""),
                    str(axis_name),
                ]
            )
            perspective_key = classify_perspective(blob)
            progress_list = activity_progress_by_objective.get(int(objective.id), [])
            objective_progress = int(round(sum(progress_list) / len(progress_list))) if progress_list else 0

            metrics[perspective_key]["objectives"] += 1
            metrics[perspective_key]["activities"] += len(progress_list)
            metrics[perspective_key]["progress_values"].append(objective_progress)

            total_objectives += 1
            total_activities += len(progress_list)
            total_progress_values.append(objective_progress)

            due_days = 9999
            if objective.fecha_final:
                due_days = (objective.fecha_final - now).days
            if objective.fecha_final and objective.fecha_final < now and objective_progress < 100:
                objective_status = "rojo"
                objective_status_label = "Atrasado"
                risk_score = 100 + (100 - objective_progress)
            elif objective_progress < 60 and due_days <= 45:
                objective_status = "amarillo"
                objective_status_label = "En riesgo"
                risk_score = 60 + (60 - objective_progress)
            elif objective_progress < 30:
                objective_status = "amarillo"
                objective_status_label = "En riesgo"
                risk_score = 50 + (30 - objective_progress)
            else:
                objective_status = "verde"
                objective_status_label = "Controlado"
                risk_score = 0
            if risk_score > 0:
                risk_objective_rows.append(
                    {
                        "id": int(objective.id),
                        "nombre": objective_name_by_id[int(objective.id)],
                        "eje": axis_name,
                        "perspectiva": perspective_title_map.get(perspective_key, "Procesos"),
                        "lider": (objective.lider or "").strip() or ((axis.lider_departamento or "").strip() if axis else "") or "Sin líder",
                        "avance": objective_progress,
                        "status": objective_status,
                        "status_label": objective_status_label,
                        "fecha_fin": objective.fecha_final.isoformat() if objective.fecha_final else "Sin fecha",
                        "score": risk_score,
                    }
                )

        for activity in activities:
            status_name = activity_status_by_id.get(int(activity.id), "No iniciada")
            status_key, status_label = status_chip_map.get(status_name, ("gris", "No iniciado"))
            progress = activity_progress_by_id.get(int(activity.id), 0)
            due_days = 9999
            if activity.fecha_final:
                due_days = (activity.fecha_final - now).days

            score = 0
            if status_name == "Atrasada":
                score += 100
            elif status_name == "En revisión":
                score += 70
            elif status_name == "En proceso" and progress < 50 and due_days <= 30:
                score += 55
            elif status_name == "No iniciada" and due_days <= 15:
                score += 40
            score += max(0, 20 - min(20, progress // 5))
            if score > 0:
                start_label = activity.fecha_inicial.isoformat() if activity.fecha_inicial else "Sin inicio"
                end_label = activity.fecha_final.isoformat() if activity.fecha_final else "Sin fin"
                critical_activity_rows.append(
                    {
                        "id": int(activity.id),
                        "nombre": (activity.nombre or "").strip() or "Actividad sin nombre",
                        "periodo": f"{start_label} - {end_label}",
                        "objetivo": objective_name_by_id.get(int(activity.objective_id), "Sin objetivo"),
                        "responsable": (activity.responsable or "").strip() or "Sin responsable",
                        "avance": progress,
                        "entregables": 1 if (activity.entregable or "").strip() else 0,
                        "status": status_key,
                        "status_label": status_label,
                        "score": score,
                    }
                )
    finally:
        db.close()

    total_progress = int(round(sum(total_progress_values) / len(total_progress_values))) if total_progress_values else 0
    terminadas = status_counts.get("Terminada", 0)
    completion_ratio = int(round((terminadas / total_activities) * 100)) if total_activities else 0
    riesgo_count = (
        status_counts.get("Atrasada", 0)
        + status_counts.get("En revisión", 0)
        + status_counts.get("En proceso", 0)
    )

    presupuesto_rows = 0
    presupuesto_total = 0.0
    presupuesto_por_rubro: Dict[str, float] = {}
    presupuesto_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "presupuesto.txt")
    if os.path.exists(presupuesto_path):
        try:
            with open(presupuesto_path, "r", encoding="utf-8") as fh:
                for raw in fh:
                    line = (raw or "").strip()
                    if not line:
                        continue
                    parts = [chunk.strip() for chunk in line.split("\t")]
                    if len(parts) < 3:
                        continue
                    code = parts[0]
                    amount_raw = parts[2].replace(",", "").strip()
                    try:
                        amount = float(amount_raw)
                    except (TypeError, ValueError):
                        continue
                    presupuesto_rows += 1
                    presupuesto_total += amount
                    if not code:
                        continue
                    rubro = code.split("-")[0].strip() or "ND"
                    presupuesto_por_rubro[rubro] = float(presupuesto_por_rubro.get(rubro, 0.0)) + amount
        except OSError:
            presupuesto_rows = 0
            presupuesto_total = 0.0
            presupuesto_por_rubro = {}

    presupuesto_ejercido = presupuesto_total * (completion_ratio / 100.0)
    pres_ejecutado_pct = int(round((presupuesto_ejercido / presupuesto_total) * 100)) if presupuesto_total > 0 else 0

    proyectando_filled = 0
    proyectando_total = 0
    try:
        from fastapi_modulo.modulos.proyectando.data_store import load_datos_preliminares_store

        prelim_data = load_datos_preliminares_store()
        if isinstance(prelim_data, dict):
            projected_values = [str(value or "").strip() for value in prelim_data.values()]
            proyectando_total = len(projected_values)
            proyectando_filled = len([value for value in projected_values if value])
    except Exception:
        proyectando_filled = 0
        proyectando_total = 0

    objective_rows_html = []
    for row in sorted(risk_objective_rows, key=lambda item: item["score"], reverse=True)[:8]:
        objective_rows_html.append(
            f"""
            <tr>
              <td class="bscA__mono"><strong>{escape(row['nombre'])}</strong><div class="bscA__muted">{escape(row['eje'])}</div></td>
              <td><span class="bscA__pill">{escape(row['perspectiva'])}</span></td>
              <td>{escape(row['lider'])}</td>
              <td class="bscA__num">
                <div class="bscA__miniProgress"><div class="bscA__miniFill" style="width:{row['avance']}%"></div></div>
                <span>{row['avance']}%</span>
              </td>
              <td><span class="bscA__status" data-status="{escape(row['status'])}">{escape(row['status_label'])}</span></td>
              <td class="bscA__mono">{escape(row['fecha_fin'])}</td>
            </tr>
            """
        )
    if not objective_rows_html:
        objective_rows_html.append(
            '<tr><td colspan="6" class="bscA__empty">Sin objetivos en riesgo en este momento.</td></tr>'
        )

    activity_rows_html = []
    for row in sorted(critical_activity_rows, key=lambda item: item["score"], reverse=True)[:10]:
        activity_rows_html.append(
            f"""
            <tr>
              <td><strong>{escape(row['nombre'])}</strong><div class="bscA__muted">{escape(row['periodo'])}</div></td>
              <td class="bscA__muted">{escape(row['objetivo'])}</td>
              <td>{escape(row['responsable'])}</td>
              <td class="bscA__num">
                <div class="bscA__miniProgress"><div class="bscA__miniFill" style="width:{row['avance']}%"></div></div>
                <span>{row['avance']}%</span>
              </td>
              <td class="bscA__num">{row['entregables']}</td>
              <td><span class="bscA__status" data-status="{escape(row['status'])}">{escape(row['status_label'])}</span></td>
            </tr>
            """
        )
    if not activity_rows_html:
        activity_rows_html.append(
            '<tr><td colspan="6" class="bscA__empty">Sin actividades críticas en este momento.</td></tr>'
        )

    now = datetime.utcnow().date()
    month_anchor = now.replace(day=1)
    month_names = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    trend_labels: List[str] = []
    trend_expected: List[int] = []
    trend_real: List[int] = []

    if total_activities > 0:
        db = SessionLocal()
        try:
            objective_ids = [
                int(item.id)
                for item in db.query(StrategicObjectiveConfig)
                .filter(StrategicObjectiveConfig.is_active == True)
                .all()
            ]
            activities = (
                db.query(POAActivity)
                .filter(POAActivity.objective_id.in_(objective_ids))
                .all()
                if objective_ids
                else []
            )
            for offset in range(-11, 1):
                ref_start = add_months(month_anchor, offset)
                ref_end = month_end(ref_start)
                trend_labels.append(f"{month_names[ref_start.month - 1]}-{str(ref_start.year)[-2:]}")
                expected_due = sum(1 for activity in activities if activity.fecha_final and activity.fecha_final <= ref_end)
                real_done = sum(
                    1
                    for activity in activities
                    if activity.fecha_final
                    and activity.fecha_final <= ref_end
                    and _activity_status(activity, now) == "Terminada"
                )
                trend_expected.append(int(round((expected_due / len(activities)) * 100)) if activities else 0)
                trend_real.append(int(round((real_done / len(activities)) * 100)) if activities else 0)
        finally:
            db.close()
    else:
        for offset in range(-11, 1):
            ref_start = add_months(month_anchor, offset)
            trend_labels.append(f"{month_names[ref_start.month - 1]}-{str(ref_start.year)[-2:]}")
            trend_expected.append(0)
            trend_real.append(0)

    perspective_progress = []
    perspective_objectives = []
    for item in perspective_defs:
        data = metrics[item["key"]]
        avg_progress = int(round(sum(data["progress_values"]) / len(data["progress_values"]))) if data["progress_values"] else 0
        perspective_progress.append(avg_progress)
        perspective_objectives.append(int(data["objectives"]))

    donut_labels = ["No iniciado", "En proceso", "En revisión", "Terminada", "Atrasada"]
    donut_values = [
        status_counts.get("No iniciada", 0),
        status_counts.get("En proceso", 0),
        status_counts.get("En revisión", 0),
        status_counts.get("Terminada", 0),
        status_counts.get("Atrasada", 0),
    ]

    top_budget = sorted(presupuesto_por_rubro.items(), key=lambda item: item[1], reverse=True)[:6]
    budget_labels = [f"Rubro {item[0]}" for item in top_budget]
    budget_aprobado = [int(round(item[1])) for item in top_budget]
    budget_ejercido = [int(round(item[1] * (pres_ejecutado_pct / 100.0))) for item in top_budget]

    charts_payload = {
        "trend": {"labels": trend_labels, "real": trend_real, "expected": trend_expected},
        "perspectives": {
            "labels": [item["title"] for item in perspective_defs],
            "avance": perspective_progress,
            "meta": [85, 85, 85, 85],
            "objetivos": perspective_objectives,
        },
        "status": {"labels": donut_labels, "values": donut_values},
        "budget": {"labels": budget_labels, "aprobado": budget_aprobado, "ejercido": budget_ejercido},
    }
    charts_payload_json = json.dumps(charts_payload, ensure_ascii=False).replace("</", "<\\/")
    year_value = now.year

    content = f"""
    <section class="bscA">
      <style>
        .bscA {{
          width: 100%;
          padding: 32px;
          background: #f6f8fb;
          color: #0f172a;
          font-family: "Nunito Sans", "Inter", system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
        }}
        .bscA * {{ box-sizing: border-box; }}
        .bscA__header {{
          display: flex;
          justify-content: space-between;
          align-items: flex-end;
          gap: 16px;
        }}
        .bscA__header h1 {{
          font-size: 30px;
          font-weight: 600;
          color: #0f172a;
          margin: 0;
        }}
        .bscA__titleRow {{
          display: flex;
          align-items: center;
          gap: 16px;
        }}
        .bscA__titleIconWrap {{
          width: 68px;
          height: 68px;
          border-radius: 18px;
          border: 2px solid #b8c8c4;
          background: #dbe5e1;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.65);
          flex: 0 0 68px;
        }}
        .bscA__titleIconWrap img {{
          width: 36px;
          height: 36px;
          object-fit: contain;
          display: block;
          opacity: 0.95;
        }}
        .bscA__header p {{
          margin: 8px 0 0;
          color: #64748b;
        }}
        .bscA__filters {{
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
        }}
        .bscA__chip {{
          background: #ffffff;
          border: 1px solid #e5e7eb;
          padding: 10px 12px;
          border-radius: 999px;
          color: #475569;
          box-shadow: 0 6px 18px rgba(15,23,42,.06);
        }}
        .bscA__kpis {{
          margin-top: 22px;
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 16px;
        }}
        .bscA__kpi {{
          background: #fff;
          border: 1px solid #eef2f7;
          border-radius: 16px;
          padding: 18px;
          box-shadow: 0 10px 25px rgba(15,23,42,.06);
          transition: .2s;
        }}
        .bscA__kpi:hover {{ transform: translateY(-3px); }}
        .bscA__kpi span {{
          color: #64748b;
          font-size: 13px;
        }}
        .bscA__kpi h2 {{
          margin: 8px 0 2px;
          font-size: 32px;
          color: #0f172a;
        }}
        .bscA__kpi small {{ color: #94a3b8; }}
        .bscA__kpi--highlight {{
          background: linear-gradient(135deg, #1e40af, #2563eb);
          border: none;
        }}
        .bscA__kpi--highlight span,
        .bscA__kpi--highlight h2,
        .bscA__kpi--highlight small {{ color: #fff; }}
        .bscA__grid {{
          margin-top: 18px;
          display: grid;
          grid-template-columns: repeat(12, minmax(0, 1fr));
          gap: 16px;
        }}
        .bscA__card {{
          grid-column: span 6;
          background: #fff;
          border: 1px solid #eef2f7;
          border-radius: 18px;
          box-shadow: 0 12px 28px rgba(15,23,42,.06);
          padding: 18px;
          min-height: 280px;
        }}
        .bscA__card--wide {{ grid-column: span 12; }}
        .bscA__cardHeader {{
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 12px;
          margin-bottom: 12px;
        }}
        .bscA__cardHeader h3 {{
          margin: 0;
          font-size: 16px;
          font-weight: 600;
          color: #0f172a;
        }}
        .bscA__cardHeader p {{
          margin: 6px 0 0;
          color: #64748b;
          font-size: 13px;
        }}
        .bscA__badge {{
          background: #f1f5f9;
          border: 1px solid #e2e8f0;
          padding: 8px 10px;
          border-radius: 999px;
          color: #475569;
          font-size: 12px;
        }}
        .bscA__btn {{
          background: #0f172a;
          color: #fff;
          border: none;
          padding: 10px 12px;
          border-radius: 12px;
          cursor: pointer;
        }}
        .bscA__btn--ghost {{
          background: #fff;
          color: #0f172a;
          border: 1px solid #e5e7eb;
        }}
        .bscA__chart {{ height: 220px; }}
        .bscA__chart--sm {{ height: 210px; }}
        .bscA__tableWrap {{
          margin-top: 8px;
          overflow: auto;
          border-radius: 14px;
          border: 1px solid #eef2f7;
        }}
        .bscA__table {{
          width: 100%;
          border-collapse: separate;
          border-spacing: 0;
          background: #fff;
          min-width: 690px;
        }}
        .bscA__table th {{
          position: sticky;
          z-index: 1;
          top: 0;
          background: #f8fafc;
          color: #475569;
          text-align: left;
          font-size: 12px;
          font-weight: 600;
          padding: 12px 14px;
          border-bottom: 1px solid #eef2f7;
          white-space: nowrap;
        }}
        .bscA__table td {{
          padding: 12px 14px;
          border-bottom: 1px solid #f1f5f9;
          color: #0f172a;
          font-size: 13px;
          vertical-align: middle;
        }}
        .bscA__table tr:last-child td {{ border-bottom: none; }}
        .bscA__muted {{
          color: #64748b;
          font-size: 12px;
          margin-top: 4px;
        }}
        .bscA__mono {{ font-variant-numeric: tabular-nums; min-width: 210px; }}
        .bscA__num {{ white-space: nowrap; }}
        .bscA__pill {{
          display: inline-flex;
          padding: 6px 10px;
          border-radius: 999px;
          background: #f1f5f9;
          border: 1px solid #e2e8f0;
          color: #334155;
          font-size: 12px;
        }}
        .bscA__status {{
          display: inline-flex;
          padding: 6px 10px;
          border-radius: 999px;
          font-size: 12px;
          border: 1px solid #e2e8f0;
          background: #f8fafc;
        }}
        .bscA__status[data-status="gris"] {{ background: #eef2f7; border-color: #cbd5e1; color: #475569; }}
        .bscA__status[data-status="amarillo"] {{ background: #fffbeb; border-color: #fde68a; color: #92400e; }}
        .bscA__status[data-status="naranja"] {{ background: #ffedd5; border-color: #fdba74; color: #9a3412; }}
        .bscA__status[data-status="verde"] {{ background: #ecfdf5; border-color: #bbf7d0; color: #166534; }}
        .bscA__status[data-status="rojo"] {{ background: #fff1f2; border-color: #fecdd3; color: #9f1239; }}
        .bscA__status[data-status="danger"] {{ background: #fff1f2; border-color: #fecdd3; color: #9f1239; }}
        .bscA__status[data-status="warning"] {{ background: #fffbeb; border-color: #fde68a; color: #92400e; }}
        .bscA__status[data-status="ok"] {{ background: #ecfdf5; border-color: #bbf7d0; color: #166534; }}
        .bscA__miniProgress {{
          width: 110px;
          height: 8px;
          background: #e2e8f0;
          border-radius: 99px;
          overflow: hidden;
          display: inline-block;
          vertical-align: middle;
          margin-right: 8px;
        }}
        .bscA__miniFill {{
          height: 100%;
          background: linear-gradient(90deg, #16a34a, #22c55e);
        }}
        .bscA__empty {{ color:#64748b; text-align:center; font-style:italic; }}
        @media (max-width: 1280px) {{
          .bscA__kpis {{ grid-template-columns:repeat(2, minmax(0,1fr)); }}
          .bscA__card {{ grid-column: span 12; }}
          .bscA__card--wide {{ grid-column: span 12; }}
        }}
        @media (max-width: 780px) {{
          .bscA__header {{ align-items:flex-start; flex-direction:column; }}
          .bscA__titleIconWrap {{
            width: 56px;
            height: 56px;
            border-radius: 14px;
            flex-basis: 56px;
          }}
          .bscA__titleIconWrap img {{
            width: 30px;
            height: 30px;
          }}
          .bscA__kpis {{ grid-template-columns: 1fr; }}
          .bscA__card, .bscA__card--wide {{ grid-column: span 12; }}
        }}
      </style>
      <div class="bscA__header">
        <div class="bscA__headerLeft">
          <div class="bscA__titleRow">
            <span class="bscA__titleIconWrap" aria-hidden="true">
              <img src="/templates/icon/tablero.svg" alt="">
            </span>
            <h1>Balanced Scorecard - Analítica</h1>
          </div>
          <p>Gráficas, tendencias y control ejecutivo (objetivos + POA + presupuesto + proyectando)</p>
        </div>
        <div class="bscA__filters">
          <div class="bscA__chip">Año: <strong>{year_value}</strong></div>
          <div class="bscA__chip">Periodo: <strong>Ene-Dic</strong></div>
          <div class="bscA__chip">Eje: <strong>Todos</strong></div>
        </div>
      </div>
      <div class="bscA__kpis">
        <div class="bscA__kpi">
          <span>Avance global</span>
          <h2>{total_progress}%</h2>
          <small>Meta: 85%</small>
        </div>
        <div class="bscA__kpi">
          <span>Objetivos</span>
          <h2>{total_objectives}</h2>
          <small>Activos</small>
        </div>
        <div class="bscA__kpi">
          <span>Actividades POA</span>
          <h2>{total_activities}</h2>
          <small>Totales</small>
        </div>
        <div class="bscA__kpi">
          <span>En riesgo</span>
          <h2>{riesgo_count}</h2>
          <small>Semáforo rojo/amarillo</small>
        </div>
        <div class="bscA__kpi bscA__kpi--highlight">
          <span>Ejecución presupuestal</span>
          <h2>{pres_ejecutado_pct}%</h2>
          <small>Ejercido / Aprobado</small>
        </div>
      </div>
      <div class="bscA__grid">
        <article class="bscA__card bscA__card--wide bscA__card--trend">
          <div class="bscA__cardHeader">
            <div>
              <h3>Tendencia estratégica (mensual)</h3>
              <p>Avance global vs avance esperado</p>
            </div>
            <div class="bscA__badge">Últimos 12 meses</div>
          </div>
          <div class="bscA__chart"><canvas id="bscATrend"></canvas></div>
        </article>
        <article class="bscA__card bscA__card--radar">
          <div class="bscA__cardHeader">
            <div>
              <h3>Balance por perspectiva</h3>
              <p>Radar del BSC (4 perspectivas)</p>
            </div>
          </div>
          <div class="bscA__chart bscA__chart--sm"><canvas id="bscARadar"></canvas></div>
        </article>
        <article class="bscA__card bscA__card--bars">
          <div class="bscA__cardHeader">
            <div>
              <h3>Avance por perspectiva</h3>
              <p>Comparativo y cumplimiento meta</p>
            </div>
          </div>
          <div class="bscA__chart bscA__chart--sm"><canvas id="bscABars"></canvas></div>
        </article>
        <article class="bscA__card bscA__card--donut">
          <div class="bscA__cardHeader">
            <div>
              <h3>Estados POA</h3>
              <p>No iniciado / En proceso / Revisión / Terminado / Atrasado</p>
            </div>
          </div>
          <div class="bscA__chart bscA__chart--sm"><canvas id="bscADonut"></canvas></div>
        </article>
        <article class="bscA__card bscA__card--budget">
          <div class="bscA__cardHeader">
            <div>
              <h3>Presupuesto por rubro</h3>
              <p>Aprobado vs ejercido (top rubros)</p>
            </div>
          </div>
          <div class="bscA__chart bscA__chart--sm"><canvas id="bscABudget"></canvas></div>
        </article>
        <article class="bscA__card bscA__card--wide bscA__card--risk">
          <div class="bscA__cardHeader">
            <div>
              <h3>Objetivos en riesgo</h3>
              <p>Prioridad directiva (impacto + atraso + avance)</p>
            </div>
            <button class="bscA__btn" type="button">Ver todos</button>
          </div>
          <div class="bscA__tableWrap">
            <table class="bscA__table">
              <thead>
                <tr>
                  <th>Objetivo</th>
                  <th>Perspectiva</th>
                  <th>Líder</th>
                  <th>Avance</th>
                  <th>Estado</th>
                  <th>Fecha fin</th>
                </tr>
              </thead>
              <tbody>
                {"".join(objective_rows_html)}
              </tbody>
            </table>
          </div>
        </article>
        <article class="bscA__card bscA__card--wide bscA__card--activities">
          <div class="bscA__cardHeader">
            <div>
              <h3>Actividades POA críticas</h3>
              <p>Top actividades por atraso o revisión pendiente</p>
            </div>
            <button class="bscA__btn bscA__btn--ghost" type="button">Exportar</button>
          </div>
          <div class="bscA__tableWrap">
            <table class="bscA__table">
              <thead>
                <tr>
                  <th>Actividad</th>
                  <th>Objetivo</th>
                  <th>Responsable</th>
                  <th>Avance</th>
                  <th>Entregables</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {"".join(activity_rows_html)}
              </tbody>
            </table>
          </div>
        </article>
      </div>
      <script type="application/json" id="bscAData">{charts_payload_json}</script>
      <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
      <script src="/static/js/bsc_dashboard_analytics.js"></script>
      <script>
        (function() {{
          if (!window.Chart || !window.BscDashboardAnalytics) return;
          const payloadNode = document.getElementById("bscAData");
          if (!payloadNode) return;
          const payload = JSON.parse(payloadNode.textContent || "{{}}");
          const dashboard = new window.BscDashboardAnalytics({{
            state: {{
              year: {year_value},
              periodLabel: "Ene-Dic",
              axisLabel: "Todos",
              kpis: {{
                global: {total_progress},
                metaGlobal: 85,
                objetivos: {total_objectives},
                actividades: {total_activities},
                riesgo: {riesgo_count},
                presEjecutado: {pres_ejecutado_pct}
              }}
            }},
            payload: payload,
            refs: {{
              trendCanvas: document.getElementById("bscATrend"),
              radarCanvas: document.getElementById("bscARadar"),
              barsCanvas: document.getElementById("bscABars"),
              donutCanvas: document.getElementById("bscADonut"),
              budgetCanvas: document.getElementById("bscABudget")
            }}
          }});
          dashboard.mount();
        }})();
      </script>
    </section>
    """
    return render_backend_page(
        request,
        title="Inicio",
        description="Balanced Scorecard",
        content=content,
        hide_floating_actions=True,
        show_page_header=True,
    )


@app.get("/perfil", response_class=HTMLResponse)
def perfil_page(request: Request):
    user_name = escape((getattr(request.state, "user_name", None) or "").strip() or "Usuario")
    user_role = escape((getattr(request.state, "user_role", None) or "").strip() or "usuario")
    user_tenant = escape((getattr(request.state, "tenant_id", None) or "").strip() or "default")
    content = f"""
    <section style="background:#fff;border:1px solid #dbe3ef;border-radius:14px;padding:16px;display:grid;gap:10px;max-width:760px;">
        <h3 style="margin:0;font-size:1.12rem;color:#0f172a;">Perfil</h3>
        <p style="margin:0;color:#475569;">Información de la sesión actual.</p>
        <article style="border:1px solid #e2e8f0;border-radius:10px;padding:10px;"><strong>Usuario</strong><div>{user_name}</div></article>
        <article style="border:1px solid #e2e8f0;border-radius:10px;padding:10px;"><strong>Rol</strong><div>{user_role}</div></article>
        <article style="border:1px solid #e2e8f0;border-radius:10px;padding:10px;"><strong>Tenant</strong><div>{user_tenant}</div></article>
    </section>
    """
    return render_backend_page(
        request,
        title="Perfil",
        description="Datos de perfil del usuario autenticado.",
        content=content,
        hide_floating_actions=True,
        show_page_header=True,
    )


@app.get("/control-seguimiento", response_class=HTMLResponse)
def control_seguimiento_page(request: Request):
    login_identity = _get_login_identity_context()
    logo_url = (login_identity.get("login_logo_url") or "/templates/icon/icon.png").strip() or "/templates/icon/icon.png"
    no_access_content = f"""
    <section style="width:100%;min-height:70vh;background:#ffffff;border-radius:16px;padding:24px;box-sizing:border-box;">
        <div style="display:flex;align-items:flex-start;justify-content:flex-start;">
            <img src="{escape(logo_url)}" alt="Logo empresa" style="max-width:180px;max-height:72px;object-fit:contain;">
        </div>
        <div style="min-height:56vh;display:flex;align-items:center;justify-content:center;text-align:center;color:#0f172a;font-size:28px;font-weight:700;padding:16px;">
            No tiene acceso, comuníquese con el administrador
        </div>
    </section>
    """
    return render_backend_page(
        request,
        title="Control y segumiento",
        description="",
        content=no_access_content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@app.get("/mi-tablero", response_class=HTMLResponse)
def mi_tablero_page(request: Request):
    no_access_content = """
    <section style="width:100%;min-height:70vh;background:#ffffff;border-radius:16px;padding:24px;box-sizing:border-box;">
        <div style="min-height:56vh;display:flex;align-items:center;justify-content:center;text-align:center;color:#0f172a;font-size:28px;font-weight:700;padding:16px;">
            No tiene acceso
        </div>
    </section>
    """
    return render_backend_page(
        request,
        title="Mi tablero",
        description="",
        content=no_access_content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@app.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse(url="/web/inicio", status_code=308)


@app.head("/", response_class=HTMLResponse)
def root_head():
    return RedirectResponse(url="/web/inicio", status_code=308)

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


@app.get("/ajustes/configuracion", response_class=HTMLResponse)
def ajustes_configuracion_page(request: Request):
    require_admin_or_superadmin(request)
    return _render_ajustes_configuracion_page(request)


@app.get("/api/ajustes/actualizacion")
def ajustes_actualizacion_estado(request: Request):
    require_admin_or_superadmin(request)
    context = _get_update_context(request)
    return {"success": True, **_snapshot_update_state(context)}


@app.post("/api/ajustes/actualizacion/verificar")
def ajustes_actualizacion_verificar(request: Request):
    require_admin_or_superadmin(request)
    context = _get_update_context(request)
    try:
        manifest = _fetch_update_manifest(context["manifest_url"])
        manifest_info = _validate_update_manifest(context, manifest)
        snapshot = {
            "checked_at": datetime.utcnow().isoformat(),
            "version": manifest_info["version"],
            "strategy": manifest_info["strategy"],
            "branch": manifest_info["branch"],
            "channel": context["channel"],
            "notes": manifest_info["notes"],
            "manifest_url": context["manifest_url"],
        }
        _write_json_file(context["files"]["manifest"], snapshot)
        _append_update_history(
            context["host"],
            {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "checked",
                "target_version": manifest_info["version"],
            },
        )
        context = _get_update_context(request)
        return {"success": True, **_snapshot_update_state(context, manifest_info)}
    except Exception as exc:
        _append_update_history(
            context["host"],
            {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "check_error",
                "target_version": "",
                "error": str(exc),
            },
        )
        return JSONResponse({"success": False, "error": str(exc)}, status_code=400)


@app.post("/api/ajustes/actualizacion/aplicar")
def ajustes_actualizacion_aplicar(request: Request):
    require_admin_or_superadmin(request)
    context = _get_update_context(request)
    try:
        manifest = _fetch_update_manifest(context["manifest_url"])
        manifest_info = _validate_update_manifest(context, manifest)
        if not manifest_info["update_available"]:
            return {"success": True, **_snapshot_update_state(context, manifest_info)}
        job_payload = _start_update_job(context, manifest_info)
        context = _get_update_context(request)
        state = _snapshot_update_state(context, manifest_info)
        state["last_job"] = job_payload
        return {"success": True, **state}
    except Exception as exc:
        _append_update_history(
            context["host"],
            {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "start_error",
                "target_version": "",
                "error": str(exc),
            },
        )
        return JSONResponse({"success": False, "error": str(exc)}, status_code=400)


@app.get("/empresa/base-datos", response_class=HTMLResponse)
def empresa_base_datos_page(request: Request):
    require_admin_or_superadmin(request)
    return _render_database_tools_page(request)


@app.get("/empresa/base-datos/exportar")
def empresa_base_datos_exportar(request: Request):
    require_admin_or_superadmin(request)
    db_info = _get_request_database_info(request)
    if db_info["engine"] != "sqlite" or not db_info["path"]:
        raise HTTPException(status_code=400, detail="Exportación por archivo disponible solo en SQLite")
    db_path = os.path.abspath(db_info["path"])
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="No se encontró el archivo de base de datos")
    filename = f"sipet_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.db"
    return FileResponse(db_path, media_type="application/octet-stream", filename=filename)


@app.post("/empresa/base-datos/importar", response_class=HTMLResponse)
async def empresa_base_datos_importar(request: Request, db_file: UploadFile = File(...)):
    require_admin_or_superadmin(request)
    db_info = _get_request_database_info(request)
    if db_info["engine"] != "sqlite" or not db_info["path"]:
        return RedirectResponse(
            url="/empresa/base-datos?status=error&msg=Importación%20por%20archivo%20solo%20disponible%20en%20SQLite",
            status_code=303,
        )
    db_path = os.path.abspath(db_info["path"])
    ext = os.path.splitext((db_file.filename or "").lower())[1]
    if ext not in {".db", ".sqlite", ".sqlite3"}:
        return RedirectResponse(
            url="/empresa/base-datos?status=error&msg=Archivo%20inválido.%20Usa%20.db%2C%20.sqlite%20o%20.sqlite3",
            status_code=303,
        )
    raw = await db_file.read()
    if not raw:
        return RedirectResponse(
            url="/empresa/base-datos?status=error&msg=Archivo%20vacío",
            status_code=303,
        )
    tmp_path = f"{db_path}.upload.tmp"
    backup_path = f"{db_path}.bak"
    try:
        with open(tmp_path, "wb") as fh:
            fh.write(raw)
        with sqlite3.connect(tmp_path) as conn:
            conn.execute("PRAGMA schema_version;").fetchone()

        core_db.dispose_engine_for_host(db_info["host"])

        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
        os.replace(tmp_path, db_path)
        return RedirectResponse(
            url="/empresa/base-datos?status=ok&msg=Base%20de%20datos%20importada%20correctamente",
            status_code=303,
        )
    except Exception as exc:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return RedirectResponse(
            url=f"/empresa/base-datos?status=error&msg={quote_plus(str(exc) or 'Error al importar base de datos')}",
            status_code=303,
        )


def _render_identidad_institucional_page(request: Request) -> HTMLResponse:
    identity = _load_login_identity()
    favicon_url = _build_login_asset_url(identity.get("favicon_filename"), DEFAULT_LOGIN_IDENTITY["favicon_filename"])
    safe_company_short_name = escape(identity.get("company_short_name", DEFAULT_LOGIN_IDENTITY["company_short_name"]))
    safe_login_message = escape(identity.get("login_message", DEFAULT_LOGIN_IDENTITY["login_message"]))
    current_menu_position = (identity.get("menu_position") or DEFAULT_LOGIN_IDENTITY["menu_position"]).strip().lower()
    if current_menu_position not in {"arriba", "abajo"}:
        current_menu_position = DEFAULT_LOGIN_IDENTITY["menu_position"]
    logo_url = _build_login_asset_url(identity.get("logo_filename"), DEFAULT_LOGIN_IDENTITY["logo_filename"])
    desktop_bg_url = _build_login_asset_url(identity.get("desktop_bg_filename"), DEFAULT_LOGIN_IDENTITY["desktop_bg_filename"])
    mobile_bg_url = _build_login_asset_url(identity.get("mobile_bg_filename"), DEFAULT_LOGIN_IDENTITY["mobile_bg_filename"])
    loaded_assets = sum(1 for value in [favicon_url, logo_url, desktop_bg_url, mobile_bg_url] if (value or "").strip())
    consistency = max(60, min(100, int(round((loaded_assets / 4) * 100)))) if loaded_assets else 60
    saved_flag = request.query_params.get("saved")
    saved_message = "<p class='id-flash'>Identidad institucional actualizada.</p>" if saved_flag == "1" else ""
    content = f"""
        <section class="id-page">
            <style>
                .id-page {{
                    --bg: #f6f8fc;
                    --surface: rgba(255,255,255,.88);
                    --text: #0f172a;
                    --muted: #64748b;
                    --border: rgba(148,163,184,.38);
                    --shadow: 0 18px 40px rgba(15,23,42,.08);
                    --shadow-soft: 0 10px 22px rgba(15,23,42,.06);
                    --radius: 18px;
                    --primary: #0f3d2e;
                    --primary-2: #1f6f52;
                    --ok: #16a34a;
                    --warn: #f59e0b;
                    --crit: #ef4444;
                    width: 100%;
                    font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
                    color: var(--text);
                    background:
                      radial-gradient(1200px 640px at 15% 0%, rgba(15,61,46,.10), transparent 58%),
                      radial-gradient(1000px 540px at 90% 6%, rgba(37,99,235,.10), transparent 55%),
                      var(--bg);
                    border-radius: 18px;
                }}
                .id-wrap {{ width: 100%; margin: 0 auto; padding: 18px 0 34px; }}
                .id-flash {{
                    margin: 0 0 12px;
                    padding: 10px 12px;
                    border-radius: 12px;
                    background: rgba(22,163,74,.10);
                    border: 1px solid rgba(22,163,74,.20);
                    color: #166534;
                    font-weight: 700;
                }}
                .id-btn {{
                    border-radius: 14px;
                    padding: 10px 14px;
                    font-weight: 800;
                    border: 1px solid var(--border);
                    background: rgba(255,255,255,.75);
                    cursor: pointer;
                    box-shadow: var(--shadow-soft);
                    transition: transform .15s ease, box-shadow .15s ease, background .15s ease;
                }}
                .id-btn:hover {{ transform: translateY(-1px); box-shadow: var(--shadow); background: rgba(255,255,255,.95); }}
                .id-btn--primary {{
                    background: linear-gradient(135deg, var(--primary), var(--primary-2));
                    color: #fff;
                    border-color: rgba(15,61,46,.35);
                }}
                .id-btn--primary2 {{
                    background: rgba(37,99,235,.12);
                    color: #1d4ed8;
                    border-color: rgba(37,99,235,.24);
                }}
                .id-btn--soft {{
                    background: rgba(15,61,46,.10);
                    border-color: rgba(15,61,46,.18);
                    color: #0b2a20;
                }}
                .id-btn--ghost2 {{
                    background: rgba(255,255,255,.85);
                    color: var(--text);
                    border-color: var(--border);
                }}
                .id-btn--ghost3 {{
                    background: rgba(255,255,255,.90);
                    color: var(--text);
                    border-color: var(--border);
                }}
                .id-btn--danger {{
                    border-color: rgba(239,68,68,.25);
                    color: #991b1b;
                    background: rgba(239,68,68,.08);
                }}
                .id-stats {{
                    display: grid;
                    grid-template-columns: repeat(4, minmax(0, 1fr));
                    gap: 12px;
                    margin-bottom: 14px;
                }}
                .id-stat {{
                    background: var(--surface);
                    border: 1px solid var(--border);
                    border-radius: var(--radius);
                    box-shadow: var(--shadow-soft);
                    padding: 14px;
                }}
                .id-stat__k {{ color: var(--muted); font-size: 12px; font-weight: 700; }}
                .id-stat__v {{ margin-top: 8px; font-size: 28px; font-weight: 900; letter-spacing: -0.02em; }}
                .id-stat__meta {{ margin-top: 8px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }}
                .id-chip {{
                    font-size: 12px;
                    padding: 6px 10px;
                    border-radius: 999px;
                    background: rgba(15,23,42,.05);
                    border: 1px solid rgba(15,23,42,.08);
                    color: rgba(15,23,42,.72);
                }}
                .id-chip--ok {{ background: rgba(22,163,74,.10); border-color: rgba(22,163,74,.20); color: #166534; }}
                .id-bar {{
                    height: 10px;
                    flex: 1 1 auto;
                    min-width: 110px;
                    border-radius: 999px;
                    background: rgba(148,163,184,.25);
                    border: 1px solid rgba(148,163,184,.25);
                    overflow: hidden;
                }}
                .id-bar__fill {{
                    height: 100%;
                    border-radius: 999px;
                    background: linear-gradient(90deg, rgba(15,61,46,1), rgba(31,111,82,1));
                }}
                .id-grid {{ display: grid; grid-template-columns: 1.1fr .9fr; gap: 14px; align-items: start; margin-bottom: 14px; }}
                .id-card {{
                    background: var(--surface);
                    border: 1px solid var(--border);
                    border-radius: 22px;
                    box-shadow: var(--shadow-soft);
                    overflow: hidden;
                }}
                .id-card--pad {{ padding: 16px; }}
                .id-card__head {{
                    display: flex;
                    align-items: flex-start;
                    justify-content: space-between;
                    gap: 12px;
                    margin-bottom: 14px;
                }}
                .id-card__head h2 {{ margin: 0; font-size: 20px; letter-spacing: -0.02em; }}
                .id-card__head p {{ margin: 6px 0 0; color: var(--muted); font-size: 13px; }}
                .id-card__tools {{ display: flex; gap: 10px; align-items: center; }}
                .id-pill {{
                    font-size: 12px;
                    padding: 6px 10px;
                    border-radius: 999px;
                    background: rgba(255,255,255,.70);
                    border: 1px solid var(--border);
                    color: rgba(15,23,42,.72);
                }}
                .id-pill--soft {{
                    background: rgba(15,61,46,.10);
                    border-color: rgba(15,61,46,.18);
                    color: #0b2a20;
                }}
                .id-iconbtn {{
                    width: 38px;
                    height: 38px;
                    border-radius: 14px;
                    border: 1px solid var(--border);
                    background: rgba(255,255,255,.75);
                    box-shadow: var(--shadow-soft);
                    cursor: pointer;
                }}
                .id-form {{ display: flex; flex-direction: column; gap: 12px; }}
                .id-field {{ display: flex; flex-direction: column; gap: 8px; }}
                .id-field label {{ font-size: 13px; font-weight: 700; color: #334155; }}
                .id-field input,
                .id-field textarea {{
                    border: 1px solid var(--border);
                    border-radius: 14px;
                    padding: 12px;
                    background: rgba(255,255,255,.85);
                    box-shadow: 0 10px 20px rgba(15,23,42,.04);
                }}
                .id-field textarea {{ min-height: 90px; resize: vertical; }}
                .id-help {{ color: var(--muted); font-size: 12px; }}
                .id-actions {{ display: flex; gap: 10px; justify-content: flex-end; margin-top: 4px; }}
                .id-tips {{ display: flex; flex-direction: column; gap: 10px; }}
                .id-tip {{
                    display: flex;
                    gap: 10px;
                    align-items: flex-start;
                    background: rgba(255,255,255,.82);
                    border: 1px solid rgba(148,163,184,.30);
                    border-radius: 14px;
                    padding: 10px;
                }}
                .id-tip__icon {{ font-size: 18px; }}
                .id-tip__text strong {{ display: block; font-size: 13px; }}
                .id-tip__text p {{ margin: 4px 0 0; color: var(--muted); font-size: 12px; line-height: 1.35; }}
                .id-divider {{ height: 1px; background: rgba(148,163,184,.25); margin: 4px 0; }}
                .id-cta {{ display: flex; justify-content: space-between; align-items: center; gap: 10px; }}
                .id-cta p {{ margin: 4px 0 0; color: var(--muted); font-size: 12px; }}
                .id-assets__grid {{ display: flex; flex-direction: column; gap: 10px; }}
                .id-asset {{
                    display: grid;
                    grid-template-columns: 240px minmax(0, 1fr) auto;
                    gap: 14px;
                    align-items: center;
                    background: rgba(255,255,255,.86);
                    border: 1px solid rgba(148,163,184,.30);
                    border-radius: 16px;
                    padding: 12px;
                }}
                .id-asset__label {{ display: flex; gap: 8px; align-items: center; }}
                .id-asset__meta {{ margin-top: 4px; font-size: 12px; color: var(--muted); }}
                .id-dot {{ width: 10px; height: 10px; border-radius: 999px; display: inline-block; }}
                .id-dot--ok {{ background: var(--ok); box-shadow: 0 0 0 6px rgba(22,163,74,.10); }}
                .id-asset__preview {{
                    border: 1px solid rgba(148,163,184,.30);
                    background: rgba(248,250,252,.95);
                    border-radius: 12px;
                    overflow: hidden;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                .id-asset__preview img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
                .id-asset__preview--square {{ width: 96px; height: 96px; }}
                .id-asset__preview--square img {{ object-fit: contain; padding: 8px; }}
                .id-asset__preview--logo {{ height: 120px; }}
                .id-asset__preview--logo img {{ object-fit: contain; padding: 10px; }}
                .id-asset__preview--wide {{ height: 140px; }}
                .id-asset__actions {{ display: flex; flex-direction: column; gap: 8px; min-width: 116px; }}
                @media (max-width: 1200px) {{
                    .id-stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
                    .id-grid {{ grid-template-columns: 1fr; }}
                    .id-asset {{ grid-template-columns: 1fr; }}
                    .id-asset__actions {{ flex-direction: row; }}
                }}
                @media (max-width: 640px) {{
                    .id-stats {{ grid-template-columns: 1fr; }}
                    .id-actions {{ justify-content: flex-start; flex-wrap: wrap; }}
                    .id-cta {{ flex-direction: column; align-items: flex-start; }}
                }}
            </style>
            <div class="id-wrap">
                <form id="identity-form" method="post" action="/identidad-institucional" enctype="multipart/form-data">
                    <input type="hidden" id="remove_favicon" name="remove_favicon" value="0">
                    <input type="hidden" id="remove_logo" name="remove_logo" value="0">
                    <input type="hidden" id="remove_desktop" name="remove_desktop" value="0">
                    <input type="hidden" id="remove_mobile" name="remove_mobile" value="0">
                    <div style="display:none;">
                        <input type="file" id="favicon" name="favicon" accept="image/*">
                        <input type="file" id="logo_empresa" name="logo_empresa" accept="image/*">
                        <input type="file" id="fondo_escritorio" name="fondo_escritorio" accept="image/*">
                        <input type="file" id="fondo_movil" name="fondo_movil" accept="image/*">
                    </div>
                    {saved_message}
                    <section class="id-card id-card--pad" style="margin-bottom:14px;">
                        <div class="flex flex-wrap items-center justify-between gap-4">
                            <div>
                                <h2 style="margin:0;font-size:18px;">Estilo visual del sistema</h2>
                                <p style="margin:6px 0 0;color:var(--muted);font-size:13px;">Elige entre estilo original o estilo moderno para sidebar y contenedor principal.</p>
                            </div>
                            <label class="label cursor-pointer gap-3">
                                <span id="identity-sidebar-style-label" class="font-semibold text-sm" style="color:#0f3d2e;">Original</span>
                                <input id="identity-sidebar-style-switch" type="checkbox" class="toggle toggle-success">
                            </label>
                        </div>
                    </section>
                    <script>
                        (function () {{
                            var apply = function (variant) {{
                                var modern = variant === 'modern';
                                document.documentElement.classList.toggle('ui-sidebar-modern', modern);
                                var sw = document.getElementById('identity-sidebar-style-switch');
                                var label = document.getElementById('identity-sidebar-style-label');
                                if (sw) sw.checked = modern;
                                if (label) label.textContent = modern ? 'Moderno' : 'Original';
                            }};
                            var bind = function () {{
                                var sw = document.getElementById('identity-sidebar-style-switch');
                                if (!sw) return;
                                try {{
                                    apply(window.localStorage.getItem('sipet_sidebar_style_variant') || 'original');
                                }} catch (e) {{
                                    apply('original');
                                }}
                                sw.addEventListener('change', function () {{
                                    var variant = sw.checked ? 'modern' : 'original';
                                    apply(variant);
                                    try {{ window.localStorage.setItem('sipet_sidebar_style_variant', variant); }} catch (e) {{}}
                                }});
                            }};
                            if (document.readyState === 'loading') {{
                                document.addEventListener('DOMContentLoaded', bind);
                            }} else {{
                                bind();
                            }}
                        }})();
                    </script>
                    <section class="id-card id-card--pad" style="margin-bottom:14px;">
                        <div class="flex flex-wrap items-center justify-between gap-4">
                            <div>
                                <h2 style="margin:0;font-size:18px;">Posición del menu</h2>
                                <p style="margin:6px 0 0;color:var(--muted);font-size:13px;">Arriba mantiene el menú actual. Abajo activa la barra móvil inferior en páginas públicas.</p>
                            </div>
                            <div class="flex items-center gap-4">
                                <label class="label cursor-pointer gap-2">
                                    <input type="radio" name="menu_position" value="arriba" {"checked" if current_menu_position == "arriba" else ""}>
                                    <span class="font-semibold text-sm" style="color:#0f3d2e;">Arriba</span>
                                </label>
                                <label class="label cursor-pointer gap-2">
                                    <input type="radio" name="menu_position" value="abajo" {"checked" if current_menu_position == "abajo" else ""}>
                                    <span class="font-semibold text-sm" style="color:#0f3d2e;">Abajo</span>
                                </label>
                            </div>
                        </div>
                    </section>
                    <section class="id-stats">
                        <article class="id-stat">
                            <div class="id-stat__k">Nombre corto</div>
                            <div class="id-stat__v">{safe_company_short_name}</div>
                            <div class="id-stat__meta"><span class="id-chip">Activo</span></div>
                        </article>
                        <article class="id-stat">
                            <div class="id-stat__k">Recursos cargados</div>
                            <div class="id-stat__v">{loaded_assets}</div>
                            <div class="id-stat__meta"><span class="id-chip id-chip--ok">Completo</span></div>
                        </article>
                        <article class="id-stat">
                            <div class="id-stat__k">Formato recomendado</div>
                            <div class="id-stat__v">SVG/PNG</div>
                            <div class="id-stat__meta"><span class="id-chip">Alta nitidez</span></div>
                        </article>
                        <article class="id-stat">
                            <div class="id-stat__k">Consistencia visual</div>
                            <div class="id-stat__v">{consistency}%</div>
                            <div class="id-stat__meta">
                                <div class="id-bar"><div class="id-bar__fill" style="width:{consistency}%"></div></div>
                                <span class="id-chip id-chip--ok">Optimo</span>
                            </div>
                        </article>
                    </section>
                    <section class="id-grid">
                        <section class="id-card id-card--pad">
                            <header class="id-card__head">
                                <div>
                                    <h2>Datos institucionales</h2>
                                    <p>Estos datos se muestran en login y en elementos de marca del sistema.</p>
                                </div>
                                <div class="id-card__tools">
                                    <span class="id-pill id-pill--soft">Configuracion</span>
                                    <button class="id-iconbtn" type="button" title="Ayuda">?</button>
                                </div>
                            </header>
                            <div class="id-form">
                                <div class="id-field">
                                    <label for="company_short_name">Nombre corto de la empresa</label>
                                    <input class="campo campo-personalizado" id="company_short_name" name="company_short_name" type="text" value="{safe_company_short_name}" placeholder="Ej. AVAN">
                                    <div class="id-help">Se usa en titulos, encabezados y login. Recomendado: 3-18 caracteres.</div>
                                </div>
                                <div class="id-field">
                                    <label for="login_message">Mensaje para pantalla de login</label>
                                    <textarea class="campo campo-personalizado" id="login_message" name="login_message" placeholder="Ej. Incrementando el nivel de eficiencia">{safe_login_message}</textarea>
                                    <div class="id-help">Sugerencia: frase corta y orientada a valor.</div>
                                </div>
                                <div class="id-actions">
                                    <button class="id-btn id-btn--primary" type="submit" form="identity-form">Guardar</button>
                                    <button class="id-btn id-btn--soft" type="reset">Restablecer</button>
                                </div>
                            </div>
                        </section>
                        <aside class="id-card id-card--pad">
                            <header class="id-card__head">
                                <div>
                                    <h2>Recomendaciones</h2>
                                    <p>Buenas practicas para mantener calidad visual en web y movil.</p>
                                </div>
                                <div class="id-card__tools"><span class="id-pill">Guia rapida</span></div>
                            </header>
                            <div class="id-tips">
                                <div class="id-tip"><div class="id-tip__icon">L</div><div class="id-tip__text"><strong>Logo</strong><p>Preferible SVG; si usas PNG que sea transparente y amplio.</p></div></div>
                                <div class="id-tip"><div class="id-tip__icon">F</div><div class="id-tip__text"><strong>Favicon</strong><p>Usa 32x32 y 64x64 con buena legibilidad.</p></div></div>
                                <div class="id-tip"><div class="id-tip__icon">M</div><div class="id-tip__text"><strong>Fondo movil</strong><p>Formato vertical con punto focal centrado.</p></div></div>
                                <div class="id-tip"><div class="id-tip__icon">E</div><div class="id-tip__text"><strong>Fondo escritorio</strong><p>Recomendado 1920x1080 y buen contraste.</p></div></div>
                                <div class="id-divider"></div>
                                <div class="id-cta">
                                    <div><strong>Vista previa</strong><p>Valida como se vera el login con los recursos actuales.</p></div>
                                    <button class="id-btn id-btn--ghost2" type="button">Abrir preview</button>
                                </div>
                            </div>
                        </aside>
                    </section>
                    <section class="id-card id-card--pad id-assets">
                        <header class="id-card__head">
                            <div>
                                <h2>Recursos visuales</h2>
                                <p>Administra favicon, logo y fondos para web y movil.</p>
                            </div>
                            <div class="id-card__tools">
                                <span class="id-pill">4 recursos</span>
                            </div>
                        </header>
                        <div class="id-assets__grid">
                            <article class="id-asset">
                                <div class="id-asset__left">
                                    <div class="id-asset__label"><span class="id-dot id-dot--ok"></span><strong>Favicon</strong></div>
                                    <div class="id-asset__meta">Recomendado: 32x32 / 64x64 - PNG/ICO</div>
                                </div>
                                <div class="id-asset__preview id-asset__preview--square">
                                    <img src="{favicon_url}" alt="Favicon">
                                </div>
                                <div class="id-asset__actions identity-asset-actions">
                                    <button class="id-btn id-btn--ghost3 identity-asset-edit" data-target-input="favicon" type="button">Editar</button>
                                    <button class="id-btn id-btn--danger identity-asset-delete" data-target-remove="remove_favicon" type="button">Eliminar</button>
                                </div>
                            </article>
                            <article class="id-asset">
                                <div class="id-asset__left">
                                    <div class="id-asset__label"><span class="id-dot id-dot--ok"></span><strong>Logo de la empresa</strong></div>
                                    <div class="id-asset__meta">Preferible SVG - alternativa PNG transparente</div>
                                </div>
                                <div class="id-asset__preview id-asset__preview--logo">
                                    <img src="{logo_url}" alt="Logo">
                                </div>
                                <div class="id-asset__actions identity-asset-actions">
                                    <button class="id-btn id-btn--ghost3 identity-asset-edit" data-target-input="logo_empresa" type="button">Editar</button>
                                    <button class="id-btn id-btn--danger identity-asset-delete" data-target-remove="remove_logo" type="button">Eliminar</button>
                                </div>
                            </article>
                            <article class="id-asset">
                                <div class="id-asset__left">
                                    <div class="id-asset__label"><span class="id-dot id-dot--ok"></span><strong>Fondo de escritorio</strong></div>
                                    <div class="id-asset__meta">Recomendado: 1920x1080 - JPG/PNG</div>
                                </div>
                                <div class="id-asset__preview id-asset__preview--wide">
                                    <img src="{desktop_bg_url}" alt="Fondo de escritorio">
                                </div>
                                <div class="id-asset__actions identity-asset-actions">
                                    <button class="id-btn id-btn--ghost3 identity-asset-edit" data-target-input="fondo_escritorio" type="button">Editar</button>
                                    <button class="id-btn id-btn--danger identity-asset-delete" data-target-remove="remove_desktop" type="button">Eliminar</button>
                                </div>
                            </article>
                            <article class="id-asset">
                                <div class="id-asset__left">
                                    <div class="id-asset__label"><span class="id-dot id-dot--ok"></span><strong>Fondo movil</strong></div>
                                    <div class="id-asset__meta">Recomendado: 1080x1920 - JPG/PNG</div>
                                </div>
                                <div class="id-asset__preview id-asset__preview--wide">
                                    <img src="{mobile_bg_url}" alt="Fondo movil">
                                </div>
                                <div class="id-asset__actions identity-asset-actions">
                                    <button class="id-btn id-btn--ghost3 identity-asset-edit" data-target-input="fondo_movil" type="button">Editar</button>
                                    <button class="id-btn id-btn--danger identity-asset-delete" data-target-remove="remove_mobile" type="button">Eliminar</button>
                                </div>
                            </article>
                        </div>
                    </section>
                </form>
            </div>
        </section>
    """
    return render_backend_page(
        request,
        title="Identidad institucional",
        description="Configuración de identidad para la pantalla de login.",
        content=content,
        hide_floating_actions=True,
        show_page_header=True,
    )


@app.get("/identidad-institucional", response_class=HTMLResponse)
def identidad_institucional_page(request: Request):
    require_admin_or_superadmin(request)
    return _render_identidad_institucional_page(request)


@app.get("/identidad-institucional/", response_class=HTMLResponse)
def identidad_institucional_page_slash(request: Request):
    require_admin_or_superadmin(request)
    return RedirectResponse(url="/identidad-institucional", status_code=307)


@app.post("/identidad-institucional", response_class=HTMLResponse)
async def identidad_institucional_save(
    request: Request,
    company_short_name: str = Form(""),
    login_message: str = Form(""),
    menu_position: str = Form("arriba"),
    favicon: Optional[UploadFile] = File(None),
    logo_empresa: Optional[UploadFile] = File(None),
    fondo_escritorio: Optional[UploadFile] = File(None),
    fondo_movil: Optional[UploadFile] = File(None),
    remove_favicon: str = Form("0"),
    remove_logo: str = Form("0"),
    remove_desktop: str = Form("0"),
    remove_mobile: str = Form("0"),
):
    require_admin_or_superadmin(request)
    current = _load_login_identity()
    current["company_short_name"] = company_short_name.strip() or DEFAULT_LOGIN_IDENTITY["company_short_name"]
    current["login_message"] = login_message.strip() or DEFAULT_LOGIN_IDENTITY["login_message"]
    current["menu_position"] = "abajo" if str(menu_position).strip().lower() == "abajo" else "arriba"

    if str(remove_favicon).strip() == "1":
        _remove_login_image_if_custom(current.get("favicon_filename"))
        current["favicon_filename"] = DEFAULT_LOGIN_IDENTITY["favicon_filename"]
    if str(remove_logo).strip() == "1":
        _remove_login_image_if_custom(current.get("logo_filename"))
        current["logo_filename"] = DEFAULT_LOGIN_IDENTITY["logo_filename"]
    if str(remove_desktop).strip() == "1":
        _remove_login_image_if_custom(current.get("desktop_bg_filename"))
        current["desktop_bg_filename"] = DEFAULT_LOGIN_IDENTITY["desktop_bg_filename"]
    if str(remove_mobile).strip() == "1":
        _remove_login_image_if_custom(current.get("mobile_bg_filename"))
        current["mobile_bg_filename"] = DEFAULT_LOGIN_IDENTITY["mobile_bg_filename"]

    new_favicon = await _store_login_image(favicon, "favicon") if favicon else None
    if new_favicon:
        _remove_login_image_if_custom(current.get("favicon_filename"))
        current["favicon_filename"] = new_favicon

    new_logo = await _store_login_image(logo_empresa, "logo_empresa") if logo_empresa else None
    if new_logo:
        _remove_login_image_if_custom(current.get("logo_filename"))
        current["logo_filename"] = new_logo

    new_desktop = await _store_login_image(fondo_escritorio, "fondo_escritorio") if fondo_escritorio else None
    if new_desktop:
        _remove_login_image_if_custom(current.get("desktop_bg_filename"))
        current["desktop_bg_filename"] = new_desktop

    new_mobile = await _store_login_image(fondo_movil, "fondo_movil") if fondo_movil else None
    if new_mobile:
        _remove_login_image_if_custom(current.get("mobile_bg_filename"))
        current["mobile_bg_filename"] = new_mobile

    _save_login_identity(current)
    try:
        from fastapi_modulo.modulos.frontend import frontend as _frontend_module
        _frontend_module._page_cache.clear()
    except Exception:
        pass
    return RedirectResponse(url="/identidad-institucional?saved=1", status_code=303)

# Placeholder para templates
# En el futuro, importar y usar templates para todas las respuestas

if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8005")))

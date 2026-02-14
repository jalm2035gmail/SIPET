
import json
import base64
import hashlib
import hmac
import smtplib
import csv
import sqlite3
from io import BytesIO, StringIO
from datetime import datetime
from html import escape
import os
import re
import secrets
from textwrap import dedent
from email.message import EmailMessage
from urllib.parse import urlparse

from typing import Any, Dict, List, Optional, Set
from fastapi import FastAPI, Request, Body, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
import httpx
from openpyxl import Workbook
from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import create_engine, Column, String, Integer, JSON, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

HIDDEN_SYSTEM_USERS = {"0konomiyaki"}
IDENTIDAD_LOGIN_CONFIG_PATH = "fastapi_modulo/identidad_login.json"
IDENTIDAD_LOGIN_IMAGE_DIR = "fastapi_modulo/templates/imagenes"
DEFAULT_LOGIN_IDENTITY = {
    "favicon_filename": "icon.png",
    "logo_filename": "icon.png",
    "desktop_bg_filename": "fondo.jpg",
    "mobile_bg_filename": "movil.jpg",
    "company_short_name": "AVAN",
    "login_message": "Incrementando el nivel de eficiencia",
}
PLANTILLAS_STORE_PATH = "fastapi_modulo/plantillas_store.json"
SYSTEM_REPORT_HEADER_TEMPLATE_ID = "system-report-header"
AUTH_COOKIE_NAME = "auth_session"
AUTH_COOKIE_SECRET = os.environ.get("AUTH_COOKIE_SECRET", "sipet-dev-auth-secret")
NON_DATA_FIELD_TYPES = {"header", "paragraph", "html", "divider", "pagebreak"}


ROLE_ALIASES = {
    "super_admin": "superadministrador",
    "superadministrador": "superadministrador",
    "admin": "administrador",
    "administrador": "administrador",
    "strategic_manager": "departamento",
    "department_manager": "departamento",
    "departamento": "departamento",
    "team_leader": "usuario",
    "collaborator": "usuario",
    "viewer": "usuario",
    "usuario": "usuario",
}


def normalize_role_name(role_name: Optional[str]) -> str:
    normalized = (role_name or "").strip().lower()
    if not normalized:
        return "usuario"
    return ROLE_ALIASES.get(normalized, normalized)


def get_current_role(request: Request) -> str:
    role = getattr(request.state, "user_role", None)
    if role is None:
        role = request.cookies.get("user_role") or os.environ.get("DEFAULT_USER_ROLE") or ""
    return normalize_role_name(role)


def is_superadmin(request: Request) -> bool:
    return get_current_role(request) == "superadministrador"


def is_admin(request: Request) -> bool:
    return get_current_role(request) == "administrador"


def is_admin_or_superadmin(request: Request) -> bool:
    return is_superadmin(request) or is_admin(request)


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


def _ensure_login_identity_paths() -> None:
    os.makedirs(IDENTIDAD_LOGIN_IMAGE_DIR, exist_ok=True)


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
    data = await upload.read()
    if not data:
        return None
    _ensure_login_identity_paths()
    ext = _get_upload_ext(upload)
    new_filename = f"{prefix}_{secrets.token_hex(6)}{ext}"
    image_path = os.path.join(IDENTIDAD_LOGIN_IMAGE_DIR, new_filename)
    with open(image_path, "wb") as fh:
        fh.write(data)
    return new_filename


def _build_login_asset_url(filename: Optional[str], default_filename: str) -> str:
    selected = filename or default_filename
    selected_path = os.path.join(IDENTIDAD_LOGIN_IMAGE_DIR, selected)
    if not os.path.exists(selected_path):
        selected = default_filename
        selected_path = os.path.join(IDENTIDAD_LOGIN_IMAGE_DIR, selected)
    version = int(os.path.getmtime(selected_path)) if os.path.exists(selected_path) else 0
    return f"/templates/imagenes/{selected}?v={version}"


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


def _build_default_report_header_template() -> Dict[str, str]:
    now_iso = datetime.utcnow().isoformat()
    return {
        "id": SYSTEM_REPORT_HEADER_TEMPLATE_ID,
        "nombre": "Encabezado",
        "html": (
            "<header class='reporte-encabezado'>"
            "<div class='reporte-encabezado__marca'>{{ empresa }}</div>"
            "<div class='reporte-encabezado__meta'>"
            "<h1>{{ titulo_reporte }}</h1>"
            "<p>{{ subtitulo_reporte }}</p>"
            "</div>"
            "<div class='reporte-encabezado__fecha'>Fecha: {{ fecha_reporte }}</div>"
            "</header>"
        ),
        "css": (
            ".reporte-encabezado { display:flex; align-items:center; justify-content:space-between; gap:16px; "
            "padding:16px 20px; border:1px solid #cbd5e1; border-radius:12px; background:#f8fafc; font-family:Arial,sans-serif; } "
            ".reporte-encabezado__marca { font-weight:800; color:#0f172a; font-size:1.1rem; letter-spacing:.04em; } "
            ".reporte-encabezado__meta h1 { margin:0; font-size:1.05rem; color:#0f172a; } "
            ".reporte-encabezado__meta p { margin:4px 0 0; color:#475569; font-size:.88rem; } "
            ".reporte-encabezado__fecha { color:#334155; font-size:.84rem; white-space:nowrap; }"
        ),
        "created_at": now_iso,
        "updated_at": now_iso,
    }


def _with_system_templates(templates: List[Dict[str, str]]) -> List[Dict[str, str]]:
    default_header = _build_default_report_header_template()
    has_header = any(
        str(tpl.get("id", "")).strip() == SYSTEM_REPORT_HEADER_TEMPLATE_ID
        or str(tpl.get("nombre", "")).strip().lower() == "encabezado"
        for tpl in templates
    )
    if has_header:
        return templates
    return [default_header, *templates]


def _get_report_header_template() -> Dict[str, str]:
    templates = _load_plantillas_store()
    for tpl in templates:
        if str(tpl.get("id", "")).strip() == SYSTEM_REPORT_HEADER_TEMPLATE_ID:
            return tpl
    for tpl in templates:
        if str(tpl.get("nombre", "")).strip().lower() == "encabezado":
            return tpl
    return _build_default_report_header_template()


def _apply_template_context(content: str, context: Dict[str, str]) -> str:
    rendered = content or ""
    for key, value in context.items():
        rendered = rendered.replace(f"{{{{ {key} }}}}", value)
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def _build_report_export_context() -> Dict[str, str]:
    identidad = _load_login_identity()
    return {
        "empresa": identidad.get("company_short_name") or "SIPET",
        "titulo_reporte": "Reporte consolidado",
        "subtitulo_reporte": "Avance, desempeno y seguimiento",
        "fecha_reporte": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def _build_report_export_rows() -> List[Dict[str, str]]:
    return [
        {
            "reporte": "Reporte ejecutivo",
            "descripcion": "Resumen de estado estrategico",
            "formato": "PDF / Excel",
        },
        {
            "reporte": "Reporte operativo",
            "descripcion": "Actividades, avances y cumplimiento",
            "formato": "PDF / Excel",
        },
        {
            "reporte": "Reporte KPI",
            "descripcion": "Indicadores, metas y variaciones",
            "formato": "PDF / Excel",
        },
    ]


def _build_report_export_html_document() -> str:
    template = _get_report_header_template()
    context = _build_report_export_context()
    header_html = _apply_template_context(template.get("html", ""), context)
    header_css = template.get("css", "")
    rows = _build_report_export_rows()
    rows_html = "".join(
        (
            "<tr>"
            f"<td>{escape(row['reporte'])}</td>"
            f"<td>{escape(row['descripcion'])}</td>"
            f"<td>{escape(row['formato'])}</td>"
            "</tr>"
        )
        for row in rows
    )
    return (
        "<!doctype html><html lang='es'><head><meta charset='utf-8'>"
        "<title>Reporte consolidado</title>"
        "<style>"
        f"{header_css}"
        "body{font-family:Arial,sans-serif;background:#fff;color:#0f172a;padding:24px;}"
        ".reporte-bloque{margin-top:18px;}"
        "table{width:100%;border-collapse:collapse;}"
        "th,td{border:1px solid #cbd5e1;padding:10px;text-align:left;font-size:14px;}"
        "th{background:#f1f5f9;}"
        "</style></head><body>"
        f"{header_html}"
        "<section class='reporte-bloque'>"
        "<h2>Detalle de reportes</h2>"
        "<table><thead><tr><th>Reporte</th><th>Descripcion</th><th>Formato</th></tr></thead>"
        f"<tbody>{rows_html}</tbody></table>"
        "</section></body></html>"
    )


def _save_plantillas_store(templates: List[Dict[str, str]]) -> None:
    os.makedirs(os.path.dirname(PLANTILLAS_STORE_PATH), exist_ok=True)
    with open(PLANTILLAS_STORE_PATH, "w", encoding="utf-8") as fh:
        json.dump(templates, fh, ensure_ascii=False, indent=2)


def build_view_buttons_html(view_buttons: Optional[List[Dict]]) -> str:
    if not view_buttons:
        return ""
    pieces = []
    for button in view_buttons:
        label = button.get("label", "").strip()
        if not label:
            continue
        icon = button.get("icon")
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
            icon_html = f'<img src="{icon}" alt="{label} icon">'
        pieces.append(f'<button class="{classes}" type="button"{attr_str}>{icon_html}<span>{label}</span></button>')
    return "".join(pieces)


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
):
    """
    Helper para renderizar una pantalla backend con panel flotante y botones de vistas.
    - view_buttons: lista de dicts {label, view?, url, icon}
    - floating_buttons: lista de dicts {label, onclick}
    """
    rendered_view_buttons = view_buttons_html or build_view_buttons_html(view_buttons)
    can_manage_personalization = is_superadmin(request)
    login_identity = _get_login_identity_context()
    context = {
        "request": request,
        "title": title,
        "subtitle": subtitle,
        "page_title": page_title or title,
        "page_description": page_description or description,
        "content": content,
        "view_buttons_html": rendered_view_buttons,
        "floating_buttons": floating_buttons,
        "hide_floating_actions": hide_floating_actions,
        "show_page_header": show_page_header,
        "colores": get_colores_context(),
        "can_manage_personalization": can_manage_personalization,
        "app_favicon_url": login_identity.get("login_favicon_url"),
    }
    return templates.TemplateResponse("base.html", context)

# Configuración SQLite (BD principal unificada)
PRIMARY_DB_PATH = "strategic_planning.db"
LEGACY_DB_PATH = "fastapi_modulo/colores.db"
DATABASE_URL = f"sqlite:///./{PRIMARY_DB_PATH}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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
    correo = Column("email", String, unique=True, index=True)
    celular = Column(String)
    contrasena = Column("password", String)
    departamento = Column(String)
    puesto = Column(String)
    jefe = Column(String)
    coach = Column(String)
    rol_id = Column(Integer)
    imagen = Column(String)
    role = Column(String)
    is_active = Column(Boolean, default=True)


class FormDefinition(Base):
    __tablename__ = "form_definitions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    description = Column(String)
    config = Column(JSON, default=dict)
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


DEFAULT_SYSTEM_ROLES = [
    ("superadministrador", "Acceso total a todo el módulo"),
    ("administrador", "Acceso a todo menos a Personalización"),
    ("departamento", "Acceso a su departamento"),
    ("usuario", "Acceso solo a sus datos"),
]


def ensure_default_roles() -> None:
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


def migrate_legacy_sqlite_data() -> None:
    if not os.path.exists(LEGACY_DB_PATH):
        return
    if os.path.abspath(LEGACY_DB_PATH) == os.path.abspath(PRIMARY_DB_PATH):
        return

    table_order = [
        "colores",
        "roles",
        "users",
        "usuarios",
        "form_definitions",
        "form_fields",
        "form_submissions",
    ]

    def quote_ident(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    with sqlite3.connect(PRIMARY_DB_PATH) as conn:
        conn.execute("ATTACH DATABASE ? AS legacy", (LEGACY_DB_PATH,))
        try:
            for table_name in table_order:
                legacy_exists = conn.execute(
                    "SELECT 1 FROM legacy.sqlite_master WHERE type='table' AND name=?",
                    (table_name,),
                ).fetchone()
                if not legacy_exists:
                    continue

                quoted_table = quote_ident(table_name)
                target_columns = [
                    row[1]
                    for row in conn.execute(f"PRAGMA table_info({quoted_table})").fetchall()
                ]
                legacy_columns = [
                    row[1]
                    for row in conn.execute(f"PRAGMA legacy.table_info({quoted_table})").fetchall()
                ]
                shared_columns = [col for col in target_columns if col in legacy_columns]
                if not shared_columns:
                    continue

                quoted_columns = ", ".join(quote_ident(col) for col in shared_columns)
                conn.execute(
                    f"INSERT OR IGNORE INTO {quoted_table} ({quoted_columns}) "
                    f"SELECT {quoted_columns} FROM legacy.{quoted_table}"
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            try:
                conn.execute("DETACH DATABASE legacy")
            except sqlite3.OperationalError:
                pass


def unify_users_table() -> None:
    """
    Unifica usuarios legacy (`usuarios`) dentro de la tabla canónica `users`.
    Mantiene compatibilidad agregando columnas opcionales usadas por el frontend.
    """
    required_columns = {
        "celular": "VARCHAR",
        "departamento": "VARCHAR",
        "puesto": "VARCHAR",
        "jefe": "VARCHAR",
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
                        password = COALESCE(NULLIF(?, ''), password),
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
migrate_legacy_sqlite_data()
unify_users_table()
ensure_default_roles()

app = FastAPI(title="Módulo de Planificación Estratégica y POA", docs_url="/docs", redoc_url="/redoc")
templates = Jinja2Templates(directory="fastapi_modulo/templates")
app.state.templates = templates
app.mount("/templates", StaticFiles(directory="fastapi_modulo/templates"), name="templates")

@app.get("/health")
def healthcheck():
    return {"status": "ok"}


def _not_found_context(request: Request, title: str = "Pagina no encontrada") -> Dict[str, str]:
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


@app.middleware("http")
async def enforce_backend_login(request: Request, call_next):
    path = request.url.path
    public_paths = {
        "/web",
        "/web/404",
        "/web/login",
        "/logout",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
    }
    if (
        request.method == "OPTIONS"
        or path in public_paths
        or path.startswith("/templates/")
        or path.startswith("/docs/")
        or path.startswith("/redoc/")
    ):
        return await call_next(request)

    session_token = request.cookies.get(AUTH_COOKIE_NAME, "")
    session_data = _read_session_cookie(session_token)
    if not session_data:
        if path.startswith("/api/") or path.startswith("/guardar-colores"):
            return JSONResponse({"success": False, "error": "No autenticado"}, status_code=401)
        return templates.TemplateResponse(
            "not_found.html",
            _not_found_context(request),
            status_code=404,
        )

    request.state.user_name = session_data["username"]
    request.state.user_role = session_data["role"]
    return await call_next(request)


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
            return hmac.compare_digest(password, stored)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        # Compatibilidad con usuarios legacy guardados en texto plano.
        return hmac.compare_digest(password, stored)


def is_hidden_user(request: Request, username: Optional[str]) -> bool:
    if is_superadmin(request):
        return False
    return (username or "").strip().lower() in {u.lower() for u in HIDDEN_SYSTEM_USERS}


def _build_session_cookie(username: str, role: str) -> str:
    payload_json = json.dumps(
        {"u": username.strip(), "r": role.strip().lower()},
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
    return {"username": username, "role": role}

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
@app.get("/web", response_class=HTMLResponse)
def web(request: Request):
    login_identity = _get_login_identity_context()
    return templates.TemplateResponse(
        "frontend/web.html",
        {
            "request": request,
            "title": "SIPET",
            "app_favicon_url": login_identity.get("login_favicon_url"),
            "company_logo_url": login_identity.get("login_logo_url"),
        },
    )


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
):
    login_identity = _get_login_identity_context()
    username = usuario.strip()
    password = contrasena or ""
    if not username or not password:
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
    try:
        user = db.query(Usuario).filter(Usuario.usuario == username).first()
        if not user or not verify_password(password, user.contrasena or ""):
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

        role_name = "usuario"
        if user.rol_id:
            role = db.query(Rol).filter(Rol.id == user.rol_id).first()
            if role and role.nombre:
                role_name = normalize_role_name(role.nombre)
        elif user.role:
            role_name = normalize_role_name(user.role)
    finally:
        db.close()

    response = RedirectResponse(url="/inicio", status_code=303)
    response.set_cookie(
        AUTH_COOKIE_NAME,
        _build_session_cookie(username, role_name),
        httponly=True,
        samesite="lax",
    )
    response.set_cookie("user_role", normalize_role_name(role_name), httponly=True, samesite="lax")
    response.set_cookie("user_name", username, httponly=True, samesite="lax")
    return response


@app.get("/logout")
@app.get("/logout/")
def logout():
    response = RedirectResponse(url="/web/login", status_code=303)
    response.delete_cookie(AUTH_COOKIE_NAME)
    response.delete_cookie("user_role")
    response.delete_cookie("user_name")
    return response


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
    is_active: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)
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
    description: Optional[str]
    config: Dict[str, Any]
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
            "description": form_definition.description,
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
) -> HTMLResponse:
    rendered_view_buttons = view_buttons_html or build_view_buttons_html(view_buttons)
    can_manage_personalization = is_superadmin(request)
    login_identity = _get_login_identity_context()
    context = {
        "request": request,
        "title": title,
        "content": content,
        "subtitle": subtitle,
        "page_title": title,
        "page_description": description,
        "hide_floating_actions": hide_floating_actions,
        "floating_actions_html": floating_actions_html,
        "floating_actions_screen": floating_actions_screen,
        "view_buttons_html": rendered_view_buttons,
        "show_page_header": show_page_header,
        "can_manage_personalization": can_manage_personalization,
        "app_favicon_url": login_identity.get("login_favicon_url"),
    }
    context.update({"colores": get_colores_context()})
    return templates.TemplateResponse("base.html", context)



# Almacenamiento simple en archivo para el contenido editable de Avance
AVANCE_CONTENT_FILE = "fastapi_modulo/avance_content.txt"
def get_avance_content():
    if os.path.exists(AVANCE_CONTENT_FILE):
        with open(AVANCE_CONTENT_FILE, "r", encoding="utf-8") as f:
            return f.read()
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




PERSONALIZACION_HTML = dedent("""
    <section class="personalization-panel" aria-labelledby="personalizacion-title">
        <div>
            <h2 id="personalizacion-title">Personalizar pantalla</h2>
            <p>Define los colores principales que se aplicarán en todo el sitio para mantener la identidad institucional.</p>
        </div>
        <div class="color-group">
            <h3>Navbar</h3>
            <div class="color-grid">
                <article class="color-option">
                    <label for="navbar-bg">Fondo</label>
                    <input type="color" id="navbar-bg" name="navbar-bg" value="#ffffff">
                    <div class="color-preview" id="navbar-bg-preview" style="background:#ffffff;"></div>
                </article>
                <article class="color-option">
                    <label for="navbar-text">Texto</label>
                    <input type="color" id="navbar-text" name="navbar-text" value="#0f172a">
                    <div class="color-preview" id="navbar-text-preview" style="background:#0f172a;"></div>
                </article>
            </div>
        </div>
        <div class="color-group">
            <h3>Sidebar</h3>
            <div class="color-grid">
                <article class="color-option">
                    <label for="sidebar-top">Color superior</label>
                    <input type="color" id="sidebar-top" name="sidebar-top" value="#1f2a3d">
                    <div class="color-preview" id="sidebar-top-preview" style="background:#1f2a3d;"></div>
                </article>
                <article class="color-option">
                    <label for="sidebar-bottom">Color inferior</label>
                    <input type="color" id="sidebar-bottom" name="sidebar-bottom" value="#0f172a">
                    <div class="color-preview" id="sidebar-bottom-preview" style="background:#0f172a;"></div>
                </article>
                <article class="color-option">
                    <label for="sidebar-text">Texto</label>
                    <input type="color" id="sidebar-text" name="sidebar-text" value="#ffffff">
                    <div class="color-preview" id="sidebar-text-preview" style="background:#ffffff;"></div>
                </article>
                <article class="color-option">
                    <label for="sidebar-icon">Iconos</label>
                    <input type="color" id="sidebar-icon" name="sidebar-icon" value="#f5f7fb">
                    <div class="color-preview" id="sidebar-icon-preview" style="background:#f5f7fb;"></div>
                </article>
                <article class="color-option">
                    <label for="sidebar-hover">Hover</label>
                    <input type="color" id="sidebar-hover" name="sidebar-hover" value="#2a3a52">
                    <div class="color-preview" id="sidebar-hover-preview" style="background:#2a3a52;"></div>
                </article>
                <article class="color-option">
                    <label for="field-color">Color del campo</label>
                    <input type="color" id="field-color" name="field-color" value="#e7d7da">
                    <div class="color-preview" id="field-color-preview" style="background:#e7d7da;"></div>
                </article>
            </div>
        </div>
        <div class="color-field-note">
            <p><strong>Clase disponible:</strong> usa <code>campo-personalizado</code> para aplicar el color de campo configurado por el usuario.</p>
        </div>
    </section>
""")

FODA_HTML = dedent("""
    <section class="foda-page" id="foda-builder">
        <article class="foda-input-card">
            <h2>Matriz FODA</h2>
            <p>Registra factores y clasifícalos como fortalezas, debilidades, oportunidades o amenazas.</p>
            <div class="foda-input-grid">
                <div class="form-field">
                    <label for="foda-description">Descripción</label>
                    <textarea id="foda-description" placeholder="Describe el factor"></textarea>
                </div>
                <div class="form-field">
                    <label for="foda-category">Categoría</label>
                    <select id="foda-category">
                        <option value="strengths">Fortalezas</option>
                        <option value="weaknesses">Debilidades</option>
                        <option value="opportunities">Oportunidades</option>
                        <option value="threats">Amenazas</option>
                    </select>
                </div>
                <div class="form-field">
                    <label for="foda-impact">Impacto</label>
                    <select id="foda-impact">
                        <option value="high">Alto</option>
                        <option value="medium">Medio</option>
                        <option value="low">Bajo</option>
                    </select>
                </div>
            </div>
            <div class="foda-input-actions">
                <button type="button" id="foda-add">Agregar factor</button>
            </div>
        </article>
        <section class="foda-matrix">
            <article class="foda-quadrant foda-strengths">
                <header>
                    <h3>Fortalezas</h3>
                    <span id="foda-count-strengths">0</span>
                </header>
                <ul id="foda-list-strengths"></ul>
            </article>
            <article class="foda-quadrant foda-weaknesses">
                <header>
                    <h3>Debilidades</h3>
                    <span id="foda-count-weaknesses">0</span>
                </header>
                <ul id="foda-list-weaknesses"></ul>
            </article>
            <article class="foda-quadrant foda-opportunities">
                <header>
                    <h3>Oportunidades</h3>
                    <span id="foda-count-opportunities">0</span>
                </header>
                <ul id="foda-list-opportunities"></ul>
            </article>
            <article class="foda-quadrant foda-threats">
                <header>
                    <h3>Amenazas</h3>
                    <span id="foda-count-threats">0</span>
                </header>
                <ul id="foda-list-threats"></ul>
            </article>
        </section>
    </section>
""")

PESTEL_HTML = dedent("""
    <section class="pestel-page" id="pestel-builder">
        <article class="pestel-input-card">
            <h2>Análisis PESTEL</h2>
            <p>Registra factores externos por dimensión: Política, Económica, Social, Tecnológica, Ecológica y Legal.</p>
            <div class="pestel-input-grid">
                <div class="form-field">
                    <label for="pestel-description">Factor</label>
                    <textarea id="pestel-description" placeholder="Describe el factor PESTEL"></textarea>
                </div>
                <div class="form-field">
                    <label for="pestel-factor">Dimensión</label>
                    <select id="pestel-factor">
                        <option value="political">Política</option>
                        <option value="economic">Económica</option>
                        <option value="social">Social</option>
                        <option value="technological">Tecnológica</option>
                        <option value="ecological">Ecológica</option>
                        <option value="legal">Legal</option>
                    </select>
                </div>
                <div class="form-field">
                    <label for="pestel-impact">Impacto</label>
                    <select id="pestel-impact">
                        <option value="high">Alto</option>
                        <option value="medium">Medio</option>
                        <option value="low">Bajo</option>
                    </select>
                </div>
            </div>
            <div class="pestel-input-actions">
                <button type="button" id="pestel-add">Agregar factor</button>
            </div>
        </article>
        <section class="pestel-board">
            <article class="pestel-column">
                <header><h3>Política</h3><span id="pestel-count-political">0</span></header>
                <ul id="pestel-list-political"></ul>
            </article>
            <article class="pestel-column">
                <header><h3>Económica</h3><span id="pestel-count-economic">0</span></header>
                <ul id="pestel-list-economic"></ul>
            </article>
            <article class="pestel-column">
                <header><h3>Social</h3><span id="pestel-count-social">0</span></header>
                <ul id="pestel-list-social"></ul>
            </article>
            <article class="pestel-column">
                <header><h3>Tecnológica</h3><span id="pestel-count-technological">0</span></header>
                <ul id="pestel-list-technological"></ul>
            </article>
            <article class="pestel-column">
                <header><h3>Ecológica</h3><span id="pestel-count-ecological">0</span></header>
                <ul id="pestel-list-ecological"></ul>
            </article>
            <article class="pestel-column">
                <header><h3>Legal</h3><span id="pestel-count-legal">0</span></header>
                <ul id="pestel-list-legal"></ul>
            </article>
        </section>
    </section>
""")

PORTER_HTML = dedent("""
    <section class="porter-page" id="porter-builder">
        <article class="porter-input-card">
            <h2>5 Fuerzas de Porter</h2>
            <p>Analiza la intensidad competitiva del entorno y su impacto en la estrategia.</p>
            <div class="porter-input-grid">
                <div class="form-field">
                    <label for="porter-description">Factor</label>
                    <textarea id="porter-description" placeholder="Describe el factor de la fuerza"></textarea>
                </div>
                <div class="form-field">
                    <label for="porter-force">Fuerza</label>
                    <select id="porter-force">
                        <option value="competitors">Rivalidad entre competidores</option>
                        <option value="entrants">Amenaza de nuevos entrantes</option>
                        <option value="suppliers">Poder de negociación de proveedores</option>
                        <option value="buyers">Poder de negociación de compradores</option>
                        <option value="substitutes">Amenaza de productos sustitutos</option>
                    </select>
                </div>
                <div class="form-field">
                    <label for="porter-impact">Impacto</label>
                    <select id="porter-impact">
                        <option value="high">Alto</option>
                        <option value="medium">Medio</option>
                        <option value="low">Bajo</option>
                    </select>
                </div>
            </div>
            <div class="porter-input-actions">
                <button type="button" id="porter-add">Agregar factor</button>
            </div>
        </article>
        <section class="porter-board">
            <article class="porter-column">
                <header><h3>Competidores</h3><span id="porter-count-competitors">0</span></header>
                <ul id="porter-list-competitors"></ul>
            </article>
            <article class="porter-column">
                <header><h3>Nuevos entrantes</h3><span id="porter-count-entrants">0</span></header>
                <ul id="porter-list-entrants"></ul>
            </article>
            <article class="porter-column">
                <header><h3>Proveedores</h3><span id="porter-count-suppliers">0</span></header>
                <ul id="porter-list-suppliers"></ul>
            </article>
            <article class="porter-column">
                <header><h3>Compradores</h3><span id="porter-count-buyers">0</span></header>
                <ul id="porter-list-buyers"></ul>
            </article>
            <article class="porter-column">
                <header><h3>Sustitutos</h3><span id="porter-count-substitutes">0</span></header>
                <ul id="porter-list-substitutes"></ul>
            </article>
        </section>
    </section>
""")

PERCEPCION_CLIENTE_HTML = dedent("""
    <section class="percepcion-page" id="percepcion-builder">
        <article class="percepcion-input-card">
            <h2>Percepción del cliente</h2>
            <p>Registra percepciones y clasifícalas para orientar mejoras del servicio.</p>
            <div class="percepcion-input-grid">
                <div class="form-field">
                    <label for="percepcion-description">Comentario</label>
                    <textarea id="percepcion-description" placeholder="Describe la percepción detectada"></textarea>
                </div>
                <div class="form-field">
                    <label for="percepcion-category">Categoría</label>
                    <select id="percepcion-category">
                        <option value="positive">Percepción positiva</option>
                        <option value="neutral">Percepción neutral</option>
                        <option value="negative">Percepción negativa</option>
                    </select>
                </div>
                <div class="form-field">
                    <label for="percepcion-priority">Prioridad</label>
                    <select id="percepcion-priority">
                        <option value="high">Alta</option>
                        <option value="medium">Media</option>
                        <option value="low">Baja</option>
                    </select>
                </div>
            </div>
            <div class="percepcion-input-actions">
                <button type="button" id="percepcion-add">Agregar percepción</button>
            </div>
        </article>
        <section class="percepcion-board">
            <article class="percepcion-column">
                <header><h3>Positivas</h3><span id="percepcion-count-positive">0</span></header>
                <ul id="percepcion-list-positive"></ul>
            </article>
            <article class="percepcion-column">
                <header><h3>Neutrales</h3><span id="percepcion-count-neutral">0</span></header>
                <ul id="percepcion-list-neutral"></ul>
            </article>
            <article class="percepcion-column">
                <header><h3>Negativas</h3><span id="percepcion-count-negative">0</span></header>
                <ul id="percepcion-list-negative"></ul>
            </article>
        </section>
    </section>
""")

PLAN_ESTRATEGICO_HTML = dedent("""
    <section class="plan-shell">
        <style>
            .plan-shell {
                display: grid;
                gap: 14px;
            }
            .plan-header {
                background: linear-gradient(125deg, #102c4a 0%, #155179 55%, #1d7db0 100%);
                border-radius: 16px;
                padding: 20px;
                color: #f4f8ff;
                box-shadow: 0 12px 30px rgba(12, 38, 61, 0.25);
            }
            .plan-header h2 {
                margin: 0 0 6px;
                font-size: 1.3rem;
            }
            .plan-header p {
                margin: 0;
                opacity: 0.95;
                line-height: 1.55;
            }
            .plan-kpis {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 10px;
            }
            .plan-kpi {
                background: #fff;
                border: 1px solid #dbe6f3;
                border-radius: 12px;
                padding: 12px;
                box-shadow: 0 6px 16px rgba(15, 38, 61, 0.08);
            }
            .plan-kpi small {
                display: block;
                color: #546b84;
                margin-bottom: 6px;
            }
            .plan-kpi strong {
                color: #13314e;
                font-size: 1.28rem;
            }
            .plan-grid {
                display: grid;
                grid-template-columns: 1.2fr 0.8fr;
                gap: 12px;
            }
            .plan-card {
                background: #fff;
                border: 1px solid #dbe6f3;
                border-radius: 14px;
                padding: 14px;
                box-shadow: 0 6px 16px rgba(15, 38, 61, 0.08);
            }
            .plan-card h3 {
                margin: 0 0 10px;
                font-size: 1rem;
                color: #113250;
            }
            .plan-list {
                margin: 0;
                padding: 0;
                list-style: none;
                display: grid;
                gap: 8px;
            }
            .plan-list li {
                border: 1px solid #e5edf6;
                border-radius: 10px;
                background: #f8fbff;
                padding: 10px;
                line-height: 1.45;
                color: #24435f;
            }
            .plan-roadmap {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 10px;
            }
            .phase {
                border-radius: 12px;
                border: 1px dashed #bed0e4;
                background: #f4f9ff;
                padding: 10px;
            }
            .phase strong {
                display: block;
                color: #0f2f4d;
                margin-bottom: 6px;
            }
            .phase span {
                color: #47627f;
                font-size: 0.9rem;
            }
            @media (max-width: 980px) {
                .plan-kpis {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
                .plan-grid {
                    grid-template-columns: 1fr;
                }
                .plan-roadmap {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
            }
            @media (max-width: 620px) {
                .plan-kpis,
                .plan-roadmap {
                    grid-template-columns: 1fr;
                }
            }
        </style>

        <article class="plan-header">
            <h2>Plan estratégico institucional</h2>
            <p>
                Cascarón para estructurar visión, ejes estratégicos, objetivos, iniciativas y metas
                con trazabilidad al POA.
            </p>
        </article>

        <section class="plan-kpis">
            <article class="plan-kpi"><small>Objetivos estratégicos</small><strong>12</strong></article>
            <article class="plan-kpi"><small>Iniciativas activas</small><strong>24</strong></article>
            <article class="plan-kpi"><small>Indicadores vinculados</small><strong>36</strong></article>
            <article class="plan-kpi"><small>Avance del plan</small><strong>74%</strong></article>
        </section>

        <section class="plan-grid">
            <article class="plan-card">
                <h3>Objetivos priorizados</h3>
                <ul class="plan-list">
                    <li><strong>OE-01:</strong> Fortalecer la sostenibilidad financiera institucional.</li>
                    <li><strong>OE-02:</strong> Mejorar la satisfacción de clientes y usuarios finales.</li>
                    <li><strong>OE-03:</strong> Optimizar procesos críticos y tiempos de respuesta.</li>
                    <li><strong>OE-04:</strong> Impulsar capacidades del talento y cultura de mejora continua.</li>
                </ul>
            </article>
            <article class="plan-card">
                <h3>Ejes estratégicos</h3>
                <ul class="plan-list">
                    <li>Gobernanza y cumplimiento</li>
                    <li>Excelencia operativa</li>
                    <li>Innovación y digitalización</li>
                    <li>Desarrollo del talento</li>
                </ul>
            </article>
        </section>

        <article class="plan-card">
            <h3>Hoja de ruta (cascarón)</h3>
            <div class="plan-roadmap">
                <div class="phase"><strong>Fase 1</strong><span>Diagnóstico estratégico y línea base.</span></div>
                <div class="phase"><strong>Fase 2</strong><span>Definición de objetivos, metas e indicadores.</span></div>
                <div class="phase"><strong>Fase 3</strong><span>Implementación de iniciativas y seguimiento.</span></div>
                <div class="phase"><strong>Fase 4</strong><span>Evaluación de resultados y ajuste del plan.</span></div>
            </div>
        </article>
    </section>
""")

INICIO_BSC_HTML = dedent("""
    <section class="poa-dashboard">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

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
              width: min(80%, 1280px);
              max-width: 100%;
              margin: 0 auto;
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

PROYECTANDO_HTML = dedent("""
    <section class="proyectando-finanzas">
        <style>
            .proyectando-finanzas{
                background:#f4f7fb;
                border-radius:14px;
                padding:6px 0;
            }
            .proyectando-finanzas *{
                box-sizing:border-box;
                font-family:Arial, sans-serif;
            }
            .container{
                margin-left:10%;
                margin-right:10%;
                padding:30px 0;
            }
            .title{
                margin-bottom:25px;
                color:#1e293b;
            }
            .card{
                background:white;
                border-radius:14px;
                padding:20px;
                box-shadow:0 10px 25px rgba(0,0,0,.06);
            }
            .kpis{
                display:grid;
                grid-template-columns:repeat(4,1fr);
                gap:15px;
                margin-bottom:20px;
            }
            .kpi h3{
                color:#64748b;
                font-size:14px;
                margin:0;
            }
            .kpi h2{
                margin:10px 0 0;
                font-size:28px;
            }
            .grid{
                display:grid;
                grid-template-columns:2fr 1fr;
                gap:20px;
                margin-bottom:20px;
            }
            .form{
                display:grid;
                grid-template-columns:1fr 1fr;
                gap:15px;
                margin-top:15px;
            }
            .proyectando-finanzas label{
                font-size:13px;
                color:#334155;
            }
            .proyectando-finanzas input,
            .proyectando-finanzas select{
                width:100%;
                padding:10px;
                border-radius:10px;
                border:1px solid #cbd5e1;
                margin-top:5px;
            }
            .buttons{
                margin-top:20px;
                display:flex;
                gap:10px;
            }
            .proyectando-finanzas button{
                padding:10px 16px;
                border-radius:10px;
                border:none;
                background:#e2e8f0;
                cursor:pointer;
            }
            .primary{
                background:#2563eb;
                color:white;
            }
            .proyectando-finanzas table{
                width:100%;
                border-collapse:collapse;
                margin-top:15px;
            }
            .proyectando-finanzas th,
            .proyectando-finanzas td{
                padding:12px;
                text-align:left;
                border-bottom:1px solid #e2e8f0;
            }
            .badge{
                padding:6px 12px;
                border-radius:20px;
                font-size:12px;
                display:inline-block;
            }
            .low{background:#dcfce7;color:#166534;}
            .mid{background:#fef3c7;color:#92400e;}
            .high{background:#fee2e2;color:#991b1b;}
            .charts{
                display:grid;
                grid-template-columns:1fr 1fr;
                gap:20px;
            }
            .proyectando-finanzas canvas{
                height:250px !important;
            }
            @media(max-width:1100px){
                .kpis{grid-template-columns:1fr 1fr;}
                .grid{grid-template-columns:1fr;}
                .charts{grid-template-columns:1fr;}
                .container{
                    margin-left:5%;
                    margin-right:5%;
                }
            }
            @media(max-width:680px){
                .form{grid-template-columns:1fr;}
                .kpis{grid-template-columns:1fr;}
            }
        </style>

        <div class="container">
            <div class="kpis">
                <article class="card kpi">
                    <h3>Ingresos proyectados (12m)</h3>
                    <h2>$1,240,000</h2>
                </article>
                <article class="card kpi">
                    <h3>Costos proyectados (12m)</h3>
                    <h2>$918,000</h2>
                </article>
                <article class="card kpi">
                    <h3>Flujo neto estimado</h3>
                    <h2>$322,000</h2>
                </article>
                <article class="card kpi">
                    <h3>Margen estimado</h3>
                    <h2>26%</h2>
                </article>
            </div>

            <div class="grid">
                <article class="card">
                    <h3>Parámetros de proyección</h3>
                    <div class="form">
                        <div>
                            <label>Horizonte</label>
                            <select>
                                <option>12 meses</option>
                                <option>24 meses</option>
                                <option>36 meses</option>
                            </select>
                        </div>
                        <div>
                            <label>Crecimiento mensual (%)</label>
                            <input type="number" value="2.5" step="0.1">
                        </div>
                        <div>
                            <label>Inflación estimada (%)</label>
                            <input type="number" value="4.0" step="0.1">
                        </div>
                        <div>
                            <label>Tasa de descuento (%)</label>
                            <input type="number" value="10.0" step="0.1">
                        </div>
                        <div>
                            <label>Ingresos base mensuales</label>
                            <input type="number" value="85000">
                        </div>
                        <div>
                            <label>Costos base mensuales</label>
                            <input type="number" value="62000">
                        </div>
                    </div>
                    <div class="buttons">
                        <button class="primary" type="button">Calcular proyección</button>
                        <button type="button">Guardar escenario</button>
                        <button type="button">Exportar</button>
                    </div>
                </article>

                <article class="card">
                    <h3>Escenarios</h3>
                    <table>
                        <thead>
                            <tr><th>Escenario</th><th>Flujo neto</th><th>Riesgo</th></tr>
                        </thead>
                        <tbody>
                            <tr><td>Conservador</td><td>$210,000</td><td><span class="badge low">Bajo</span></td></tr>
                            <tr><td>Base</td><td>$322,000</td><td><span class="badge mid">Medio</span></td></tr>
                            <tr><td>Agresivo</td><td>$455,000</td><td><span class="badge high">Alto</span></td></tr>
                        </tbody>
                    </table>
                </article>
            </div>

            <div class="charts">
                <article class="card">
                    <h3>Proyección de ingresos vs costos</h3>
                    <canvas id="proyectando-chart-1"></canvas>
                </article>
                <article class="card">
                    <h3>Flujo neto por escenario</h3>
                    <canvas id="proyectando-chart-2"></canvas>
                </article>
            </div>
        </div>
    </section>
""")

POA_HTML = dedent("""
    <section class="poa-shell">
        <style>
            .poa-shell {
                display: grid;
                gap: 14px;
            }
            .poa-header {
                background: linear-gradient(125deg, #0f2f4b 0%, #14557f 55%, #1b80b6 100%);
                border-radius: 16px;
                padding: 20px;
                color: #f4f9ff;
                box-shadow: 0 12px 30px rgba(10, 38, 61, 0.24);
            }
            .poa-header h2 {
                margin: 0 0 6px;
                font-size: 1.3rem;
            }
            .poa-header p {
                margin: 0;
                line-height: 1.55;
                opacity: 0.95;
            }
            .poa-kpis {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 10px;
            }
            .poa-kpi {
                background: #fff;
                border: 1px solid #dbe6f3;
                border-radius: 12px;
                padding: 12px;
                box-shadow: 0 6px 16px rgba(15, 38, 61, 0.08);
            }
            .poa-kpi small {
                display: block;
                color: #546b84;
                margin-bottom: 6px;
            }
            .poa-kpi strong {
                color: #13314e;
                font-size: 1.28rem;
            }
            .poa-grid {
                display: grid;
                grid-template-columns: 1.2fr 0.8fr;
                gap: 12px;
            }
            .poa-card {
                background: #fff;
                border: 1px solid #dbe6f3;
                border-radius: 14px;
                padding: 14px;
                box-shadow: 0 6px 16px rgba(15, 38, 61, 0.08);
            }
            .poa-card h3 {
                margin: 0 0 10px;
                font-size: 1rem;
                color: #113250;
            }
            .poa-list {
                margin: 0;
                padding: 0;
                list-style: none;
                display: grid;
                gap: 8px;
            }
            .poa-list li {
                border: 1px solid #e5edf6;
                border-radius: 10px;
                background: #f8fbff;
                padding: 10px;
                line-height: 1.45;
                color: #24435f;
            }
            .poa-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 0.92rem;
            }
            .poa-table th,
            .poa-table td {
                text-align: left;
                padding: 9px 8px;
                border-bottom: 1px solid #e5edf6;
            }
            .poa-badge {
                display: inline-block;
                font-size: 0.78rem;
                font-weight: 700;
                border-radius: 999px;
                padding: 4px 8px;
            }
            .ok { background: #dcfce7; color: #166534; }
            .warn { background: #fef3c7; color: #92400e; }
            .crit { background: #fee2e2; color: #991b1b; }
            .poa-roadmap {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 10px;
            }
            .poa-phase {
                border-radius: 12px;
                border: 1px dashed #bed0e4;
                background: #f4f9ff;
                padding: 10px;
            }
            .poa-phase strong {
                display: block;
                color: #0f2f4d;
                margin-bottom: 6px;
            }
            .poa-phase span {
                color: #47627f;
                font-size: 0.9rem;
            }
            @media (max-width: 980px) {
                .poa-kpis {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
                .poa-grid {
                    grid-template-columns: 1fr;
                }
                .poa-roadmap {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
            }
            @media (max-width: 620px) {
                .poa-kpis,
                .poa-roadmap {
                    grid-template-columns: 1fr;
                }
            }
        </style>

        <article class="poa-header">
            <h2>Programación Operativa Anual (POA)</h2>
            <p>
                Cascarón para planificar actividades operativas, responsables, presupuesto, hitos
                y seguimiento trimestral alineado al plan estratégico.
            </p>
        </article>

        <section class="poa-kpis">
            <article class="poa-kpi"><small>Actividades programadas</small><strong>64</strong></article>
            <article class="poa-kpi"><small>Actividades en ejecución</small><strong>39</strong></article>
            <article class="poa-kpi"><small>Cumplimiento trimestral</small><strong>76%</strong></article>
            <article class="poa-kpi"><small>Desviaciones críticas</small><strong>5</strong></article>
        </section>

        <section class="poa-grid">
            <article class="poa-card">
                <h3>Metas operativas priorizadas</h3>
                <ul class="poa-list">
                    <li><strong>MO-01:</strong> Reducir tiempos de atención de solicitudes en 20%.</li>
                    <li><strong>MO-02:</strong> Estandarizar procesos clave en áreas operativas.</li>
                    <li><strong>MO-03:</strong> Incrementar productividad por célula de trabajo.</li>
                    <li><strong>MO-04:</strong> Asegurar cumplimiento de cronograma anual.</li>
                </ul>
            </article>
            <article class="poa-card">
                <h3>Responsables por frente</h3>
                <ul class="poa-list">
                    <li>Operaciones: Dirección Operativa</li>
                    <li>Calidad: Coordinación de Mejora Continua</li>
                    <li>Tecnología: Equipo de Transformación Digital</li>
                    <li>Control: PMO / Planeación</li>
                </ul>
            </article>
        </section>

        <article class="poa-card">
            <h3>Seguimiento trimestral (cascarón)</h3>
            <table class="poa-table">
                <thead>
                    <tr>
                        <th>Trimestre</th>
                        <th>Meta</th>
                        <th>Avance</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td>T1</td><td>18 hitos</td><td>16 / 18</td><td><span class="poa-badge ok">En meta</span></td></tr>
                    <tr><td>T2</td><td>16 hitos</td><td>12 / 16</td><td><span class="poa-badge warn">En riesgo</span></td></tr>
                    <tr><td>T3</td><td>15 hitos</td><td>0 / 15</td><td><span class="poa-badge crit">Pendiente</span></td></tr>
                    <tr><td>T4</td><td>15 hitos</td><td>0 / 15</td><td><span class="poa-badge crit">Pendiente</span></td></tr>
                </tbody>
            </table>
        </article>

        <article class="poa-card">
            <h3>Cronograma anual (cascarón)</h3>
            <div class="poa-roadmap">
                <div class="poa-phase"><strong>Q1</strong><span>Arranque operativo y ajustes de línea base.</span></div>
                <div class="poa-phase"><strong>Q2</strong><span>Escalamiento de iniciativas y control de costos.</span></div>
                <div class="poa-phase"><strong>Q3</strong><span>Consolidación de mejoras y auditoría de avance.</span></div>
                <div class="poa-phase"><strong>Q4</strong><span>Cierre, evaluación de resultados y lecciones aprendidas.</span></div>
            </div>
        </article>
    </section>
""")

KPI_HTML = dedent("""
    <section class="foda-page">
        <article class="foda-input-card">
            <h2>KPIs</h2>
            <p>Panel para administrar indicadores clave de desempeño por objetivo y periodo.</p>
            <div class="foda-matrix">
                <article class="foda-quadrant">
                    <header><h3>Indicadores activos</h3><span>0</span></header>
                    <ul><li class="foda-item"><div><strong>Sin indicadores cargados</strong><br><small>Define KPIs por objetivo estratégico.</small></div></li></ul>
                </article>
                <article class="foda-quadrant">
                    <header><h3>Alertas</h3><span>0</span></header>
                    <ul><li class="foda-item"><div><strong>Sin alertas</strong><br><small>Se mostrarán desvíos y umbrales fuera de rango.</small></div></li></ul>
                </article>
            </div>
        </article>
    </section>
""")

REPORTES_HTML = dedent("""
    <section class="foda-page">
        <article class="foda-input-card">
            <h2>Reportes</h2>
            <p>Consolida reportes de avance, desempeño y seguimiento para exportación.</p>
            <div class="foda-matrix">
                <article class="foda-quadrant">
                    <header><h3>Reportes disponibles</h3><span>3</span></header>
                    <ul>
                        <li class="foda-item"><div><strong>Reporte ejecutivo</strong><br><small>Resumen de estado estratégico.</small></div></li>
                        <li class="foda-item"><div><strong>Reporte operativo</strong><br><small>Actividades, avances y cumplimiento.</small></div></li>
                        <li class="foda-item"><div><strong>Reporte KPI</strong><br><small>Indicadores, metas y variaciones.</small></div></li>
                    </ul>
                </article>
                <article class="foda-quadrant">
                    <header><h3>Exportaciones</h3><span>PDF / Excel</span></header>
                    <ul>
                        <li class="foda-item"><div><strong>Formato PDF</strong><br><small>Para distribución institucional.</small></div></li>
                        <li class="foda-item"><div><strong>Formato Excel</strong><br><small>Para análisis detallado.</small></div></li>
                    </ul>
                </article>
            </div>
        </article>
    </section>
""")


def render_personalizacion_page(request: Request) -> HTMLResponse:
    return render_backend_page(
        request,
        title="Personalizar",
        description="Agrega tu imagen corporativa",
        content=PERSONALIZACION_HTML,
        hide_floating_actions=False,
        floating_actions_screen="personalization",
    )


@app.get("/personalizar-pantalla", response_class=HTMLResponse)
def personalizar_pantalla(request: Request):
    require_superadmin(request)
    return backend_screen(
        request,
        title="Personalizar",
        subtitle="Colores institucionales",
        description="Agrega tu imagen corporativa",
        content=PERSONALIZACION_HTML,
        view_buttons=[
            {"label": "Formulario", "view": "form", "icon": "/templates/icon/formulario.svg"},
            {"label": "Lista", "view": "list", "icon": "/templates/icon/list.svg"},
            {"label": "Colores", "view": "colores", "icon": "/templates/icon/personalizacion.svg", "active": True},
        ],
        hide_floating_actions=False,
    )


@app.get("/backend-template", response_class=HTMLResponse)
def backend_template(request: Request):
    placeholder = "<section style='min-height:300px;display:flex;align-items:center;justify-content:center;'><strong>Template listo para montar una página de backend.</strong></section>"
    return render_backend_page(
        request,
            title="Backend Template",
            description="Cascarón para nuevas pantallas",
            content=placeholder,
            hide_floating_actions=False,
            view_buttons=[
                {"label": "Formulario", "icon": "/templates/icon/formulario.svg", "view": "form"},
                {"label": "Lista", "icon": "/templates/icon/list.svg", "view": "list"},
                {"label": "Kanban", "icon": "/templates/icon/kanban.svg", "view": "kanban"},
                {"label": "Gráfica", "icon": "/templates/icon/grid.svg", "view": "grafica"},
                {"label": "Gantt", "icon": "/templates/icon/grid.svg", "view": "gantt"},
                {"label": "Dashboard", "icon": "/templates/icon/tablero.svg", "view": "dashboard"},
                {"label": "Calendario", "icon": "/templates/icon/calendario.svg", "view": "calendario"},
            ],
        )


@app.get("/reportes", response_class=HTMLResponse)
def reportes(request: Request):
    return render_backend_page(
        request,
        title="Reportes",
        description="Resumen de indicadores, exportaciones y archivos generados",
        content=REPORTES_HTML,
        hide_floating_actions=False,
        floating_actions_html="""
            <div class="floating-actions-group" data-floating-screen="reportes">
                <button class="action-button" type="button" id="action-export-reportes" aria-label="Exportar">
                    <img src="/templates/icon/guardar.svg" alt="Exportar">
                    <span class="action-label">Exportar</span>
                </button>
                <button class="action-button" type="button" id="action-export-pdf" aria-label="Generar PDF">
                    <img src="/templates/icon/guardar.svg" alt="PDF">
                    <span class="action-label">PDF</span>
                </button>
                <button class="action-button" type="button" id="action-export-excel" aria-label="Generar Excel">
                    <img src="/templates/icon/list.svg" alt="Excel">
                    <span class="action-label">Excel</span>
                </button>
            </div>
        """,
        floating_actions_screen="reportes",
    )


@app.get("/api/reportes/export/{formato}")
def exportar_reporte(formato: str):
    formato_normalizado = (formato or "").strip().lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    context = _build_report_export_context()
    rows = _build_report_export_rows()

    if formato_normalizado == "html":
        document = _build_report_export_html_document()
        filename = f"reporte_consolidado_{timestamp}.html"
        return Response(
            content=document,
            media_type="text/html; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    if formato_normalizado == "pdf":
        filename = f"reporte_consolidado_{timestamp}.pdf"
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        y = height - 56
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(48, y, context["empresa"])
        y -= 20
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(48, y, context["titulo_reporte"])
        y -= 16
        pdf.setFont("Helvetica", 10)
        pdf.drawString(48, y, context["subtitulo_reporte"])
        y -= 16
        pdf.drawString(48, y, f"Fecha: {context['fecha_reporte']}")
        y -= 28
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(48, y, "Detalle de reportes")
        y -= 18
        pdf.setFont("Helvetica", 10)
        for row in rows:
            line = f"- {row['reporte']}: {row['descripcion']} ({row['formato']})"
            pdf.drawString(48, y, line[:110])
            y -= 14
            if y < 60:
                pdf.showPage()
                y = height - 56
                pdf.setFont("Helvetica", 10)
        pdf.save()
        content = buffer.getvalue()
        buffer.close()
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    if formato_normalizado == "excel":
        filename = f"reporte_consolidado_{timestamp}.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "Reporte"
        ws["A1"] = context["empresa"]
        ws["A2"] = context["titulo_reporte"]
        ws["A3"] = context["subtitulo_reporte"]
        ws["A4"] = f"Fecha: {context['fecha_reporte']}"
        ws["A6"] = "Reporte"
        ws["B6"] = "Descripcion"
        ws["C6"] = "Formato"
        row_index = 7
        for row in rows:
            ws[f"A{row_index}"] = row["reporte"]
            ws[f"B{row_index}"] = row["descripcion"]
            ws[f"C{row_index}"] = row["formato"]
            row_index += 1
        output = BytesIO()
        wb.save(output)
        content = output.getvalue()
        output.close()
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return JSONResponse({"success": False, "error": "Formato no soportado"}, status_code=400)


@app.get("/kpis", response_class=HTMLResponse)
def kpis_page(request: Request):
    return render_backend_page(
        request,
        title="KPIs",
        description="Gestión y seguimiento de indicadores clave de desempeño.",
        content=KPI_HTML,
        hide_floating_actions=True,
        show_page_header=True,
    )



# --- NUEVO: Endpoint dinámico para usuarios desde BD ---
def _render_usuarios_page(request: Request) -> HTMLResponse:
    db = SessionLocal()
    usuarios = db.query(Usuario).all()
    db.close()
    usuarios_content = f"""
        <section id="usuario-panel" class="usuario-panel">
            <div id="usuario-view"></div>
        </section>
    """
    return render_backend_page(
        request,
        title="Usuarios",
        description="Gestiona usuarios, roles y permisos desde la misma pantalla",
        content=usuarios_content,
        hide_floating_actions=False,
        view_buttons=[
            {"label": "Form", "icon": "/templates/icon/formulario.svg", "view": "form", "active": True},
            {"label": "Lista", "icon": "/templates/icon/list.svg", "view": "list"},
            {"label": "Kanban", "icon": "/templates/icon/kanban.svg", "view": "kanban"},
            {"label": "Organigrama", "view": "organigrama"},
        ],
        floating_actions_screen="usuarios",
    )


@app.get("/usuarios", response_class=HTMLResponse)
@app.get("/usuarios-sistema", response_class=HTMLResponse)
def usuarios_page(request: Request):
    return _render_usuarios_page(request)


@app.get("/plantillas", response_class=HTMLResponse)
def plantillas_page(request: Request):
    plantillas_content = """
        <section id="plantillas-page" class="plantillas-page">
            <div class="plantillas-layout">
                <aside class="plantillas-list-card">
                    <h3>Plantillas</h3>
                    <p class="plantillas-hint">Selecciona una plantilla existente o crea una nueva desde la barra flotante. "Encabezado" es la base para todos los reportes.</p>
                    <ul id="plantillas-list" class="plantillas-list"></ul>
                </aside>
                <section class="plantillas-editor-card">
                    <div class="form-field">
                        <label for="template-name">Nombre de plantilla</label>
                        <input type="text" id="template-name" placeholder="Ej: Tarjeta institucional">
                    </div>
                    <div class="plantillas-editor-grid">
                        <div class="form-field">
                            <label for="template-html">HTML</label>
                            <textarea id="template-html" class="plantilla-code" placeholder="<section class='card'>...</section>"></textarea>
                        </div>
                        <div class="form-field">
                            <label for="template-css">CSS</label>
                            <textarea id="template-css" class="plantilla-code" placeholder=".card { padding: 16px; border-radius: 12px; }"></textarea>
                        </div>
                    </div>
                    <div class="plantillas-preview-head">
                        <h4>Vista previa</h4>
                        <div style="display:flex; gap:8px;">
                            <button type="button" id="template-new-btn">Nuevo</button>
                            <button type="button" id="template-edit-btn">Editar</button>
                            <button type="button" id="template-builder-btn">Construir formulario</button>
                            <button type="button" id="template-preview-btn">Previsualizar</button>
                            <button type="button" id="template-save-btn">Guardar</button>
                            <button type="button" id="template-delete-btn">Eliminar</button>
                        </div>
                    </div>
                    <iframe id="template-preview" class="plantilla-preview-frame" title="Vista previa de plantilla"></iframe>
                    <section id="form-builder-panel" class="form-builder-panel hidden" aria-label="Constructor de formularios">
                        <div class="form-builder-head">
                            <h4>Constructor de formularios</h4>
                            <p>Crea formularios dinámicos para usuarios finales.</p>
                        </div>
                        <div class="form-builder-grid">
                            <div class="form-field">
                                <label for="builder-form-select">Formularios existentes</label>
                                <select id="builder-form-select" class="campo-personalizado">
                                    <option value="">Nuevo formulario</option>
                                </select>
                            </div>
                            <div class="form-field">
                                <label for="builder-form-name">Nombre</label>
                                <input type="text" id="builder-form-name" class="campo-personalizado" placeholder="Ej: Solicitud de crédito">
                            </div>
                            <div class="form-field">
                                <label for="builder-form-slug">Slug (opcional)</label>
                                <input type="text" id="builder-form-slug" class="campo-personalizado" placeholder="solicitud-credito">
                            </div>
                            <div class="form-field">
                                <label for="builder-form-active">Estado</label>
                                <select id="builder-form-active" class="campo-personalizado">
                                    <option value="true">Activo</option>
                                    <option value="false">Inactivo</option>
                                </select>
                            </div>
                            <div class="form-field form-builder-description">
                                <label for="builder-form-description">Descripción</label>
                                <textarea id="builder-form-description" class="campo-personalizado" placeholder="Descripción del formulario"></textarea>
                            </div>
                            <div class="form-field form-builder-description">
                                <label for="builder-form-config">Configuración (JSON)</label>
                                <textarea id="builder-form-config" class="campo-personalizado" placeholder='{"wizard":{"steps":[{"title":"Paso 1","fields":["nombre","email"]},{"title":"Paso 2","fields":["tipo","detalle"]}]},"notifications":{"email":{"enabled":true,"to":["equipo@empresa.com"],"cc":[],"subject":"Nuevo envio"},"webhooks":[{"url":"https://api.empresa.com/hook/forms","method":"POST"}]}}'></textarea>
                            </div>
                        </div>
                        <div class="form-builder-field-editor">
                            <h5>Agregar campo</h5>
                            <div class="form-builder-grid field-grid">
                                <div class="form-field">
                                    <label for="builder-field-type">Tipo</label>
                                    <select id="builder-field-type" class="campo-personalizado">
                                        <option value="text">Texto corto</option>
                                        <option value="textarea">Texto largo</option>
                                        <option value="email">Email</option>
                                        <option value="password">Contraseña</option>
                                        <option value="number">Número (decimal)</option>
                                        <option value="integer">Número (entero)</option>
                                        <option value="select">Desplegable (Dropdown)</option>
                                        <option value="checkboxes">Opción múltiple (Checkboxes)</option>
                                        <option value="radio">Opción única (Radio)</option>
                                        <option value="likert">Escala Likert</option>
                                        <option value="checkbox">Checkbox</option>
                                        <option value="date">Selector de fecha</option>
                                        <option value="time">Selector de hora</option>
                                        <option value="daterange">Rango de fechas</option>
                                        <option value="file">Carga de archivos</option>
                                        <option value="signature">Firma digital</option>
                                        <option value="url">Enlace (URL)</option>
                                        <option value="header">Encabezado</option>
                                        <option value="paragraph">Texto estático (Paragraph)</option>
                                        <option value="html">Texto estático (HTML)</option>
                                        <option value="divider">Separador</option>
                                        <option value="pagebreak">Salto de página</option>
                                    </select>
                                </div>
                                <div class="form-field">
                                    <label for="builder-field-label">Etiqueta</label>
                                    <input type="text" id="builder-field-label" class="campo-personalizado" placeholder="Nombre completo">
                                </div>
                                <div class="form-field">
                                    <label for="builder-field-name">Nombre técnico</label>
                                    <input type="text" id="builder-field-name" class="campo-personalizado" placeholder="nombre_completo">
                                </div>
                                <div class="form-field">
                                    <label for="builder-field-placeholder">Placeholder</label>
                                    <input type="text" id="builder-field-placeholder" class="campo-personalizado" placeholder="Escribe aquí">
                                </div>
                                <div class="form-field">
                                    <label for="builder-field-help">Ayuda</label>
                                    <input type="text" id="builder-field-help" class="campo-personalizado" placeholder="Texto de ayuda">
                                </div>
                                <div class="form-field">
                                    <label for="builder-field-options">Opciones (select/radio)</label>
                                    <input type="text" id="builder-field-options" class="campo-personalizado" placeholder="Opción A, Opción B, Opción C">
                                </div>
                                <div class="form-field">
                                    <label for="builder-field-conditional">Condicional (JSON)</label>
                                    <input type="text" id="builder-field-conditional" class="campo-personalizado" placeholder='{"field":"tipo","operator":"equals","value":"staff"}'>
                                </div>
                                <div class="form-field form-field-inline">
                                    <label for="builder-field-required">Obligatorio</label>
                                    <input type="checkbox" id="builder-field-required">
                                </div>
                            </div>
                            <div class="form-builder-actions">
                                <button type="button" id="builder-add-field-btn">Agregar campo</button>
                                <button type="button" id="builder-clear-form-btn">Limpiar</button>
                                <button type="button" id="builder-save-form-btn">Guardar formulario</button>
                                <button type="button" id="builder-delete-form-btn">Eliminar formulario</button>
                            </div>
                        </div>
                        <div class="form-builder-list-wrap">
                            <h5>Campos del formulario</h5>
                            <div id="builder-fields-list" class="form-builder-fields-list"></div>
                        </div>
                    </section>
                </section>
            </div>
        </section>
    """
    return render_backend_page(
        request,
        title="Plantillas",
        description="Crea y guarda plantillas con HTML y CSS.",
        content=plantillas_content,
        hide_floating_actions=False,
        floating_actions_screen="plantillas",
    )


@app.get("/api/plantillas")
def listar_plantillas():
    return JSONResponse({"success": True, "data": _load_plantillas_store()})


@app.post("/api/plantillas")
def guardar_plantilla(data: dict = Body(...)):
    nombre = (data.get("nombre") or "").strip()
    html_code = data.get("html") or ""
    css_code = data.get("css") or ""
    template_id = (data.get("id") or "").strip()
    if not nombre:
        return JSONResponse({"success": False, "error": "El nombre es obligatorio"}, status_code=400)
    if not html_code.strip() and not css_code.strip():
        return JSONResponse({"success": False, "error": "Debes agregar HTML o CSS"}, status_code=400)

    templates = _load_plantillas_store()
    now_iso = datetime.utcnow().isoformat()
    if template_id:
        updated = False
        for template in templates:
            if template.get("id") == template_id:
                template["nombre"] = nombre
                template["html"] = html_code
                template["css"] = css_code
                template["updated_at"] = now_iso
                updated = True
                break
        if not updated:
            return JSONResponse({"success": False, "error": "Plantilla no encontrada"}, status_code=404)
    else:
        template_id = secrets.token_hex(8)
        templates.insert(
            0,
            {
                "id": template_id,
                "nombre": nombre,
                "html": html_code,
                "css": css_code,
                "created_at": now_iso,
                "updated_at": now_iso,
            },
        )
    _save_plantillas_store(templates)
    return JSONResponse({"success": True, "data": {"id": template_id}})


@app.post("/api/admin/forms", response_model=FormDefinitionResponseSchema)
def create_form_definition(
    request: Request,
    form_data: FormDefinitionCreateSchema,
    db=Depends(get_db),
):
    require_admin_or_superadmin(request)
    slug = slugify_value(form_data.slug or form_data.name)
    existing = db.query(FormDefinition).filter(FormDefinition.slug == slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="El slug ya existe")

    form = FormDefinition(
        name=form_data.name,
        slug=slug,
        description=form_data.description,
        config=form_data.config or {},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_active=form_data.is_active,
    )
    db.add(form)
    db.flush()

    for field_data in form_data.fields:
        db.add(
            FormField(
                form_id=form.id,
                field_type=field_data.field_type,
                label=field_data.label,
                name=field_data.name,
                placeholder=field_data.placeholder,
                help_text=field_data.help_text,
                default_value=field_data.default_value,
                is_required=field_data.is_required,
                validation_rules=field_data.validation_rules,
                options=field_data.options,
                order=field_data.order,
                conditional_logic=field_data.conditional_logic,
            )
        )

    db.commit()
    db.refresh(form)
    return form


@app.get("/api/admin/forms", response_model=List[FormDefinitionResponseSchema])
def list_form_definitions(
    request: Request,
    db=Depends(get_db),
):
    require_admin_or_superadmin(request)
    return db.query(FormDefinition).order_by(FormDefinition.id.desc()).all()


@app.get("/api/admin/forms/{form_id}", response_model=FormDefinitionResponseSchema)
def get_form_definition(
    form_id: int,
    request: Request,
    db=Depends(get_db),
):
    require_admin_or_superadmin(request)
    form = db.query(FormDefinition).filter(FormDefinition.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Formulario no encontrado")
    return form


@app.put("/api/admin/forms/{form_id}")
def update_form_definition(
    form_id: int,
    request: Request,
    form_data: FormDefinitionCreateSchema,
    db=Depends(get_db),
):
    require_admin_or_superadmin(request)
    form = db.query(FormDefinition).filter(FormDefinition.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Formulario no encontrado")

    new_slug = slugify_value(form_data.slug or form_data.name)
    duplicate = (
        db.query(FormDefinition)
        .filter(FormDefinition.slug == new_slug, FormDefinition.id != form_id)
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=400, detail="El slug ya existe")

    form.name = form_data.name
    form.slug = new_slug
    form.description = form_data.description
    form.config = form_data.config or {}
    form.is_active = form_data.is_active
    form.updated_at = datetime.utcnow()
    db.add(form)

    db.query(FormField).filter(FormField.form_id == form_id).delete()
    for field_data in form_data.fields:
        db.add(
            FormField(
                form_id=form_id,
                field_type=field_data.field_type,
                label=field_data.label,
                name=field_data.name,
                placeholder=field_data.placeholder,
                help_text=field_data.help_text,
                default_value=field_data.default_value,
                is_required=field_data.is_required,
                validation_rules=field_data.validation_rules,
                options=field_data.options,
                order=field_data.order,
                conditional_logic=field_data.conditional_logic,
            )
        )

    db.commit()
    return {"success": True, "message": "Formulario actualizado"}


@app.delete("/api/admin/forms/{form_id}")
def delete_form_definition(
    form_id: int,
    request: Request,
    db=Depends(get_db),
):
    require_admin_or_superadmin(request)
    form = db.query(FormDefinition).filter(FormDefinition.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Formulario no encontrado")
    db.delete(form)
    db.commit()
    return {"success": True, "message": "Formulario eliminado"}


@app.get("/api/admin/forms/{form_id}/submissions/export/{formato}")
def export_form_submissions(
    form_id: int,
    formato: str,
    request: Request,
    db=Depends(get_db),
):
    require_admin_or_superadmin(request)
    form = db.query(FormDefinition).filter(FormDefinition.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Formulario no encontrado")

    submissions = (
        db.query(FormSubmission)
        .filter(FormSubmission.form_id == form_id)
        .order_by(FormSubmission.submitted_at.asc(), FormSubmission.id.asc())
        .all()
    )
    columns = _build_submission_export_columns(form, submissions)
    base_headers = ["submission_id", "submitted_at", "ip_address", "user_agent"]
    headers = [*base_headers, *columns]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_slug = slugify_value(form.slug or form.name)

    if formato.lower() == "csv":
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=headers)
        writer.writeheader()
        for submission in submissions:
            data = submission.data if isinstance(submission.data, dict) else {}
            row = {
                "submission_id": submission.id,
                "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else "",
                "ip_address": submission.ip_address or "",
                "user_agent": submission.user_agent or "",
            }
            for field_name in columns:
                row[field_name] = _normalize_submission_value(data.get(field_name))
            writer.writerow(row)
        filename = f"{safe_slug}_submissions_{timestamp}.csv"
        return Response(
            content=buffer.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    if formato.lower() in {"excel", "xlsx"}:
        wb = Workbook()
        ws = wb.active
        ws.title = "Submissions"
        ws.append(headers)
        for submission in submissions:
            data = submission.data if isinstance(submission.data, dict) else {}
            row_values = [
                submission.id,
                submission.submitted_at.isoformat() if submission.submitted_at else "",
                submission.ip_address or "",
                submission.user_agent or "",
            ]
            row_values.extend(_normalize_submission_value(data.get(field_name)) for field_name in columns)
            ws.append(row_values)
        output = BytesIO()
        wb.save(output)
        filename = f"{safe_slug}_submissions_{timestamp}.xlsx"
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    raise HTTPException(status_code=400, detail="Formato no soportado. Usa csv o excel")


@app.get("/api/forms/{slug}")
def get_public_form_definition(
    slug: str,
    db=Depends(get_db),
):
    form = (
        db.query(FormDefinition)
        .filter(FormDefinition.slug == slug, FormDefinition.is_active == True)  # noqa: E712
        .first()
    )
    if not form:
        raise HTTPException(status_code=404, detail="Formulario no encontrado")
    return {"success": True, "data": FormRenderer.render_to_json(form)}


@app.post("/api/forms/{slug}/submit")
def submit_public_form(
    slug: str,
    request: Request,
    payload: Dict[str, Any] = Body(default_factory=dict),
    db=Depends(get_db),
):
    form = (
        db.query(FormDefinition)
        .filter(FormDefinition.slug == slug, FormDefinition.is_active == True)  # noqa: E712
        .first()
    )
    if not form:
        raise HTTPException(status_code=404, detail="Formulario no encontrado")

    normalized_payload = _normalize_form_submission_payload(form, payload)
    visible_fields = FormRenderer.visible_field_names(form, normalized_payload)
    dynamic_model = FormRenderer.generate_pydantic_model(form, visible_field_names=visible_fields)
    try:
        validated = dynamic_model.model_validate(normalized_payload)
        validated_data = validated.model_dump()
        FormRenderer._apply_custom_rules(form, validated_data, visible_field_names=visible_fields)
    except ValidationError as exc:
        return JSONResponse(
            {"success": False, "error": "Datos inválidos", "details": exc.errors()},
            status_code=422,
        )
    except ValueError as exc:
        return JSONResponse(
            {"success": False, "error": str(exc)},
            status_code=422,
        )
    validated_data = {key: value for key, value in validated_data.items() if key in visible_fields}

    submission = FormSubmission(
        form_id=form.id,
        data=validated_data,
        submitted_at=datetime.utcnow(),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    email_status = send_form_submission_email_notification(form, submission)
    webhook_status = send_form_submission_webhooks(form, submission)

    return {
        "success": True,
        "message": "Formulario enviado correctamente",
        "submission_id": submission.id,
        "notification": {
            "email": email_status,
            "webhooks": webhook_status,
        },
    }


@app.get("/forms/{slug}", response_class=HTMLResponse)
def render_public_form(
    slug: str,
    request: Request,
    db=Depends(get_db),
):
    form = (
        db.query(FormDefinition)
        .filter(FormDefinition.slug == slug, FormDefinition.is_active == True)  # noqa: E712
        .first()
    )
    if not form:
        raise HTTPException(status_code=404, detail="Formulario no encontrado")
    login_identity = _get_login_identity_context()
    return request.app.state.templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "title": form.name,
            "form": form,
            "form_json": json.dumps(FormRenderer.render_to_json(form), ensure_ascii=False),
            "app_favicon_url": login_identity.get("login_favicon_url"),
        },
    )


@app.get("/forms/api/{slug}")
def get_public_form_definition_v2(
    slug: str,
    db=Depends(get_db),
):
    form = (
        db.query(FormDefinition)
        .filter(FormDefinition.slug == slug, FormDefinition.is_active == True)  # noqa: E712
        .first()
    )
    if not form:
        raise HTTPException(status_code=404, detail="Formulario no encontrado")
    return {"success": True, "data": FormRenderer.render_to_json(form)}


@app.post("/forms/api/{slug}/submit")
async def submit_public_form_v2(
    slug: str,
    request: Request,
    db=Depends(get_db),
):
    form = (
        db.query(FormDefinition)
        .filter(FormDefinition.slug == slug, FormDefinition.is_active == True)  # noqa: E712
        .first()
    )
    if not form:
        raise HTTPException(status_code=404, detail="Formulario no encontrado")

    form_data = await request.form()
    payload: Dict[str, Any] = {}
    for key in form_data.keys():
        values = form_data.getlist(key)
        payload[key] = values if len(values) > 1 else values[0]
    normalized_payload = _normalize_form_submission_payload(form, payload)
    visible_fields = FormRenderer.visible_field_names(form, normalized_payload)
    dynamic_model = FormRenderer.generate_pydantic_model(form, visible_field_names=visible_fields)
    try:
        validated = dynamic_model.model_validate(normalized_payload)
        validated_data = validated.model_dump()
        FormRenderer._apply_custom_rules(form, validated_data, visible_field_names=visible_fields)
    except ValidationError as exc:
        return JSONResponse(
            {"success": False, "error": "Datos inválidos", "details": exc.errors()},
            status_code=422,
        )
    except ValueError as exc:
        return JSONResponse(
            {"success": False, "error": str(exc)},
            status_code=422,
        )
    validated_data = {key: value for key, value in validated_data.items() if key in visible_fields}

    submission = FormSubmission(
        form_id=form.id,
        data=validated_data,
        submitted_at=datetime.utcnow(),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    email_status = send_form_submission_email_notification(form, submission)
    webhook_status = send_form_submission_webhooks(form, submission)
    return {
        "success": True,
        "message": "Formulario enviado correctamente",
        "submission_id": submission.id,
        "notification": {
            "email": email_status,
            "webhooks": webhook_status,
        },
    }


@app.delete("/api/plantillas/{template_id}")
def eliminar_plantilla(template_id: str):
    template_id = (template_id or "").strip()
    if not template_id:
        return JSONResponse({"success": False, "error": "ID de plantilla invalido"}, status_code=400)
    if template_id == SYSTEM_REPORT_HEADER_TEMPLATE_ID:
        return JSONResponse(
            {"success": False, "error": "La plantilla Encabezado es obligatoria para reportes"},
            status_code=400,
        )

    templates = _load_plantillas_store()
    remaining = [tpl for tpl in templates if str(tpl.get("id", "")).strip() != template_id]
    if len(remaining) == len(templates):
        return JSONResponse({"success": False, "error": "Plantilla no encontrada"}, status_code=404)
    _save_plantillas_store(remaining)
    return JSONResponse({"success": True})


@app.post("/api/usuarios/registro-seguro")
def crear_usuario_seguro(request: Request, data: dict = Body(...)):
    nombre = (data.get("nombre") or "").strip()
    usuario_login = (data.get("usuario") or "").strip()
    correo = (data.get("correo") or "").strip()
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
        exists_login = db.query(Usuario).filter(Usuario.usuario == usuario_login).first()
        if exists_login:
            return JSONResponse({"success": False, "error": "El usuario ya existe"}, status_code=409)
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
            usuario=usuario_login,
            correo=correo,
            contrasena=hash_password(password),
            rol_id=rol_id,
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
                    "correo": nuevo.correo,
                    "rol_id": nuevo.rol_id,
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

        def resolved_role(u: Usuario) -> str:
            if u.rol_id and roles.get(u.rol_id):
                return normalize_role_name(roles.get(u.rol_id))
            return normalize_role_name(u.role)

        data = [
            {
                "id": u.id,
                "nombre": u.nombre,
                "correo": u.correo,
                "rol": resolved_role(u),
                "imagen": u.imagen,
            }
            for u in usuarios
            if not is_hidden_user(request, u.usuario)
            and (is_superadmin(request) or resolved_role(u) != "superadministrador")
        ]
        return JSONResponse({"success": True, "data": data})
    finally:
        db.close()


def _render_areas_page(request: Request) -> HTMLResponse:
    areas_content = """
        <section id="area-panel" class="usuario-panel">
            <div id="area-view"></div>
        </section>
    """
    return render_backend_page(
        request,
        title="Áreas organizacionales",
        description="Administra la estructura de áreas de la organización",
        content=areas_content,
        hide_floating_actions=False,
        view_buttons=[
            {"label": "Form", "icon": "/templates/icon/formulario.svg", "view": "form", "active": True},
            {"label": "Kanban", "icon": "/templates/icon/kanban.svg", "view": "kanban"},
            {"label": "Organigrama", "view": "organigrama"},
        ],
        floating_actions_screen="areas",
    )


@app.get("/areas-organizacionales", response_class=HTMLResponse)
def areas_page(request: Request):
    return _render_areas_page(request)


@app.get("/inicio", response_class=HTMLResponse)
def inicio_page(request: Request):
    return render_backend_page(
        request,
        title="Inicio",
        description="Tablero de control estratégico y táctico",
        content=INICIO_BSC_HTML,
        hide_floating_actions=True,
        show_page_header=True,
        view_buttons=[
            {"label": "Formulario", "icon": "/templates/icon/formulario.svg", "view": "form"},
            {"label": "Lista", "icon": "/templates/icon/list.svg", "view": "list"},
            {"label": "Kanban", "icon": "/templates/icon/kanban.svg", "view": "kanban"},
            {"label": "Dashboard", "icon": "/templates/icon/tablero.svg", "view": "dashboard", "active": True},
        ],
    )


@app.get("/proyectando", response_class=HTMLResponse)
def proyectando_page(request: Request):
    return render_backend_page(
        request,
        title="Proyectando",
        description="Herramienta de proyección financiera",
        content=PROYECTANDO_HTML,
        hide_floating_actions=True,
        show_page_header=True,
        view_buttons=[
            {"label": "Formulario", "icon": "/templates/icon/formulario.svg", "view": "form"},
            {"label": "Lista", "icon": "/templates/icon/list.svg", "view": "list"},
            {"label": "Kanban", "icon": "/templates/icon/kanban.svg", "view": "kanban"},
            {"label": "Dashboard", "icon": "/templates/icon/tablero.svg", "view": "dashboard", "active": True},
        ],
    )


@app.get("/planes", response_class=HTMLResponse)
def plan_estrategico_page(request: Request):
    return render_backend_page(
        request,
        title="Plan estratégico",
        description="Consolidación de planificación estratégica institucional.",
        content=PLAN_ESTRATEGICO_HTML,
        hide_floating_actions=True,
        show_page_header=True,
    )


@app.get("/poa", response_class=HTMLResponse)
def poa_page(request: Request):
    return render_backend_page(
        request,
        title="POA",
        description="Programación operativa anual alineada al plan estratégico.",
        content=POA_HTML,
        hide_floating_actions=True,
        show_page_header=True,
    )


def _render_blank_management_screen(request: Request, title: str) -> HTMLResponse:
    return render_backend_page(
        request,
        title=title,
        description="",
        content="",
        hide_floating_actions=True,
        show_page_header=False,
    )


@app.get("/diagnostico", response_class=HTMLResponse)
def diagnostico_page(request: Request):
    return _render_blank_management_screen(request, "Diagnóstico")


@app.get("/diagnostico/foda", response_class=HTMLResponse)
def diagnostico_foda_page(request: Request):
    return render_backend_page(
        request,
        title="FODA",
        description="Identifica factores internos y externos para el diagnóstico estratégico.",
        content=FODA_HTML,
        hide_floating_actions=True,
        show_page_header=True,
    )


@app.get("/diagnostico/pestel", response_class=HTMLResponse)
def diagnostico_pestel_page(request: Request):
    return render_backend_page(
        request,
        title="PESTEL",
        description="Analiza factores externos que impactan la estrategia institucional.",
        content=PESTEL_HTML,
        hide_floating_actions=True,
        show_page_header=True,
    )


@app.get("/diagnostico/porter", response_class=HTMLResponse)
def diagnostico_porter_page(request: Request):
    return render_backend_page(
        request,
        title="PORTER",
        description="Evalúa las cinco fuerzas competitivas para priorizar decisiones estratégicas.",
        content=PORTER_HTML,
        hide_floating_actions=True,
        show_page_header=True,
    )


@app.get("/diagnostico/percepcion-cliente", response_class=HTMLResponse)
def diagnostico_percepcion_cliente_page(request: Request):
    return render_backend_page(
        request,
        title="Percepción del cliente",
        description="Monitorea feedback para detectar fortalezas y brechas del servicio.",
        content=PERCEPCION_CLIENTE_HTML,
        hide_floating_actions=True,
        show_page_header=True,
    )


BACKEND_ROLES_PERMISSIONS_URL = os.environ.get(
    "BACKEND_ROLES_PERMISSIONS_URL",
    "http://localhost:8000/api/v1/personalizacion/roles-permisos"
)


async def _fetch_roles_permissions_view() -> str:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(BACKEND_ROLES_PERMISSIONS_URL, timeout=10.0)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Error al cargar el módulo de roles: {exc}") from exc
    return resp.text.replace("http://localhost:8000", "http://localhost:8005")


def _render_local_roles_permissions_page(
    request: Request,
    error_detail: Optional[str] = None,
) -> HTMLResponse:
    db = SessionLocal()
    try:
        roles = db.query(Rol).order_by(Rol.id.asc()).all()
    finally:
        db.close()
    error_html = (
        f"<p style='margin:0 0 12px;color:#991b1b;font-weight:600;'>"
        f"Servicio externo no disponible. Se muestra vista local. Detalle: {escape(error_detail or '')}"
        f"</p>"
        if error_detail
        else ""
    )
    rows_html = "".join(
        [
            (
                "<tr>"
                f"<td>{role.id}</td>"
                f"<td>{escape(role.nombre or '')}</td>"
                f"<td>{escape(role.descripcion or '')}</td>"
                "</tr>"
            )
            for role in roles
        ]
    )
    content = f"""
        <section class="form-section">
            {error_html}
            <div class="section-title">
                <h2>Roles y permisos (vista local)</h2>
            </div>
            <p class="plantillas-hint">El módulo remoto no respondió, por lo que se cargó una vista local de contingencia.</p>
            <div style="overflow:auto;">
                <table style="width:100%; border-collapse:collapse; background:#fff;">
                    <thead>
                        <tr>
                            <th style="border:1px solid #cbd5e1; text-align:left; padding:10px;">ID</th>
                            <th style="border:1px solid #cbd5e1; text-align:left; padding:10px;">Rol</th>
                            <th style="border:1px solid #cbd5e1; text-align:left; padding:10px;">Descripción</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
        </section>
    """
    return render_backend_page(
        request,
        title="Roles y permisos",
        description="Gestión de roles y permisos",
        content=content,
        hide_floating_actions=True,
        show_page_header=True,
    )


@app.get("/roles-sistema", response_class=HTMLResponse)
@app.get("/roles-permisos", response_class=HTMLResponse)
@app.get("/api/v1/personalizacion/roles-permisos", response_class=HTMLResponse)
@app.get("/personalizacion/roles-permisos", response_class=HTMLResponse)
async def personalizacion_roles_permisos(request: Request):
    require_superadmin(request)
    try:
        content = await _fetch_roles_permissions_view()
        return HTMLResponse(content=content)
    except HTTPException as exc:
        if exc.status_code == 502:
            return _render_local_roles_permissions_page(request, exc.detail)
        raise


@app.get("/", response_class=HTMLResponse)
def root():
    return "<h1>Bienvenido al módulo de planificación estratégica y POA</h1>"

# Área de configuración de imagen (menú)
@app.get("/configura-imagen", response_class=HTMLResponse)
def configura_imagen():
    # Aquí se usará un template en el futuro
    return "<h2>Configuración de imagen (template)</h2>"


def _render_identidad_institucional_page(request: Request) -> HTMLResponse:
    identity = _load_login_identity()
    favicon_url = _build_login_asset_url(identity.get("favicon_filename"), DEFAULT_LOGIN_IDENTITY["favicon_filename"])
    safe_company_short_name = escape(identity.get("company_short_name", DEFAULT_LOGIN_IDENTITY["company_short_name"]))
    safe_login_message = escape(identity.get("login_message", DEFAULT_LOGIN_IDENTITY["login_message"]))
    logo_url = _build_login_asset_url(identity.get("logo_filename"), DEFAULT_LOGIN_IDENTITY["logo_filename"])
    desktop_bg_url = _build_login_asset_url(identity.get("desktop_bg_filename"), DEFAULT_LOGIN_IDENTITY["desktop_bg_filename"])
    mobile_bg_url = _build_login_asset_url(identity.get("mobile_bg_filename"), DEFAULT_LOGIN_IDENTITY["mobile_bg_filename"])
    saved_flag = request.query_params.get("saved")
    saved_message = "<p style='color:#166534;font-weight:600;margin:0 0 12px;'>Identidad institucional actualizada.</p>" if saved_flag == "1" else ""
    content = f"""
        <section class="foda-page">
            <article class="foda-input-card">
                {saved_message}
                <form id="identity-form" method="post" action="/identidad-institucional" enctype="multipart/form-data" class="foda-input-grid">
                    <input type="hidden" id="remove_favicon" name="remove_favicon" value="0">
                    <input type="hidden" id="remove_logo" name="remove_logo" value="0">
                    <input type="hidden" id="remove_desktop" name="remove_desktop" value="0">
                    <input type="hidden" id="remove_mobile" name="remove_mobile" value="0">
                    <div class="identity-inline-field">
                        <label class="identity-field-label" for="company_short_name">
                            <span>Nombre corto</span>
                            <span>de la empresa:</span>
                        </label>
                        <input class="campo-personalizado" type="text" id="company_short_name" name="company_short_name" value="{safe_company_short_name}" placeholder="Ej: AVAN">
                    </div>
                    <div class="identity-inline-field">
                        <label class="identity-field-label" for="login_message">
                            <span>Mensaje para</span>
                            <span>pantalla de login:</span>
                        </label>
                        <textarea class="campo-personalizado" id="login_message" name="login_message" rows="3" placeholder="Mensaje institucional">{safe_login_message}</textarea>
                    </div>
                    <div class="form-field">
                        <label for="favicon">Favicon</label>
                        <input class="campo-personalizado" type="file" id="favicon" name="favicon" accept="image/*">
                        <small>Actual: {identity.get("favicon_filename", DEFAULT_LOGIN_IDENTITY["favicon_filename"])}</small>
                    </div>
                    <div class="form-field">
                        <label for="logo_empresa">Logo de la empresa</label>
                        <input class="campo-personalizado" type="file" id="logo_empresa" name="logo_empresa" accept="image/*">
                        <small>Actual: {identity.get("logo_filename", DEFAULT_LOGIN_IDENTITY["logo_filename"])}</small>
                    </div>
                    <div class="form-field">
                        <label for="fondo_escritorio">Fondo de escritorio</label>
                        <input class="campo-personalizado" type="file" id="fondo_escritorio" name="fondo_escritorio" accept="image/*">
                        <small>Actual: {identity.get("desktop_bg_filename", DEFAULT_LOGIN_IDENTITY["desktop_bg_filename"])}</small>
                    </div>
                    <div class="form-field">
                        <label for="fondo_movil">Fondo de móvil</label>
                        <input class="campo-personalizado" type="file" id="fondo_movil" name="fondo_movil" accept="image/*">
                        <small>Actual: {identity.get("mobile_bg_filename", DEFAULT_LOGIN_IDENTITY["mobile_bg_filename"])}</small>
                    </div>
                    <div class="foda-input-actions" style="grid-column: 1 / -1;">
                        <button type="submit">Guardar identidad</button>
                    </div>
                </form>
            </article>
            <section class="identity-assets-list">
                <article class="identity-asset-row">
                    <div class="identity-asset-title">Favicon</div>
                    <div class="identity-asset-media">
                        <img src="{favicon_url}" alt="Favicon" class="identity-asset-image identity-asset-image-favicon">
                        <div class="identity-asset-actions">
                            <button type="button" class="identity-asset-edit" data-target-input="favicon">Editar</button>
                            <button type="button" class="identity-asset-delete" data-target-remove="remove_favicon">Eliminar</button>
                        </div>
                    </div>
                </article>
                <article class="identity-asset-row">
                    <div class="identity-asset-title">Logo de la empresa</div>
                    <div class="identity-asset-media">
                        <img src="{logo_url}" alt="Logo" class="identity-asset-image identity-asset-image-logo">
                        <div class="identity-asset-actions">
                            <button type="button" class="identity-asset-edit" data-target-input="logo_empresa">Editar</button>
                            <button type="button" class="identity-asset-delete" data-target-remove="remove_logo">Eliminar</button>
                        </div>
                    </div>
                </article>
                <article class="identity-asset-row">
                    <div class="identity-asset-title">Fondo de escritorio</div>
                    <div class="identity-asset-media">
                        <img src="{desktop_bg_url}" alt="Fondo escritorio" class="identity-asset-image">
                        <div class="identity-asset-actions">
                            <button type="button" class="identity-asset-edit" data-target-input="fondo_escritorio">Editar</button>
                            <button type="button" class="identity-asset-delete" data-target-remove="remove_desktop">Eliminar</button>
                        </div>
                    </div>
                </article>
                <article class="identity-asset-row">
                    <div class="identity-asset-title">Fondo móvil</div>
                    <div class="identity-asset-media">
                        <img src="{mobile_bg_url}" alt="Fondo móvil" class="identity-asset-image">
                        <div class="identity-asset-actions">
                            <button type="button" class="identity-asset-edit" data-target-input="fondo_movil">Editar</button>
                            <button type="button" class="identity-asset-delete" data-target-remove="remove_mobile">Eliminar</button>
                        </div>
                    </div>
                </article>
            </section>
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
    return _render_identidad_institucional_page(request)


@app.post("/identidad-institucional", response_class=HTMLResponse)
async def identidad_institucional_save(
    request: Request,
    company_short_name: str = Form(""),
    login_message: str = Form(""),
    favicon: Optional[UploadFile] = File(None),
    logo_empresa: Optional[UploadFile] = File(None),
    fondo_escritorio: Optional[UploadFile] = File(None),
    fondo_movil: Optional[UploadFile] = File(None),
    remove_favicon: str = Form("0"),
    remove_logo: str = Form("0"),
    remove_desktop: str = Form("0"),
    remove_mobile: str = Form("0"),
):
    current = _load_login_identity()
    current["company_short_name"] = company_short_name.strip() or DEFAULT_LOGIN_IDENTITY["company_short_name"]
    current["login_message"] = login_message.strip() or DEFAULT_LOGIN_IDENTITY["login_message"]

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
    return RedirectResponse(url="/identidad-institucional?saved=1", status_code=303)

# Placeholder para templates
# En el futuro, importar y usar templates para todas las respuestas

if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8005")))

from html import escape
import re
import unicodedata

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import Column, Integer, String

from fastapi_modulo.db import MAIN, SessionLocal, engine


class Rol(MAIN):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True)
    descripcion = Column(String)


DEFAULT_SYSTEM_ROLES = [
    ("superadministrador", "Acceso total a todo el módulo"),
    ("administrador_multiempresa", "Acceso a todas las empresas del sistema"),
    ("administrador", "Acceso completo a su empresa"),
    ("autoridades", "Acceso al tablero de control"),
    ("departamento", "Acceso a su departamento"),
    ("usuario", "Acceso solo a sus datos"),
]


ROLE_ALIASES = {
    "super_admin": "superadministrador",
    "superadministrador": "superadministrador",
    "administrador_multiempresa": "administrador_multiempresa",
    "admin_multiempresa": "administrador_multiempresa",
    "multiempresa_admin": "administrador_multiempresa",
    "administrador_multi": "administrador_multiempresa",
    "admin": "administrador",
    "administrador": "administrador",
    "administador": "administrador",
    "administrdor": "administrador",
    "admnistrador": "administrador",
    "autoridad": "autoridades",
    "autoridades": "autoridades",
    "authority": "autoridades",
    "authorities": "autoridades",
    "strategic_manager": "departamento",
    "department_manager": "departamento",
    "departamento": "departamento",
    "team_leader": "usuario",
    "collaborator": "usuario",
    "viewer": "usuario",
    "usuario": "usuario",
}


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


router = APIRouter()
templates = Jinja2Templates(directory=["fastapi_modulo/templates", "fastapi_modulo"])


def _get_colores_context() -> dict:
    from fastapi_modulo.main import get_colores_context
    return get_colores_context()


def _roles_content(roles: list[Rol]) -> str:
    rows_html = "".join(
        [
            (
                "<tr>"
                f"<td>{escape(role.nombre or '')}</td>"
                f"<td>{escape(role.descripcion or '')}</td>"
                "<td>"
                f"<form method='post' action='/roles/edit/{role.id}'>"
                f"<input type='text' name='nombre' value='{escape(role.nombre or '')}' required class='campo-personalizado'>"
                f"<input type='text' name='descripcion' value='{escape(role.descripcion or '')}' class='campo-personalizado'>"
                "<button type='submit' class='color-btn color-btn--ghost'>Editar</button>"
                "</form>"
                f"<form method='post' action='/roles/delete/{role.id}'>"
                "<button type='submit' class='color-btn color-btn--primary' onclick=\"return confirm('¿Eliminar este rol?')\">Eliminar</button>"
                "</form>"
                "</td>"
                "</tr>"
            )
            for role in roles
        ]
    )
    return f"""
<section class="form-section">
    <div class="section-title">
        <h2>Gestión de roles</h2>
    </div>
    <form method="post" action="/roles/create" class="section-grid">
        <label class="form-field">
            <span>Nombre del rol</span>
            <input type="text" name="nombre" required class="campo-personalizado" placeholder="Nombre del rol">
        </label>
        <label class="form-field">
            <span>Descripción</span>
            <input type="text" name="descripcion" class="campo-personalizado" placeholder="Descripción del rol">
        </label>
        <div class="form-field">
            <button type="submit" class="color-btn color-btn--primary">Crear rol</button>
        </div>
    </form>
    <table>
        <thead>
            <tr>
                <th>Nombre</th>
                <th>Descripción</th>
                <th>Acciones</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
</section>
"""


@router.get("/roles", response_class=None)
def roles_page(request: Request):
    ensure_default_roles()
    db = SessionLocal()
    try:
        roles = db.query(Rol).order_by(Rol.id.asc()).all()
    finally:
        db.close()
    return templates.TemplateResponse(
        "MAIN.html",
        {
            "request": request,
            "title": "Roles",
            "description": "Administra los roles del sistema.",
            "page_title": "Roles",
            "page_description": "Administra los roles del sistema.",
            "section_label": "",
            "section_title": "",
            "content": _roles_content(roles),
            "floating_actions_html": "",
            "floating_actions_screen": "personalization",
            "hide_floating_actions": True,
            "show_page_header": True,
            "colores": _get_colores_context(),
        },
    )


def _require_superadmin(request: Request) -> None:
    role = str(getattr(request.state, "user_role", "") or "").strip().lower()
    if not role:
        role = str(request.cookies.get("user_role") or "").strip().lower()
    role = unicodedata.normalize("NFKD", role)
    role = "".join(ch for ch in role if not unicodedata.combining(ch))
    role = re.sub(r"[^a-z0-9]+", "_", role).strip("_")
    if role in {"superadmin", "super_admin", "super_administrador", "superadministrador"}:
        role = "superadministrador"
    else:
        role = ROLE_ALIASES.get(role, role)
    if role != "superadministrador":
        raise HTTPException(status_code=403, detail="Acceso solo para superadministrador")


@router.get("/roles-sistema", response_class=HTMLResponse)
@router.get("/roles-permisos", response_class=HTMLResponse)
@router.get("/api/v1/personalizacion/roles-permisos", response_class=HTMLResponse)
@router.get("/personalizacion/roles-permisos", response_class=HTMLResponse)
def roles_permisos_page(request: Request):
    try:
        _require_superadmin(request)
    except HTTPException:
        return RedirectResponse(url="/roles", status_code=status.HTTP_303_SEE_OTHER)
    ensure_default_roles()
    db = SessionLocal()
    try:
        roles = db.query(Rol).order_by(Rol.id.asc()).all()
    finally:
        db.close()
    return templates.TemplateResponse(
        "MAIN.html",
        {
            "request": request,
            "title": "Roles y permisos",
            "description": "Gestión de roles y permisos",
            "page_title": "Roles y permisos",
            "page_description": "Gestión de roles y permisos",
            "section_label": "",
            "section_title": "",
            "content": _roles_content(roles),
            "floating_actions_html": "",
            "floating_actions_screen": "personalization",
            "hide_floating_actions": True,
            "show_page_header": True,
            "colores": _get_colores_context(),
        },
    )


@router.post("/roles/create")
def create_role(request: Request, nombre: str = Form(...), descripcion: str = Form("")):
    del request
    db = SessionLocal()
    try:
        db.add(Rol(nombre=nombre.strip(), descripcion=descripcion.strip()))
        db.commit()
    finally:
        db.close()
    return RedirectResponse(url="/roles", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/roles/edit/{role_id}")
def edit_role(request: Request, role_id: int, nombre: str = Form(...), descripcion: str = Form("")):
    del request
    db = SessionLocal()
    try:
        role = db.query(Rol).filter(Rol.id == role_id).first()
        if role:
            role.nombre = nombre.strip()
            role.descripcion = descripcion.strip()
            db.add(role)
            db.commit()
    finally:
        db.close()
    return RedirectResponse(url="/roles", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/roles/delete/{role_id}")
def delete_role(request: Request, role_id: int):
    del request
    db = SessionLocal()
    try:
        role = db.query(Rol).filter(Rol.id == role_id).first()
        if role:
            db.delete(role)
            db.commit()
    finally:
        db.close()
    return RedirectResponse(url="/roles", status_code=status.HTTP_303_SEE_OTHER)

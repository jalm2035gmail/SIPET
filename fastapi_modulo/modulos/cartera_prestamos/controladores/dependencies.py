from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .prestamos_menu import MODULE_MENU, MODULE_SUBDOMAINS, get_current_subdomain, get_module_subdomains


MODULE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = MODULE_DIR / "static"
TEMPLATES = Jinja2Templates(directory=str(MODULE_DIR / "vistas"))
RESUMEN_TEMPLATE_PATH = MODULE_DIR / "vistas" / "mesa_control.html"
GESTION_TEMPLATE_PATH = MODULE_DIR / "vistas" / "gestion.html"
RECUPERACION_TEMPLATE_PATH = MODULE_DIR / "vistas" / "recuperacion.html"
DEFAULT_LOGO_URL = "/modulos/cartera_prestamos/static/description/financiamiento.svg"
STATIC_BASE_URL = "/modulos/cartera_prestamos/static"

PAGE_STYLESHEETS = {
    "resumen": [f"{STATIC_BASE_URL}/css/cartera_mesa_control.css"],
    "gestion": [f"{STATIC_BASE_URL}/css/cartera_gestion.css"],
    "recuperacion": [f"{STATIC_BASE_URL}/css/cartera_recuperacion.css"],
}

PAGE_SCRIPTS = {
    "resumen": [f"{STATIC_BASE_URL}/js/mesa_control.js"],
    "gestion": [f"{STATIC_BASE_URL}/js/gestion.js"],
    "recuperacion": [f"{STATIC_BASE_URL}/js/recuperacion.js"],
}

SECTION_PERMISSION_KEYS = {
    "resumen": "view_resumen",
    "gestion": "view_gestion",
    "recuperacion": "view_recuperacion",
    "indicadores": "view_indicadores",
    "cobranza": "view_cobranza",
    "configuracion": "view_configuracion",
}

DEFAULT_SECTION_PERMISSIONS = {
    "view_resumen": False,
    "view_gestion": False,
    "view_recuperacion": False,
    "view_indicadores": False,
    "view_cobranza": False,
    "view_configuracion": False,
}

ROLE_PERMISSIONS = {
    "direccion_general": {key: True for key in DEFAULT_SECTION_PERMISSIONS},
    "gerente_credito": {
        "view_resumen": True,
        "view_gestion": True,
        "view_recuperacion": True,
        "view_indicadores": True,
        "view_cobranza": True,
        "view_configuracion": False,
    },
    "analista_cartera": {
        "view_resumen": True,
        "view_gestion": True,
        "view_recuperacion": False,
        "view_indicadores": True,
        "view_cobranza": False,
        "view_configuracion": False,
    },
    "supervisor_cobranza": {
        "view_resumen": True,
        "view_gestion": True,
        "view_recuperacion": True,
        "view_indicadores": True,
        "view_cobranza": True,
        "view_configuracion": False,
    },
    "gestor_cobranza": {
        "view_resumen": False,
        "view_gestion": False,
        "view_recuperacion": True,
        "view_indicadores": False,
        "view_cobranza": True,
        "view_configuracion": False,
    },
    "auditoria": {
        "view_resumen": True,
        "view_gestion": False,
        "view_recuperacion": False,
        "view_indicadores": True,
        "view_cobranza": False,
        "view_configuracion": False,
    },
    "configuracion": {
        "view_resumen": False,
        "view_gestion": False,
        "view_recuperacion": False,
        "view_indicadores": False,
        "view_cobranza": False,
        "view_configuracion": True,
    },
    "admin": {key: True for key in DEFAULT_SECTION_PERMISSIONS},
    "administrador": {key: True for key in DEFAULT_SECTION_PERMISSIONS},
    "superadmin": {key: True for key in DEFAULT_SECTION_PERMISSIONS},
}

MODULE_SECTIONS: dict[str, dict[str, Any]] = {
    "resumen": {
        "title": "Cartera ejecutiva",
        "description": "Mesa de control y seguimiento ejecutivo de cartera de préstamos.",
        "subdomain": "ejecutiva",
        "current_section": "resumen",
        "implemented": True,
        "template_path": RESUMEN_TEMPLATE_PATH,
        "stylesheets": PAGE_STYLESHEETS["resumen"],
        "scripts": PAGE_SCRIPTS["resumen"],
    },
    "mesa_control": {
        "title": "Cartera ejecutiva",
        "description": "Mesa de control y seguimiento ejecutivo de cartera de préstamos.",
        "subdomain": "ejecutiva",
        "current_section": "resumen",
        "implemented": True,
        "template_path": RESUMEN_TEMPLATE_PATH,
        "stylesheets": PAGE_STYLESHEETS["resumen"],
        "scripts": PAGE_SCRIPTS["resumen"],
    },
    "gestion": {
        "title": "Cartera operativa",
        "description": "Operación, seguimiento y control operativo de cartera de préstamos.",
        "subdomain": "operativa",
        "current_section": "gestion",
        "implemented": True,
        "template_path": GESTION_TEMPLATE_PATH,
        "stylesheets": PAGE_STYLESHEETS["gestion"],
        "scripts": PAGE_SCRIPTS["gestion"],
    },
    "recuperacion": {
        "title": "Cartera de cobranza",
        "description": "Cobranza, promesas de pago y recuperación operativa de cartera.",
        "subdomain": "cobranza",
        "current_section": "recuperacion",
        "implemented": True,
        "template_path": RECUPERACION_TEMPLATE_PATH,
        "stylesheets": PAGE_STYLESHEETS["recuperacion"],
        "scripts": PAGE_SCRIPTS["recuperacion"],
    },
    "indicadores_financieros": {
        "title": "Indicadores financieros",
        "description": "Indicadores financieros de cartera de préstamos.",
        "subdomain": "ejecutiva",
        "current_section": "indicadores",
        "implemented": False,
    },
    "dashboard_general": {
        "title": "Dashboard general",
        "description": "Dashboard general de cartera de préstamos.",
        "subdomain": "ejecutiva",
        "current_section": "resumen",
        "implemented": False,
    },
    "alertas_riesgos": {
        "title": "Alertas y riesgos",
        "description": "Alertas y riesgos de cartera de préstamos.",
        "subdomain": "ejecutiva",
        "current_section": "indicadores",
        "implemented": False,
    },
    "listado_creditos": {
        "title": "Listado de creditos",
        "description": "Listado de créditos de cartera de préstamos.",
        "subdomain": "operativa",
        "current_section": "gestion",
        "implemented": False,
    },
    "operacion_comercial": {
        "title": "Operacion comercial",
        "description": "Operación comercial de cartera de préstamos.",
        "subdomain": "operativa",
        "current_section": "gestion",
        "implemented": False,
    },
    "castigos": {
        "title": "Castigos",
        "description": "Gestión de castigos de cartera de préstamos.",
        "subdomain": "operativa",
        "current_section": "gestion",
        "implemented": False,
    },
    "reestructuracion": {
        "title": "Reestructuracion",
        "description": "Reestructuración de cartera de préstamos.",
        "subdomain": "operativa",
        "current_section": "gestion",
        "implemented": False,
    },
    "indicadores": {
        "title": "Indicadores",
        "description": "Indicadores de cartera de préstamos.",
        "subdomain": "ejecutiva",
        "current_section": "indicadores",
        "implemented": False,
    },
    "planeacion_estrategica": {
        "title": "Planeacion estrategica",
        "description": "Planeación estratégica de cartera de préstamos.",
        "subdomain": "ejecutiva",
        "current_section": "indicadores",
        "implemented": False,
    },
    "gobernanza": {
        "title": "Gobernanza",
        "description": "Gobernanza de cartera de préstamos.",
        "subdomain": "operativa",
        "current_section": "configuracion",
        "implemented": False,
    },
    "gestion_cobranza": {
        "title": "Gestion de cobranza",
        "description": "Gestión de cobranza de cartera de préstamos.",
        "subdomain": "cobranza",
        "current_section": "cobranza",
        "implemented": False,
    },
    "cartera_vencida": {
        "title": "Cartera vencida",
        "description": "Cartera vencida de cartera de préstamos.",
        "subdomain": "cobranza",
        "current_section": "cobranza",
        "implemented": False,
    },
    "promesas_pago": {
        "title": "Promesas de pago",
        "description": "Promesas de pago de cartera de préstamos.",
        "subdomain": "cobranza",
        "current_section": "cobranza",
        "implemented": False,
    },
    "visitas_gestiones": {
        "title": "Visitas y gestiones",
        "description": "Visitas y gestiones de cartera de préstamos.",
        "subdomain": "cobranza",
        "current_section": "cobranza",
        "implemented": False,
    },
    "configuracion": {
        "title": "Configuracion",
        "description": "Configuración de cartera de préstamos.",
        "subdomain": "operativa",
        "current_section": "configuracion",
        "implemented": False,
    },
}

def get_current_role_label(request: Request) -> str:
    role = get_current_role(request)
    if not role:
        return "Sesión activa"
    return role.replace("_", " ").title()


def get_current_user_name(request: Request) -> str:
    return str(getattr(request.state, "user_name", "") or request.cookies.get("user_name", "") or "").strip()


def get_current_role(request: Request) -> str:
    return str(getattr(request.state, "user_role", "") or request.cookies.get("user_role", "") or "").strip().lower()


def get_role_permissions(request: Request) -> dict[str, bool]:
    role = get_current_role(request)
    permissions = dict(DEFAULT_SECTION_PERMISSIONS)
    if not role:
        return permissions
    role_permissions = ROLE_PERMISSIONS.get(role)
    if role_permissions:
        permissions.update(role_permissions)
    return permissions


def has_section_access(request: Request, current_section: str) -> bool:
    permission_key = SECTION_PERMISSION_KEYS.get(current_section)
    if not permission_key:
        return False
    permissions = get_role_permissions(request)
    return bool(permissions.get(permission_key, False))


def require_any_section_access(request: Request) -> None:
    if any(get_role_permissions(request).values()):
        return
    raise HTTPException(status_code=403, detail="Acceso restringido al módulo Cartera de préstamos.")


def require_section_access(request: Request, current_section: str) -> None:
    if has_section_access(request, current_section):
        return
    raise HTTPException(status_code=403, detail="No tienes permisos para acceder a esta sección.")


def get_visible_module_menu(request: Request) -> list[dict[str, Any]]:
    permissions = get_role_permissions(request)
    visible_items = []
    for item in MODULE_MENU:
        permission_key = SECTION_PERMISSION_KEYS.get(item["key"])
        if permission_key and permissions.get(permission_key, False):
            visible_items.append(item)
    return visible_items

def get_visible_module_subdomains(request: Request) -> list[dict[str, Any]]:
    permissions = get_role_permissions(request)
    visible_subdomains = []
    for subdomain in get_module_subdomains():
        has_visible_section = False
        for section_key in subdomain["sections"]:
            section = MODULE_SECTIONS.get(section_key)
            if not section:
                continue
            permission_key = SECTION_PERMISSION_KEYS.get(section["current_section"])
            if permission_key and permissions.get(permission_key, False):
                has_visible_section = True
                break
        if has_visible_section:
            visible_subdomains.append(subdomain)
    return visible_subdomains

def render_module_layout(
    request: Request,
    *,
    title: str,
    description: str,
    content: str,
    current_section: str,
    current_subdomain: dict[str, Any] | None = None,
    extra_stylesheets: list[str] | None = None,
    extra_scripts: list[str] | None = None,
) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(
        "base.html",
        {
            "request": request,
            "title": title,
            "page_title": title,
            "description": description,
            "content": content,
            "current_section": current_section,
            "current_subdomain": current_subdomain or get_current_subdomain(current_section),
            "module_subdomains": get_visible_module_subdomains(request),
            "module_menu": get_visible_module_menu(request),
            "current_role_label": get_current_role_label(request),
            "user_name": get_current_user_name(request),
            "role_permissions": get_role_permissions(request),
            "extra_stylesheets": extra_stylesheets or [],
            "extra_scripts": extra_scripts or [],
        },
    )


def render_template_page(
    request: Request,
    *,
    path: Path,
    title: str,
    description: str,
    current_section: str,
    current_subdomain: dict[str, Any] | None = None,
) -> HTMLResponse:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return render_no_access(
            request,
            title=title,
            description=description,
            current_section=current_section,
        )
    return render_module_layout(
        request,
        title=title,
        description=description,
        content=content,
        current_section=current_section,
        current_subdomain=current_subdomain,
        extra_stylesheets=PAGE_STYLESHEETS.get(current_section, []),
        extra_scripts=PAGE_SCRIPTS.get(current_section, []),
    )


def get_section(section_key: str) -> dict[str, Any]:
    try:
        return MODULE_SECTIONS[section_key]
    except KeyError as exc:
        raise ValueError(f"Sección desconocida: {section_key}") from exc


def render_section_page(request: Request, section_key: str) -> HTMLResponse:
    section = get_section(section_key)
    current_subdomain = MODULE_SUBDOMAINS.get(section.get("subdomain", ""))
    if not has_section_access(request, section["current_section"]):
        return render_no_access(
            request,
            title=section["title"],
            description=section["description"],
            current_section=section["current_section"],
            current_subdomain=current_subdomain,
            message="Sin permisos para acceder a esta sección.",
        )
    if section["implemented"]:
        return render_template_page(
            request,
            path=section["template_path"],
            title=section["title"],
            description=section["description"],
            current_section=section["current_section"],
            current_subdomain=current_subdomain,
        )
    return render_no_access(
        request,
        title=section["title"],
        description=section["description"],
        current_section=section["current_section"],
        current_subdomain=current_subdomain,
    )


def render_no_access(
    request: Request,
    *,
    title: str,
    description: str,
    current_section: str,
    current_subdomain: dict[str, Any] | None = None,
    message: str = "Sin acceso, consulte con el administrador",
) -> HTMLResponse:
    safe_message = escape(message)
    content = f"""
    <section style="width:100%;min-height:58vh;background:#ffffff;border:1px solid rgba(148,163,184,.22);border-radius:28px;padding:30px;display:grid;gap:20px;box-shadow:0 18px 42px rgba(15,23,42,.08);">
        <div style="display:flex;align-items:center;gap:16px;">
            <div style="width:72px;height:72px;border-radius:22px;background:linear-gradient(135deg,#0f172a,#2563eb);display:grid;place-items:center;">
                <img src="{DEFAULT_LOGO_URL}" alt="" style="width:38px;height:38px;filter:brightness(0) invert(1);">
            </div>
            <div>
                <p style="margin:0;font-size:.84rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#64748b;">Cartera de préstamos</p>
                <h2 style="margin:6px 0 0;font-size:1.6rem;letter-spacing:-.03em;color:#0f172a;">{escape(title)}</h2>
            </div>
        </div>
        <div style="display:grid;place-items:center;min-height:300px;border:1px dashed rgba(148,163,184,.35);border-radius:24px;background:linear-gradient(180deg,rgba(248,250,252,.96),#ffffff);">
            <div style="text-align:center;max-width:640px;padding:20px;">
                <p style="margin:0 0 12px;color:#0f172a;font-size:2rem;font-weight:800;letter-spacing:-.03em;line-height:1.1;">{safe_message}</p>
                <p style="margin:0;color:#64748b;font-size:1rem;line-height:1.6;">Esta sección ya está registrada dentro del módulo, pero todavía no tiene acceso operativo o contenido habilitado.</p>
            </div>
        </div>
    </section>
    """
    return render_module_layout(
        request,
        title=title,
        description=description,
        content=content,
        current_section=current_section,
        current_subdomain=current_subdomain,
    )

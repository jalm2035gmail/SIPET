from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from fastapi_modulo.modulos.brujula.controladores.dependencies import render_backend_screen


router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent
BRUJULA_TEMPLATE_PATH = BASE_DIR / "vistas" / "brujula.html"
BRUJULA_MENU_TEMPLATE_PATH = BASE_DIR / "vistas" / "brujula_menu.html"
BRUJULA_INDICADORES_TEMPLATE_PATH = BASE_DIR / "vistas" / "brujula_indicadores.html"
BRUJULA_INDICADORES_PARTIALS_DIR = BASE_DIR / "vistas" / "partials"

BRUJULA_SECTIONS = {
    "dashboard": "Dashboard Ejecutivo",
    "solidez-financiera": "Solidez Financiera",
    "liquidez": "Liquidez",
    "rentabilidad": "Rentabilidad",
    "crecimiento": "Crecimiento",
    "liderazgo": "Liderazgo",
    "productividad": "Productividad",
    "balance-social": "Balance Social",
    "reportes": "Reportes",
    "configuracion": "Configuración",
    "indicadores": "Indicadores",
    "menu": "Menú BRUJULA",
}


def load_dashboard_template(section_title: str, section_description: str) -> str:
    try:
        template = BRUJULA_TEMPLATE_PATH.read_text(encoding="utf-8")
    except OSError:
        return f"<section><h2>{section_title}</h2><p>{section_description}</p></section>"
    return template.replace("{{ BRUJULA_SECTION_TITLE }}", section_title).replace("{{ BRUJULA_SECTION_DESCRIPTION }}", section_description)


def load_indicator_dashboard_template() -> str:
    try:
        template = BRUJULA_INDICADORES_TEMPLATE_PATH.read_text(encoding="utf-8")
    except OSError:
        return "<p>No se pudo cargar la vista de indicadores.</p>"
    replacements = {
        "{{ BRUJULA_INDICADORES_MATRIX }}": load_template_partial("indicadores_matrix.html"),
        "{{ BRUJULA_INDICADORES_ANALYSIS }}": load_template_partial("indicadores_analysis.html"),
        "{{ BRUJULA_INDICADORES_CATALOG }}": load_template_partial("indicadores_catalog.html"),
        "{{ BRUJULA_INDICADORES_ASSETS }}": (
            '<link rel="stylesheet" href="/static/css/brujula.css">\n'
            '<script src="/static/js/brujula.js"></script>'
        ),
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    return template


def load_menu_dashboard_template() -> str:
    try:
        return BRUJULA_MENU_TEMPLATE_PATH.read_text(encoding="utf-8")
    except OSError:
        return "<p>No se pudo cargar la vista del menú de BRUJULA.</p>"


def load_template_partial(filename: str) -> str:
    try:
        return (BRUJULA_INDICADORES_PARTIALS_DIR / filename).read_text(encoding="utf-8")
    except OSError:
        return ""

def build_section_description(section_title: str) -> str:
    if section_title == "Dashboard Ejecutivo":
        return "Visualiza en tiempo real la solidez financiera, la liquidez, la rentabilidad, el crecimiento y el balance social de la institución."
    return f"Visualiza el comportamiento de {section_title.lower()} dentro del tablero ejecutivo de BRUJULA."


def render_dashboard_page(request: Request, page_title: str, section_title: str, section_key: str):
    description = build_section_description(section_title)
    return render_backend_screen(
        request,
        title=page_title,
        description=description,
        content=load_dashboard_template(section_title, description).replace("{{ BRUJULA_SECTION_KEY }}", section_key),
        hide_floating_actions=True,
        show_page_header=False,
    )


def render_indicator_dashboard_page(request: Request):
    return render_backend_screen(
        request,
        title="BRUJULA - Indicadores",
        description="Gestión y seguimiento de indicadores clave de desempeño.",
        content=load_indicator_dashboard_template(),
        hide_floating_actions=True,
        show_page_header=False,
    )


def render_menu_dashboard_page(request: Request):
    return render_backend_screen(
        request,
        title="BRUJULA - Menú",
        description="Concentrado de accesos y menús del módulo BRUJULA.",
        content=load_menu_dashboard_template(),
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/brujula", response_class=HTMLResponse)
def brujula_page(request: Request):
    return render_dashboard_page(request, "BRUJULA", "Dashboard Ejecutivo", "dashboard")


@router.get("/brujula/{section}", response_class=HTMLResponse)
def brujula_section_page(request: Request, section: str):
    if section == "indicadores":
        return render_indicator_dashboard_page(request)
    if section == "menu":
        return render_menu_dashboard_page(request)
    section_title = BRUJULA_SECTIONS.get(section, section.replace("-", " ").title())
    return render_dashboard_page(request, f"BRUJULA - {section_title}", section_title, section)

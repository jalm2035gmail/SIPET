import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

BRUJULA_TEMPLATE_PATH = os.path.join(
    "fastapi_modulo", "modulos", "brujula", "brujula.html"
)

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
}


def _load_brujula_template(section_title: str, section_description: str) -> str:
    try:
        with open(BRUJULA_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            template = fh.read()
    except OSError:
        return (
            "<section>"
            f"<h2>{section_title}</h2>"
            f"<p>{section_description}</p>"
            "</section>"
        )
    return (
        template.replace("{{ BRUJULA_SECTION_TITLE }}", section_title)
        .replace("{{ BRUJULA_SECTION_DESCRIPTION }}", section_description)
    )


def _build_section_description(section_title: str) -> str:
    if section_title == "Dashboard Ejecutivo":
        return (
            "Visualiza en tiempo real la solidez financiera, la liquidez, la "
            "rentabilidad, el crecimiento y el balance social de la institución."
        )
    return (
        f"Visualiza el comportamiento de {section_title.lower()} dentro del tablero "
        "ejecutivo de BRUJULA."
    )


def _render_brujula_page(
    request: Request,
    page_title: str,
    section_title: str,
    section_key: str,
):
    from fastapi_modulo.main import render_backend_page

    description = _build_section_description(section_title)
    return render_backend_page(
        request,
        title=page_title,
        description=description,
        content=_load_brujula_template(section_title, description).replace(
            "{{ BRUJULA_SECTION_KEY }}", section_key
        ),
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/brujula", response_class=HTMLResponse)
def brujula_page(request: Request):
    return _render_brujula_page(
        request,
        "BRUJULA",
        "Dashboard Ejecutivo",
        "dashboard",
    )


@router.get("/brujula/{section}", response_class=HTMLResponse)
def brujula_section_page(request: Request, section: str):
    section_title = BRUJULA_SECTIONS.get(section, section.replace("-", " ").title())
    return _render_brujula_page(
        request,
        f"BRUJULA - {section_title}",
        section_title,
        section,
    )

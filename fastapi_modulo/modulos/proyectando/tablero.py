import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()
TABLERO_TEMPLATE_PATH = os.path.join("fastapi_modulo", "templates", "modulos", "proyectando", "tablero.html")


def _get_colores_context() -> dict:
    from fastapi_modulo.main import get_colores_context
    return get_colores_context()


@router.get("/proyectando", response_class=HTMLResponse)
def proyectando_page(request: Request):
    try:
        with open(TABLERO_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        content = "<p>No se pudo cargar la vista de Proyectando.</p>"
    return request.app.state.templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "title": "Proyectando",
            "description": "Herramienta de proyección financiera",
            "page_title": "Proyectando",
            "page_description": "Herramienta de proyección financiera",
            "section_label": "",
            "section_title": "",
            "content": content,
            "hide_floating_actions": True,
            "show_page_header": False,
            "view_buttons_html": "",
            "colores": _get_colores_context(),
        },
    )

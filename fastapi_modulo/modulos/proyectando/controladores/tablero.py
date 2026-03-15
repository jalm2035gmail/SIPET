from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()
MODULE_DIR = Path(__file__).resolve().parent.parent
TABLERO_TEMPLATE_PATH = MODULE_DIR / "vistas" / "tablero.html"


def _get_colores_context() -> dict:
    from fastapi_modulo.main import get_colores_context
    return get_colores_context()


@router.get("/proyectando", response_class=HTMLResponse)
def proyectando_page(request: Request):
    try:
        content = TABLERO_TEMPLATE_PATH.read_text(encoding="utf-8")
    except OSError:
        content = "<p>No se pudo cargar la vista de Proyectando.</p>"
    return request.app.state.templates.TemplateResponse(
        "MAIN.html",
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

import os
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()
NO_ACCESO_TEMPLATE_PATH = os.path.join("fastapi_modulo", "templates", "no_acceso.html")


def _get_colores_context() -> dict:
    from fastapi_modulo.main import get_colores_context
    return get_colores_context()


def _render_simple_no_access(request: Request, title: str):
    content = (
        '<section style="max-width:760px;margin:40px auto;padding:28px;border:1px solid #e2e8f0;'
        'border-radius:14px;background:#fff;">'
        '<h2 style="font-size:1.15rem;color:#0f172a;margin:0 0 10px;">Sin acceso</h2>'
        '<p style="margin:0;color:#334155;line-height:1.55;">'
        'Sin acceso, pongase en contacto con el administrador!'
        '</p>'
        '</section>'
    )
    return request.app.state.templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "title": title,
            "description": "Sin acceso",
            "page_title": title,
            "page_description": "Sin acceso",
            "section_label": "",
            "section_title": "",
            "content": content,
            "hide_floating_actions": True,
            "show_page_header": False,
            "view_buttons_html": "",
            "colores": _get_colores_context(),
        },
    )

@router.get("/proyectando/no-acceso", response_class=HTMLResponse)
def proyectando_no_acceso_page(request: Request):
    try:
        with open(NO_ACCESO_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        content = "<p>No hay acceso a esta sección.</p>"
    return request.app.state.templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "title": "No hay acceso",
            "description": "Acceso denegado a esta sección.",
            "page_title": "No hay acceso",
            "page_description": "Acceso denegado a esta sección.",
            "section_label": "",
            "section_title": "",
            "content": content,
            "hide_floating_actions": True,
            "show_page_header": False,
            "view_buttons_html": "",
            "colores": _get_colores_context(),
        },
    )


@router.get("/inteli-coop", response_class=HTMLResponse)
def inteli_coop_no_acceso_page(request: Request):
    return _render_simple_no_access(request, "Inteli-coop")


@router.get("/lider", response_class=HTMLResponse)
def lider_no_acceso_page(request: Request):
    return _render_simple_no_access(request, "BRUJULA")

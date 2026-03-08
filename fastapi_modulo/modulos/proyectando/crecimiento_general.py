import os

from fastapi import APIRouter, Body, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi_modulo.modulos.proyectando.data_store import (
    load_crecimiento_general_activo_total_editor,
    load_crecimiento_general_resumen,
    save_crecimiento_general_activo_total_growth,
)

router = APIRouter()
CRECIMIENTO_GENERAL_TEMPLATE_PATH = os.path.join(
    "fastapi_modulo", "templates", "modulos", "proyectando", "crecimiento_general.html"
)


def _get_colores_context() -> dict:
    from fastapi_modulo.main import get_colores_context
    return get_colores_context()


@router.get("/proyectando/crecimiento-general", response_class=HTMLResponse)
def proyectando_crecimiento_general_page(request: Request):
    try:
        with open(CRECIMIENTO_GENERAL_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        content = "<p>No se pudo cargar la vista de crecimiento general.</p>"
    return request.app.state.templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "title": "Crecimiento general",
            "description": "",
            "page_title": "Crecimiento general",
            "page_description": "",
            "section_label": "",
            "section_title": "",
            "content": content,
            "hide_floating_actions": True,
            "show_page_header": False,
            "view_buttons_html": "",
            "colores": _get_colores_context(),
        },
    )


@router.get("/api/proyectando/crecimiento-general/resumen")
async def obtener_crecimiento_general_resumen():
    return {"success": True, "data": load_crecimiento_general_resumen()}


@router.get("/api/proyectando/crecimiento-general/activo-total")
async def obtener_crecimiento_general_activo_total():
    return {"success": True, "data": load_crecimiento_general_activo_total_editor()}


@router.post("/api/proyectando/crecimiento-general/activo-total")
async def guardar_crecimiento_general_activo_total(data: dict = Body(...)):
    payload = data if isinstance(data, dict) else {}
    growth_map = payload.get("growth_map", {})
    if not isinstance(growth_map, dict):
        growth_map = {}
    return {"success": True, "data": save_crecimiento_general_activo_total_growth(growth_map)}


@router.get("/proyectando/crecimiento-general/activo-total", response_class=HTMLResponse)
def proyectando_crecimiento_activo_total_page(request: Request):
    return RedirectResponse(url="/proyectando/crecimiento-general", status_code=307)

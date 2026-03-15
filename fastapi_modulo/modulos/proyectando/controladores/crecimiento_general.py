from pathlib import Path

from fastapi import APIRouter, Body, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi_modulo.modulos.proyectando.modelos.data_store import (
    load_crecimiento_general_activo_total_editor,
    load_crecimiento_general_resumen,
    save_crecimiento_general_financiamiento_standards,
    save_crecimiento_general_activo_total_growth,
)

router = APIRouter()
MODULE_DIR = Path(__file__).resolve().parent.parent
CRECIMIENTO_GENERAL_TEMPLATE_PATH = MODULE_DIR / "vistas" / "crecimiento_general.html"
CRECIMIENTO_GENERAL_JS_PATH = MODULE_DIR / "static" / "js" / "crecimiento_general.js"


def _get_colores_context() -> dict:
    from fastapi_modulo.main import get_colores_context
    return get_colores_context()


@router.get("/modulos/proyectando/crecimiento_general.js")
def proyectando_crecimiento_general_js():
    try:
        content = CRECIMIENTO_GENERAL_JS_PATH.read_text(encoding="utf-8")
    except OSError:
        content = "console.error('No se pudo cargar crecimiento_general.js');"
    return HTMLResponse(content=content, media_type="application/javascript")


@router.get("/proyectando/crecimiento-general", response_class=HTMLResponse)
def proyectando_crecimiento_general_page(request: Request):
    try:
        content = CRECIMIENTO_GENERAL_TEMPLATE_PATH.read_text(encoding="utf-8")
    except OSError:
        content = "<p>No se pudo cargar la vista de crecimiento general.</p>"
    return request.app.state.templates.TemplateResponse(
        "MAIN.html",
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


@router.post("/api/proyectando/crecimiento-general/financiamiento-activo")
async def guardar_crecimiento_general_financiamiento_activo(data: dict = Body(...)):
    payload = data if isinstance(data, dict) else {}
    standards = payload.get("standards", {})
    pasivo_pct_map = payload.get("pasivo_pct_map", {})
    resultado_pct_map = payload.get("resultado_pct_map", {})
    if not isinstance(standards, dict):
        standards = {}
    if not isinstance(pasivo_pct_map, dict):
        pasivo_pct_map = {}
    if not isinstance(resultado_pct_map, dict):
        resultado_pct_map = {}
    return {"success": True, "data": save_crecimiento_general_financiamiento_standards(standards, pasivo_pct_map, resultado_pct_map)}


@router.get("/proyectando/crecimiento-general/activo-total", response_class=HTMLResponse)
def proyectando_crecimiento_activo_total_page(request: Request):
    return RedirectResponse(url="/proyectando/crecimiento-general", status_code=307)

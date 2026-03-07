from __future__ import annotations

import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter()

BASE_TEMPLATE_PATH = os.path.join("fastapi_modulo", "templates", "modulos", "control_interno")


def _bind_core_symbols() -> None:
    if globals().get("_CORE_BOUND"):
        return
    from fastapi_modulo import main as core
    globals()["render_backend_page"] = getattr(core, "render_backend_page")
    globals()["_CORE_BOUND"] = True


def _load_template(filename: str) -> str:
    path = os.path.join(BASE_TEMPLATE_PATH, filename)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return "<p>No se pudo cargar la vista.</p>"


# ── Página ────────────────────────────────────────────────────────────────────

@router.get("/control-interno/tablero", response_class=HTMLResponse)
def tablero_page(request: Request):
    _bind_core_symbols()
    return render_backend_page(
        request,
        title="Tablero de control interno",
        description="Indicadores clave de desempeño del sistema de control interno COSO",
        content=_load_template("tablero.html"),
        hide_floating_actions=True,
        show_page_header=False,
    )


# ── API: KPIs globales ────────────────────────────────────────────────────────

@router.get("/api/ci-tablero")
def api_tablero():
    from fastapi_modulo.modulos.control_interno.tablero_store import resumen_global
    return JSONResponse(resumen_global())


@router.get("/api/ci-tablero/controles")
def api_kpi_controles():
    from fastapi_modulo.modulos.control_interno.tablero_store import kpi_controles
    return JSONResponse(kpi_controles())


@router.get("/api/ci-tablero/programa")
def api_kpi_programa():
    from fastapi_modulo.modulos.control_interno.tablero_store import kpi_programa
    return JSONResponse(kpi_programa())


@router.get("/api/ci-tablero/evidencias")
def api_kpi_evidencias():
    from fastapi_modulo.modulos.control_interno.tablero_store import kpi_evidencias
    return JSONResponse(kpi_evidencias())


@router.get("/api/ci-tablero/hallazgos")
def api_kpi_hallazgos():
    from fastapi_modulo.modulos.control_interno.tablero_store import kpi_hallazgos
    return JSONResponse(kpi_hallazgos())

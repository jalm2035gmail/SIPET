from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse

from fastapi_modulo.modulos.control_interno.controladores.utils import render_module_page, static_dir

static_router = APIRouter()
control_pages_router = APIRouter()
tablero_pages_router = APIRouter()
programa_pages_router = APIRouter()
evidencia_pages_router = APIRouter()
hallazgos_pages_router = APIRouter()
reportes_pages_router = APIRouter()


@static_router.get("/modulos/control_interno/static/{asset_path:path}")
def control_interno_static(asset_path: str):
    root = static_dir().resolve()
    target = (root / Path(asset_path)).resolve()
    if not str(target).startswith(str(root)) or not target.is_file():
        raise HTTPException(status_code=404, detail="Recurso no encontrado.")
    return FileResponse(target)


@control_pages_router.get("/control-interno", response_class=HTMLResponse)
def control_page(request: Request):
    return render_module_page(
        request,
        title="Control interno",
        description="Catalogo de controles internos - Componentes COSO",
        template_name="control.html",
    )


@tablero_pages_router.get("/control-interno/tablero", response_class=HTMLResponse)
def tablero_page(request: Request):
    return render_module_page(
        request,
        title="Tablero de control interno",
        description="Indicadores clave de desempeno del sistema de control interno COSO",
        template_name="tablero.html",
    )


@programa_pages_router.get("/control-interno/programa-anual", response_class=HTMLResponse)
def programa_page(request: Request):
    return render_module_page(
        request,
        title="Programa anual de control",
        description="Planificacion y seguimiento de actividades de control interno - COSO",
        template_name="programa.html",
    )


@evidencia_pages_router.get("/control-interno/evidencias", response_class=HTMLResponse)
def evidencia_page(request: Request):
    return render_module_page(
        request,
        title="Evidencias de control",
        description="Registro documental de la ejecucion y evaluacion de controles internos",
        template_name="evidencia.html",
    )


@hallazgos_pages_router.get("/control-interno/hallazgos", response_class=HTMLResponse)
def hallazgos_page(request: Request):
    return render_module_page(
        request,
        title="Hallazgos y acciones correctivas",
        description="Registro y seguimiento de hallazgos COSO con sus acciones correctivas",
        template_name="hallazgos.html",
    )


@reportes_pages_router.get("/control-interno/reportes", response_class=HTMLResponse)
def reportes_page(request: Request):
    return render_module_page(
        request,
        title="Reportes de control interno",
        description="Generacion y exportacion de reportes del sistema de control interno COSO",
        template_name="reportes_ci.html",
    )


__all__ = [
    "control_pages_router",
    "evidencia_pages_router",
    "hallazgos_pages_router",
    "programa_pages_router",
    "reportes_pages_router",
    "static_router",
    "tablero_pages_router",
]

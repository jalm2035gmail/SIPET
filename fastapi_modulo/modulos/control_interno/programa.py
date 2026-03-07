from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
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

@router.get("/control-interno/programa-anual", response_class=HTMLResponse)
def programa_anual_page(request: Request):
    _bind_core_symbols()
    return render_backend_page(
        request,
        title="Programa anual de control",
        description="Planificación y seguimiento de actividades de control interno — COSO",
        content=_load_template("programa.html"),
        hide_floating_actions=True,
        show_page_header=False,
    )


# ── API: Programas ────────────────────────────────────────────────────────────

@router.get("/api/ci-programa")
def api_listar_programas(anio: Optional[int] = None):
    from fastapi_modulo.modulos.control_interno.programa_store import listar_programas
    return JSONResponse({"programas": listar_programas(anio=anio)})


@router.get("/api/ci-programa/{programa_id}")
def api_obtener_programa(programa_id: int):
    from fastapi_modulo.modulos.control_interno.programa_store import obtener_programa
    p = obtener_programa(programa_id)
    if not p:
        raise HTTPException(status_code=404, detail="Programa no encontrado.")
    return JSONResponse(p)


@router.post("/api/ci-programa")
async def api_crear_programa(request: Request):
    from fastapi_modulo.modulos.control_interno.programa_store import crear_programa
    data = await request.json()
    if not data.get("anio") or not data.get("nombre"):
        raise HTTPException(status_code=422, detail="Los campos año y nombre son obligatorios.")
    try:
        return JSONResponse(crear_programa(data), status_code=201)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/api/ci-programa/{programa_id}")
async def api_actualizar_programa(programa_id: int, request: Request):
    from fastapi_modulo.modulos.control_interno.programa_store import actualizar_programa
    data = await request.json()
    updated = actualizar_programa(programa_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Programa no encontrado.")
    return JSONResponse(updated)


@router.delete("/api/ci-programa/{programa_id}")
def api_eliminar_programa(programa_id: int):
    from fastapi_modulo.modulos.control_interno.programa_store import eliminar_programa
    if not eliminar_programa(programa_id):
        raise HTTPException(status_code=404, detail="Programa no encontrado.")
    return JSONResponse({"ok": True})


# ── API: Actividades ──────────────────────────────────────────────────────────

@router.get("/api/ci-programa/{programa_id}/actividades")
def api_listar_actividades(programa_id: int, estado: Optional[str] = None):
    from fastapi_modulo.modulos.control_interno.programa_store import (
        listar_actividades, resumen_programa
    )
    acts    = listar_actividades(programa_id=programa_id, estado=estado)
    resumen = resumen_programa(programa_id)
    return JSONResponse({"actividades": acts, "resumen": resumen})


@router.get("/api/ci-programa/{programa_id}/actividades/{actividad_id}")
def api_obtener_actividad(programa_id: int, actividad_id: int):
    from fastapi_modulo.modulos.control_interno.programa_store import obtener_actividad
    a = obtener_actividad(actividad_id)
    if not a or a["programa_id"] != programa_id:
        raise HTTPException(status_code=404, detail="Actividad no encontrada.")
    return JSONResponse(a)


@router.post("/api/ci-programa/{programa_id}/actividades")
async def api_crear_actividad(programa_id: int, request: Request):
    from fastapi_modulo.modulos.control_interno.programa_store import crear_actividad
    data = await request.json()
    try:
        return JSONResponse(crear_actividad(programa_id, data), status_code=201)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/api/ci-programa/{programa_id}/actividades/{actividad_id}")
async def api_actualizar_actividad(programa_id: int, actividad_id: int, request: Request):
    from fastapi_modulo.modulos.control_interno.programa_store import actualizar_actividad
    data = await request.json()
    updated = actualizar_actividad(actividad_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Actividad no encontrada.")
    return JSONResponse(updated)


@router.delete("/api/ci-programa/{programa_id}/actividades/{actividad_id}")
def api_eliminar_actividad(programa_id: int, actividad_id: int):
    from fastapi_modulo.modulos.control_interno.programa_store import eliminar_actividad
    if not eliminar_actividad(actividad_id):
        raise HTTPException(status_code=404, detail="Actividad no encontrada.")
    return JSONResponse({"ok": True})

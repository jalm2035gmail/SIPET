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
        return "<p>No se pudo cargar la vista de control interno.</p>"


# ── Página ────────────────────────────────────────────────────────────────────

@router.get("/control-interno", response_class=HTMLResponse)
def control_interno_page(request: Request):
    _bind_core_symbols()
    return render_backend_page(
        request,
        title="Control interno",
        description="Catálogo de controles internos — Componentes COSO",
        content=_load_template("control.html"),
        hide_floating_actions=True,
        show_page_header=False,
    )


# ── API ───────────────────────────────────────────────────────────────────────

@router.get("/api/control-interno")
def api_listar(
    componente: Optional[str] = None,
    area:       Optional[str] = None,
    estado:     Optional[str] = None,
    q:          Optional[str] = None,
):
    from fastapi_modulo.modulos.control_interno.store import listar_controles
    controles = listar_controles(componente=componente, area=area, estado=estado)
    if q:
        q_lower = q.lower()
        controles = [
            c for c in controles
            if q_lower in (c.get("codigo") or "").lower()
            or q_lower in (c.get("nombre") or "").lower()
            or q_lower in (c.get("area") or "").lower()
        ]
    return JSONResponse({"controles": controles})


@router.get("/api/control-interno/{control_id}")
def api_obtener(control_id: int):
    from fastapi_modulo.modulos.control_interno.store import obtener_control
    control = obtener_control(control_id)
    if not control:
        raise HTTPException(status_code=404, detail="Control no encontrado.")
    return JSONResponse(control)


@router.post("/api/control-interno")
async def api_crear(request: Request):
    from fastapi_modulo.modulos.control_interno.store import crear_control
    data = await request.json()
    if not data.get("codigo") or not data.get("nombre") or not data.get("componente") or not data.get("area"):
        raise HTTPException(status_code=422, detail="Los campos código, nombre, componente y área son obligatorios.")
    try:
        nuevo = crear_control(data)
        return JSONResponse(nuevo, status_code=201)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/api/control-interno/{control_id}")
async def api_actualizar(control_id: int, request: Request):
    from fastapi_modulo.modulos.control_interno.store import actualizar_control
    data = await request.json()
    actualizado = actualizar_control(control_id, data)
    if not actualizado:
        raise HTTPException(status_code=404, detail="Control no encontrado.")
    return JSONResponse(actualizado)


@router.delete("/api/control-interno/{control_id}")
def api_eliminar(control_id: int):
    from fastapi_modulo.modulos.control_interno.store import eliminar_control
    ok = eliminar_control(control_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Control no encontrado.")
    return JSONResponse({"ok": True})


@router.get("/api/control-interno-opciones")
def api_opciones():
    from fastapi_modulo.modulos.control_interno.store import opciones_filtro
    return JSONResponse(opciones_filtro())

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

@router.get("/control-interno/hallazgos", response_class=HTMLResponse)
def hallazgos_page(request: Request):
    _bind_core_symbols()
    return render_backend_page(
        request,
        title="Hallazgos y acciones correctivas",
        description="Registro y seguimiento de hallazgos COSO con sus acciones correctivas",
        content=_load_template("hallazgos.html"),
        hide_floating_actions=True,
        show_page_header=False,
    )


# ── API: Hallazgos ────────────────────────────────────────────────────────────

@router.get("/api/ci-hallazgo")
def api_listar(
    nivel_riesgo:    Optional[str] = None,
    estado:          Optional[str] = None,
    control_id:      Optional[int] = None,
    componente_coso: Optional[str] = None,
    q:               Optional[str] = None,
):
    from fastapi_modulo.modulos.control_interno.hallazgo_store import (
        listar_hallazgos, resumen_hallazgos,
    )
    lista   = listar_hallazgos(nivel_riesgo=nivel_riesgo, estado=estado,
                               control_id=control_id, componente_coso=componente_coso, q=q)
    resumen = resumen_hallazgos()
    return JSONResponse({"hallazgos": lista, "resumen": resumen})


@router.get("/api/ci-hallazgo/{hallazgo_id}")
def api_obtener(hallazgo_id: int):
    from fastapi_modulo.modulos.control_interno.hallazgo_store import obtener_hallazgo
    h = obtener_hallazgo(hallazgo_id)
    if not h:
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado.")
    return JSONResponse(h)


@router.post("/api/ci-hallazgo")
async def api_crear(request: Request):
    data = await request.json()
    if not (data.get("titulo") or "").strip():
        raise HTTPException(status_code=422, detail="El título es obligatorio.")
    from fastapi_modulo.modulos.control_interno.hallazgo_store import crear_hallazgo
    return JSONResponse(crear_hallazgo(data), status_code=201)


@router.put("/api/ci-hallazgo/{hallazgo_id}")
async def api_actualizar(hallazgo_id: int, request: Request):
    data = await request.json()
    from fastapi_modulo.modulos.control_interno.hallazgo_store import actualizar_hallazgo
    h = actualizar_hallazgo(hallazgo_id, data)
    if not h:
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado.")
    return JSONResponse(h)


@router.delete("/api/ci-hallazgo/{hallazgo_id}")
def api_eliminar(hallazgo_id: int):
    from fastapi_modulo.modulos.control_interno.hallazgo_store import eliminar_hallazgo
    if not eliminar_hallazgo(hallazgo_id):
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado.")
    return JSONResponse({"ok": True})


# ── API: Acciones correctivas ─────────────────────────────────────────────────

@router.get("/api/ci-hallazgo/{hallazgo_id}/acciones")
def api_listar_acciones(hallazgo_id: int):
    from fastapi_modulo.modulos.control_interno.hallazgo_store import (
        obtener_hallazgo, listar_acciones,
    )
    if not obtener_hallazgo(hallazgo_id):
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado.")
    return JSONResponse(listar_acciones(hallazgo_id))


@router.post("/api/ci-hallazgo/{hallazgo_id}/acciones")
async def api_crear_accion(hallazgo_id: int, request: Request):
    data = await request.json()
    if not (data.get("descripcion") or "").strip():
        raise HTTPException(status_code=422, detail="La descripción de la acción es obligatoria.")
    from fastapi_modulo.modulos.control_interno.hallazgo_store import (
        obtener_hallazgo, crear_accion,
    )
    if not obtener_hallazgo(hallazgo_id):
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado.")
    return JSONResponse(crear_accion(hallazgo_id, data), status_code=201)


@router.put("/api/ci-hallazgo/{hallazgo_id}/acciones/{accion_id}")
async def api_actualizar_accion(hallazgo_id: int, accion_id: int, request: Request):
    data = await request.json()
    from fastapi_modulo.modulos.control_interno.hallazgo_store import actualizar_accion
    a = actualizar_accion(accion_id, data)
    if not a:
        raise HTTPException(status_code=404, detail="Acción correctiva no encontrada.")
    return JSONResponse(a)


@router.delete("/api/ci-hallazgo/{hallazgo_id}/acciones/{accion_id}")
def api_eliminar_accion(hallazgo_id: int, accion_id: int):
    from fastapi_modulo.modulos.control_interno.hallazgo_store import eliminar_accion
    if not eliminar_accion(accion_id):
        raise HTTPException(status_code=404, detail="Acción correctiva no encontrada.")
    return JSONResponse({"ok": True})

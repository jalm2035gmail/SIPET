from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from fastapi_modulo.modulos.control_interno.modelos.schemas import (
    AccionCorrectivaCreate,
    AccionCorrectivaUpdate,
    HallazgoCreate,
    HallazgoUpdate,
)
from fastapi_modulo.modulos.control_interno.servicios import hallazgo_service

router = APIRouter()


@router.get("/api/ci-hallazgo")
def api_listar(
    nivel_riesgo: Optional[str] = None,
    estado: Optional[str] = None,
    control_id: Optional[int] = None,
    componente_coso: Optional[str] = None,
    q: Optional[str] = None,
):
    return JSONResponse({
        "hallazgos": hallazgo_service.listar_service(
            nivel_riesgo=nivel_riesgo,
            estado=estado,
            control_id=control_id,
            componente_coso=componente_coso,
            q=q,
        ),
        "resumen": hallazgo_service.resumen_service(),
    })


@router.get("/api/ci-hallazgo/{hallazgo_id}")
def api_obtener(hallazgo_id: int):
    item = hallazgo_service.obtener_service(hallazgo_id)
    if not item:
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado.")
    return JSONResponse(item)


@router.post("/api/ci-hallazgo")
def api_crear(payload: HallazgoCreate):
    return JSONResponse(hallazgo_service.crear_service(payload.dict()), status_code=201)


@router.put("/api/ci-hallazgo/{hallazgo_id}")
def api_actualizar(hallazgo_id: int, payload: HallazgoUpdate):
    item = hallazgo_service.actualizar_service(hallazgo_id, payload.dict(exclude_unset=True))
    if not item:
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado.")
    return JSONResponse(item)


@router.delete("/api/ci-hallazgo/{hallazgo_id}")
def api_eliminar(hallazgo_id: int):
    if not hallazgo_service.eliminar_service(hallazgo_id):
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado.")
    return JSONResponse({"ok": True})


@router.get("/api/ci-hallazgo/{hallazgo_id}/acciones")
def api_listar_acciones(hallazgo_id: int):
    if not hallazgo_service.obtener_service(hallazgo_id):
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado.")
    return JSONResponse(hallazgo_service.listar_acciones_service(hallazgo_id))


@router.post("/api/ci-hallazgo/{hallazgo_id}/acciones")
def api_crear_accion(hallazgo_id: int, payload: AccionCorrectivaCreate):
    if not hallazgo_service.obtener_service(hallazgo_id):
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado.")
    return JSONResponse(hallazgo_service.crear_accion_service(hallazgo_id, payload.dict()), status_code=201)


@router.put("/api/ci-hallazgo/{hallazgo_id}/acciones/{accion_id}")
def api_actualizar_accion(hallazgo_id: int, accion_id: int, payload: AccionCorrectivaUpdate):
    item = hallazgo_service.actualizar_accion_service(accion_id, payload.dict(exclude_unset=True))
    if not item:
        raise HTTPException(status_code=404, detail="Accion correctiva no encontrada.")
    return JSONResponse(item)


@router.delete("/api/ci-hallazgo/{hallazgo_id}/acciones/{accion_id}")
def api_eliminar_accion(hallazgo_id: int, accion_id: int):
    if not hallazgo_service.eliminar_accion_service(accion_id):
        raise HTTPException(status_code=404, detail="Accion correctiva no encontrada.")
    return JSONResponse({"ok": True})


__all__ = ["router"]

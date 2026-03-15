from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from fastapi_modulo.modulos.control_interno.modelos.schemas import ControlInternoCreate, ControlInternoUpdate
from fastapi_modulo.modulos.control_interno.servicios import controles_service

router = APIRouter()


@router.get("/api/control-interno")
def api_listar(componente: Optional[str] = None, area: Optional[str] = None, estado: Optional[str] = None, q: Optional[str] = None):
    return JSONResponse({"controles": controles_service.listar(componente=componente, area=area, estado=estado, q=q)})


@router.get("/api/control-interno/{control_id}")
def api_obtener(control_id: int):
    control = controles_service.obtener(control_id)
    if not control:
        raise HTTPException(status_code=404, detail="Control no encontrado.")
    return JSONResponse(control)


@router.post("/api/control-interno")
def api_crear(payload: ControlInternoCreate):
    return JSONResponse(controles_service.crear(payload.dict()), status_code=201)


@router.put("/api/control-interno/{control_id}")
def api_actualizar(control_id: int, payload: ControlInternoUpdate):
    updated = controles_service.actualizar(control_id, payload.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Control no encontrado.")
    return JSONResponse(updated)


@router.delete("/api/control-interno/{control_id}")
def api_eliminar(control_id: int):
    if not controles_service.eliminar(control_id):
        raise HTTPException(status_code=404, detail="Control no encontrado.")
    return JSONResponse({"ok": True})


@router.get("/api/control-interno-opciones")
def api_opciones():
    return JSONResponse(controles_service.opciones())


__all__ = ["router"]

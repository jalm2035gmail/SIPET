from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from fastapi_modulo.modulos.control_interno.modelos.schemas import (
    ProgramaActividadCreate,
    ProgramaActividadUpdate,
    ProgramaCreate,
    ProgramaUpdate,
)
from fastapi_modulo.modulos.control_interno.servicios import programa_service

router = APIRouter()


@router.get("/api/ci-programa")
def api_listar_programas(anio: Optional[int] = None):
    return JSONResponse({"programas": programa_service.listar_programas_service(anio=anio)})


@router.get("/api/ci-programa/{programa_id}")
def api_obtener_programa(programa_id: int):
    item = programa_service.obtener_programa_service(programa_id)
    if not item:
        raise HTTPException(status_code=404, detail="Programa no encontrado.")
    return JSONResponse(item)


@router.post("/api/ci-programa")
def api_crear_programa(payload: ProgramaCreate):
    return JSONResponse(programa_service.crear_programa_service(payload.dict()), status_code=201)


@router.put("/api/ci-programa/{programa_id}")
def api_actualizar_programa(programa_id: int, payload: ProgramaUpdate):
    item = programa_service.actualizar_programa_service(programa_id, payload.dict(exclude_unset=True))
    if not item:
        raise HTTPException(status_code=404, detail="Programa no encontrado.")
    return JSONResponse(item)


@router.delete("/api/ci-programa/{programa_id}")
def api_eliminar_programa(programa_id: int):
    if not programa_service.eliminar_programa_service(programa_id):
        raise HTTPException(status_code=404, detail="Programa no encontrado.")
    return JSONResponse({"ok": True})


@router.get("/api/ci-programa/{programa_id}/actividades")
def api_listar_actividades(programa_id: int, estado: Optional[str] = None):
    return JSONResponse({
        "actividades": programa_service.listar_actividades_service(programa_id, estado=estado),
        "resumen": programa_service.resumen_programa_service(programa_id),
    })


@router.get("/api/ci-programa/{programa_id}/actividades/{actividad_id}")
def api_obtener_actividad(programa_id: int, actividad_id: int):
    item = programa_service.obtener_actividad_service(actividad_id)
    if not item or item["programa_id"] != programa_id:
        raise HTTPException(status_code=404, detail="Actividad no encontrada.")
    return JSONResponse(item)


@router.post("/api/ci-programa/{programa_id}/actividades")
def api_crear_actividad(programa_id: int, payload: ProgramaActividadCreate):
    return JSONResponse(programa_service.crear_actividad_service(programa_id, payload.dict()), status_code=201)


@router.put("/api/ci-programa/{programa_id}/actividades/{actividad_id}")
def api_actualizar_actividad(programa_id: int, actividad_id: int, payload: ProgramaActividadUpdate):
    item = programa_service.actualizar_actividad_service(actividad_id, payload.dict(exclude_unset=True))
    if not item or item["programa_id"] != programa_id:
        raise HTTPException(status_code=404, detail="Actividad no encontrada.")
    return JSONResponse(item)


@router.delete("/api/ci-programa/{programa_id}/actividades/{actividad_id}")
def api_eliminar_actividad(programa_id: int, actividad_id: int):
    if not programa_service.eliminar_actividad_service(actividad_id):
        raise HTTPException(status_code=404, detail="Actividad no encontrada.")
    return JSONResponse({"ok": True})


__all__ = ["router"]

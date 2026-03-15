from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from fastapi_modulo.modulos.control_interno.servicios import tablero_service

router = APIRouter()


@router.get("/api/ci-tablero")
def api_tablero(
    area: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
):
    return JSONResponse(tablero_service.resumen_global_service(area=area, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta))


@router.get("/api/ci-tablero/controles")
def api_kpi_controles(
    area: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
):
    return JSONResponse(tablero_service.kpi_controles_service(area=area, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta))


@router.get("/api/ci-tablero/programa")
def api_kpi_programa(
    area: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
):
    return JSONResponse(tablero_service.kpi_programa_service(area=area, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta))


@router.get("/api/ci-tablero/evidencias")
def api_kpi_evidencias(
    area: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
):
    return JSONResponse(tablero_service.kpi_evidencias_service(area=area, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta))


@router.get("/api/ci-tablero/hallazgos")
def api_kpi_hallazgos(
    area: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
):
    return JSONResponse(tablero_service.kpi_hallazgos_service(area=area, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta))


__all__ = ["router"]

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from fastapi_modulo.modulos.control_interno.servicios import tablero_service

router = APIRouter()


@router.get("/api/ci-tablero")
def api_tablero():
    return JSONResponse(tablero_service.resumen_global_service())


@router.get("/api/ci-tablero/controles")
def api_kpi_controles():
    return JSONResponse(tablero_service.kpi_controles_service())


@router.get("/api/ci-tablero/programa")
def api_kpi_programa():
    return JSONResponse(tablero_service.kpi_programa_service())


@router.get("/api/ci-tablero/evidencias")
def api_kpi_evidencias():
    return JSONResponse(tablero_service.kpi_evidencias_service())


@router.get("/api/ci-tablero/hallazgos")
def api_kpi_hallazgos():
    return JSONResponse(tablero_service.kpi_hallazgos_service())


__all__ = ["router"]

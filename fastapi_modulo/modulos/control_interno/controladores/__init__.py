from fastapi_modulo.modulos.control_interno.controladores.control import router as control_router
from fastapi_modulo.modulos.control_interno.controladores.evidencia import router as evidencia_router
from fastapi_modulo.modulos.control_interno.controladores.hallazgos import router as hallazgos_router
from fastapi_modulo.modulos.control_interno.controladores.programa import router as programa_router
from fastapi_modulo.modulos.control_interno.controladores.reportes_ci import router as reportes_router
from fastapi_modulo.modulos.control_interno.controladores.tablero import router as tablero_router

__all__ = [
    "control_router",
    "evidencia_router",
    "hallazgos_router",
    "programa_router",
    "reportes_router",
    "tablero_router",
]

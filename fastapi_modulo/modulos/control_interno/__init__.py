from fastapi import APIRouter

from fastapi_modulo.modulos.control_interno.control_interno_menu import (
    MODULE_MENU,
    MENU_BY_KEY,
    build_menu_context,
    get_default_menu_item,
    get_menu_item,
    get_menu_item_by_href,
    list_menu_items,
    resolve_menu_key,
)
from fastapi_modulo.modulos.control_interno.controladores.control import router as control_router
from fastapi_modulo.modulos.control_interno.controladores.evidencia import router as evidencia_router
from fastapi_modulo.modulos.control_interno.controladores.hallazgos import router as hallazgos_router
from fastapi_modulo.modulos.control_interno.controladores.programa import router as programa_router
from fastapi_modulo.modulos.control_interno.controladores.reportes_ci import router as reportes_router
from fastapi_modulo.modulos.control_interno.controladores.tablero import router as tablero_router

router = APIRouter()
router.include_router(control_router)
router.include_router(programa_router)
router.include_router(evidencia_router)
router.include_router(hallazgos_router)
router.include_router(tablero_router)
router.include_router(reportes_router)

__all__ = [
    "MODULE_MENU",
    "MENU_BY_KEY",
    "build_menu_context",
    "get_default_menu_item",
    "get_menu_item",
    "get_menu_item_by_href",
    "list_menu_items",
    "resolve_menu_key",
    "router",
]

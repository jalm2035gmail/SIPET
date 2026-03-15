from fastapi import APIRouter, Depends

from fastapi_modulo.modulos.activo_fijo.controladores.api import router as api_router
from fastapi_modulo.modulos.activo_fijo.controladores.dependencies import (
    require_activo_fijo_access,
)
from fastapi_modulo.modulos.activo_fijo.controladores.pages import router as pages_router

router = APIRouter(dependencies=[Depends(require_activo_fijo_access)])
router.include_router(pages_router)
router.include_router(api_router)

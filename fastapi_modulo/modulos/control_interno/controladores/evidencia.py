from fastapi import APIRouter, Depends

from fastapi_modulo.modulos.control_interno.controladores.api_evidencias import router as api_router
from fastapi_modulo.modulos.control_interno.controladores.dependencies import bind_tenant_context
from fastapi_modulo.modulos.control_interno.controladores.pages import evidencia_pages_router

router = APIRouter()
router.include_router(evidencia_pages_router, dependencies=[Depends(bind_tenant_context)])
router.include_router(api_router, dependencies=[Depends(bind_tenant_context)])

__all__ = ["router"]

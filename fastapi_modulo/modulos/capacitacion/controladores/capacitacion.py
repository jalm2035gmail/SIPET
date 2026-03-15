"""Router ensamblador del modulo de capacitacion."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from fastapi_modulo.modulos.capacitacion.controladores.api_auditoria import router as api_auditoria_router
from fastapi_modulo.modulos.capacitacion.controladores.api_certificados import router as api_certificados_router
from fastapi_modulo.modulos.capacitacion.controladores.api_cursos import router as api_cursos_router
from fastapi_modulo.modulos.capacitacion.controladores.api_evaluaciones import router as api_evaluaciones_router
from fastapi_modulo.modulos.capacitacion.controladores.api_gamificacion import router as api_gamificacion_router
from fastapi_modulo.modulos.capacitacion.controladores.api_inscripciones import router as api_inscripciones_router
from fastapi_modulo.modulos.capacitacion.controladores.api_presentaciones import router as api_presentaciones_router
from fastapi_modulo.modulos.capacitacion.controladores.dependencies import require_access
from fastapi_modulo.modulos.capacitacion.modelos.cap_db_models import ensure_capacitacion_tenant_schema
from fastapi_modulo.modulos.capacitacion.controladores.pages import router as pages_router

ensure_capacitacion_tenant_schema()

router = APIRouter(dependencies=[Depends(require_access)])
router.include_router(pages_router)
router.include_router(api_auditoria_router)
router.include_router(api_cursos_router)
router.include_router(api_inscripciones_router)
router.include_router(api_evaluaciones_router)
router.include_router(api_gamificacion_router)
router.include_router(api_presentaciones_router)
router.include_router(api_certificados_router)

__all__ = ["router"]

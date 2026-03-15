"""API de certificados."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from fastapi_modulo.modulos.capacitacion.controladores.dependencies import current_user_key, get_current_tenant
from fastapi_modulo.modulos.capacitacion.servicios.certificados_service import (
    get_certificado,
    get_certificado_por_folio,
    get_certificados_colaborador,
)

router = APIRouter()


@router.get("/api/capacitacion/certificados/{cert_id}")
def api_get_certificado(cert_id: int, request: Request):
    obj = get_certificado(cert_id, tenant_id=get_current_tenant(request))
    if not obj:
        raise HTTPException(status_code=404, detail="Certificado no encontrado")
    return JSONResponse(obj)


@router.get("/api/capacitacion/verificar/{folio}")
def api_verificar_certificado(folio: str, request: Request):
    obj = get_certificado_por_folio(folio, tenant_id=get_current_tenant(request))
    if not obj:
        raise HTTPException(status_code=404, detail="Certificado no encontrado")
    return JSONResponse(obj)


@router.get("/api/capacitacion/mis-certificados")
def api_mis_certificados(request: Request):
    return JSONResponse(get_certificados_colaborador(current_user_key(request), tenant_id=get_current_tenant(request)))


__all__ = ["router"]

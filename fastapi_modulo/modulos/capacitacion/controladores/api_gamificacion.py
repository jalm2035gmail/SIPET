"""API de gamificacion."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from fastapi_modulo.modulos.capacitacion.controladores.dependencies import current_user_key, get_current_tenant, is_admin_or_superadmin
from fastapi_modulo.modulos.capacitacion.servicios.gamificacion_service import (
    actualizar_insignia,
    crear_insignia,
    eliminar_insignia,
    get_insignias_disponibles,
    get_metas_departamento,
    get_mis_insignias,
    get_perfil_gamificacion,
    get_ranking,
)

router = APIRouter()


class InsigniaIn(BaseModel):
    nombre: str = Field(..., max_length=100)
    descripcion: Optional[str] = None
    icono_emoji: Optional[str] = Field("🏅", max_length=10)
    condicion_tipo: str = Field(..., max_length=50)
    condicion_valor: int = Field(1, ge=1)
    color: Optional[str] = Field("#2563eb", max_length=30)
    orden: int = Field(0, ge=0)


class InsigniaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=100)
    descripcion: Optional[str] = None
    icono_emoji: Optional[str] = Field(None, max_length=10)
    condicion_tipo: Optional[str] = Field(None, max_length=50)
    condicion_valor: Optional[int] = Field(None, ge=1)
    color: Optional[str] = Field(None, max_length=30)
    orden: Optional[int] = Field(None, ge=0)


@router.get("/api/capacitacion/gamificacion/perfil")
def api_gam_perfil(request: Request):
    return JSONResponse(get_perfil_gamificacion(current_user_key(request), tenant_id=get_current_tenant(request)))


@router.get("/api/capacitacion/gamificacion/ranking")
def api_gam_ranking(request: Request, limit: int = 10, scope: str = "empresa", value: str = "", season: str = "actual"):
    return JSONResponse(get_ranking(min(limit, 50), tenant_id=get_current_tenant(request), scope=scope or "empresa", value=value or None, season=season or "actual"))


@router.get("/api/capacitacion/gamificacion/metas-departamento")
def api_gam_metas_departamento(request: Request):
    if not is_admin_or_superadmin(request):
        raise HTTPException(status_code=403, detail="Solo administradores")
    return JSONResponse(get_metas_departamento(tenant_id=get_current_tenant(request)))


@router.get("/api/capacitacion/gamificacion/insignias")
def api_gam_insignias(request: Request):
    return JSONResponse(get_insignias_disponibles(tenant_id=get_current_tenant(request)))


@router.post("/api/capacitacion/gamificacion/insignias", status_code=201)
def api_gam_crear_insignia(request: Request, body: InsigniaIn):
    if not is_admin_or_superadmin(request):
        raise HTTPException(status_code=403, detail="Solo administradores")
    return JSONResponse(crear_insignia(body.model_dump(), tenant_id=get_current_tenant(request)), status_code=201)


@router.put("/api/capacitacion/gamificacion/insignias/{insignia_id}")
def api_gam_actualizar_insignia(insignia_id: int, request: Request, body: InsigniaUpdate):
    if not is_admin_or_superadmin(request):
        raise HTTPException(status_code=403, detail="Solo administradores")
    obj = actualizar_insignia(insignia_id, body.model_dump(exclude_none=True), tenant_id=get_current_tenant(request))
    if not obj:
        raise HTTPException(status_code=404, detail="Insignia no encontrada")
    return JSONResponse(obj)


@router.delete("/api/capacitacion/gamificacion/insignias/{insignia_id}")
def api_gam_eliminar_insignia(insignia_id: int, request: Request):
    if not is_admin_or_superadmin(request):
        raise HTTPException(status_code=403, detail="Solo administradores")
    if not eliminar_insignia(insignia_id, tenant_id=get_current_tenant(request)):
        raise HTTPException(status_code=404, detail="Insignia no encontrada")
    return JSONResponse({"ok": True})


@router.get("/api/capacitacion/gamificacion/mis-insignias")
def api_gam_mis_insignias(request: Request):
    return JSONResponse(get_mis_insignias(current_user_key(request), tenant_id=get_current_tenant(request)))


__all__ = ["router"]

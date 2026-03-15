"""API de auditoria por entidad."""
from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from fastapi_modulo.modulos.capacitacion.controladores.dependencies import get_current_tenant
from fastapi_modulo.modulos.capacitacion.servicios.audit_service import list_eventos

router = APIRouter()

AUDIT_ENTITY_TYPES = {"curso", "presentacion", "evaluacion", "certificado"}


@router.get("/api/capacitacion/auditoria/{entidad_tipo}/{entidad_id}")
def api_auditoria_entidad(
    entidad_tipo: str,
    entidad_id: int,
    request: Request,
    limit: int = Query(50, ge=1, le=200),
):
    _ = get_current_tenant(request)
    entity_type = str(entidad_tipo or "").strip().lower()
    if entity_type not in AUDIT_ENTITY_TYPES:
        return JSONResponse({"detail": "Tipo de entidad no soportado"}, status_code=400)
    rows = list_eventos(entity_type, entidad_id)
    return JSONResponse(
        {
            "entidad_tipo": entity_type,
            "entidad_id": entidad_id,
            "total": len(rows),
            "items": rows[:limit],
        }
    )


__all__ = ["router"]

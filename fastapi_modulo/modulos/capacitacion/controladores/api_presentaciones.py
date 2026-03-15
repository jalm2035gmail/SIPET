"""API de presentaciones, diapositivas y elementos."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from fastapi_modulo.modulos.capacitacion.controladores.dependencies import current_session_name, current_user_key, get_current_tenant
from fastapi_modulo.modulos.capacitacion.modelos.cap_presentacion_service import (
    create_diapositiva,
    create_asset,
    create_presentacion,
    create_version_snapshot,
    delete_diapositiva,
    delete_presentacion,
    duplicate_elemento,
    duplicate_diapositiva,
    get_presentacion,
    get_templates,
    list_assets,
    list_diapositivas,
    list_elementos,
    list_presentaciones,
    list_versiones,
    reordenar_diapositivas,
    save_elementos,
    update_diapositiva,
    update_presentacion,
)
from fastapi_modulo.modulos.capacitacion.servicios.archivos_service import save_upload

router = APIRouter()


def _actor_meta(request: Request) -> tuple[str | None, str | None]:
    try:
        return current_user_key(request), current_session_name(request) or None
    except HTTPException:
        return current_session_name(request) or None, current_session_name(request) or None


@router.get("/api/capacitacion/presentaciones")
def api_pres_list(request: Request, estado: Optional[str] = None, curso_id: Optional[int] = None):
    tenant_id = get_current_tenant(request)
    try:
        autor_key = current_user_key(request)
    except HTTPException:
        autor_key = None
    return JSONResponse(list_presentaciones(tenant_id=tenant_id, autor_key=autor_key, estado=estado, curso_id=curso_id))


@router.post("/api/capacitacion/presentaciones")
async def api_pres_create(request: Request):
    tenant_id = get_current_tenant(request)
    data = await request.json()
    actor_key, actor_name = _actor_meta(request)
    autor_key = actor_key
    data["autor_key"] = autor_key
    try:
        pres = create_presentacion(data, tenant_id=tenant_id, actor_key=actor_key, actor_name=actor_name)
        return JSONResponse(pres, status_code=201)
    except Exception as exc:
        return JSONResponse({"error": str(exc) or "Error al crear la presentación."}, status_code=500)


@router.get("/api/capacitacion/presentaciones/{pres_id}")
def api_pres_get(pres_id: int, request: Request):
    pres = get_presentacion(pres_id, tenant_id=get_current_tenant(request))
    if not pres:
        return JSONResponse({"error": "No encontrado"}, status_code=404)
    return JSONResponse(pres)


@router.get("/api/capacitacion/presentaciones/templates")
def api_pres_templates():
    return JSONResponse(get_templates())


@router.put("/api/capacitacion/presentaciones/{pres_id}")
async def api_pres_update(pres_id: int, request: Request):
    data = await request.json()
    actor_key, actor_name = _actor_meta(request)
    pres = update_presentacion(pres_id, data, tenant_id=get_current_tenant(request), actor_key=actor_key, actor_name=actor_name)
    if not pres:
        return JSONResponse({"error": "No encontrado"}, status_code=404)
    return JSONResponse(pres)


@router.get("/api/capacitacion/presentaciones/{pres_id}/versiones")
def api_pres_versions(pres_id: int):
    return JSONResponse(list_versiones(pres_id))


@router.post("/api/capacitacion/presentaciones/{pres_id}/versiones")
def api_pres_create_version(pres_id: int, request: Request):
    actor_key, _actor_name = _actor_meta(request)
    version = create_version_snapshot(pres_id, actor_key=actor_key)
    if not version:
        return JSONResponse({"error": "No encontrado"}, status_code=404)
    return JSONResponse(version, status_code=201)


@router.get("/api/capacitacion/presentaciones/{pres_id}/assets")
def api_pres_assets(pres_id: int, asset_type: Optional[str] = None):
    return JSONResponse(list_assets(pres_id, asset_type))


@router.post("/api/capacitacion/presentaciones/{pres_id}/assets")
async def api_pres_assets_create(pres_id: int, request: Request):
    data = await request.json()
    actor_key, _actor_name = _actor_meta(request)
    return JSONResponse(create_asset(data, pres_id=pres_id, tenant_id=get_current_tenant(request), actor_key=actor_key), status_code=201)


@router.post("/api/capacitacion/presentaciones/{pres_id}/assets/upload", status_code=201)
async def api_pres_assets_upload(pres_id: int, request: Request, archivo: UploadFile = File(...), tipo: str = "imagen"):
    actor_key, _actor_name = _actor_meta(request)
    saved = save_upload(archivo, categoria=tipo, tenant_id=get_current_tenant(request), entidad_tipo="presentacion", entidad_id=pres_id, actor_key=actor_key)
    asset = create_asset(
        {
            "nombre": saved["nombre_original"],
            "tipo": tipo,
            "url": saved["public_url"],
            "metadata": {"archivo_id": saved["id"], "mime_type": saved["mime_type"], "size_bytes": saved["size_bytes"]},
        },
        pres_id=pres_id,
        tenant_id=get_current_tenant(request),
        actor_key=actor_key,
    )
    return JSONResponse(asset, status_code=201)


@router.delete("/api/capacitacion/presentaciones/{pres_id}")
def api_pres_delete(pres_id: int, request: Request):
    actor_key, actor_name = _actor_meta(request)
    delete_presentacion(pres_id, tenant_id=get_current_tenant(request), actor_key=actor_key, actor_name=actor_name)
    return JSONResponse({"ok": True})


@router.get("/api/capacitacion/presentaciones/{pres_id}/diapositivas")
def api_diap_list(pres_id: int, request: Request):
    return JSONResponse(list_diapositivas(pres_id, tenant_id=get_current_tenant(request)))


@router.post("/api/capacitacion/presentaciones/{pres_id}/diapositivas")
async def api_diap_create(pres_id: int, request: Request):
    data = await request.json()
    actor_key, actor_name = _actor_meta(request)
    return JSONResponse(create_diapositiva(pres_id, data, tenant_id=get_current_tenant(request), actor_key=actor_key, actor_name=actor_name), status_code=201)


@router.put("/api/capacitacion/presentaciones/{pres_id}/reordenar")
async def api_pres_reordenar(pres_id: int, request: Request):
    data = await request.json()
    actor_key, actor_name = _actor_meta(request)
    reordenar_diapositivas(pres_id, data.get("orden_ids", []), tenant_id=get_current_tenant(request), actor_key=actor_key, actor_name=actor_name)
    return JSONResponse({"ok": True})


@router.put("/api/capacitacion/diapositivas/{diap_id}")
async def api_diap_update(diap_id: int, request: Request):
    data = await request.json()
    actor_key, actor_name = _actor_meta(request)
    diap = update_diapositiva(diap_id, data, tenant_id=get_current_tenant(request), actor_key=actor_key, actor_name=actor_name)
    if not diap:
        return JSONResponse({"error": "No encontrado"}, status_code=404)
    return JSONResponse(diap)


@router.delete("/api/capacitacion/diapositivas/{diap_id}")
def api_diap_delete(diap_id: int, request: Request):
    actor_key, actor_name = _actor_meta(request)
    delete_diapositiva(diap_id, tenant_id=get_current_tenant(request), actor_key=actor_key, actor_name=actor_name)
    return JSONResponse({"ok": True})


@router.post("/api/capacitacion/diapositivas/{diap_id}/duplicar")
def api_diap_duplicar(diap_id: int, request: Request):
    actor_key, actor_name = _actor_meta(request)
    diap = duplicate_diapositiva(diap_id, tenant_id=get_current_tenant(request), actor_key=actor_key, actor_name=actor_name)
    if not diap:
        return JSONResponse({"error": "No encontrado"}, status_code=404)
    return JSONResponse(diap, status_code=201)


@router.get("/api/capacitacion/diapositivas/{diap_id}/elementos")
def api_el_list(diap_id: int, request: Request):
    return JSONResponse(list_elementos(diap_id, tenant_id=get_current_tenant(request)))


@router.put("/api/capacitacion/diapositivas/{diap_id}/elementos")
async def api_el_save(diap_id: int, request: Request):
    data = await request.json()
    actor_key, actor_name = _actor_meta(request)
    save_elementos(diap_id, data.get("elementos", []), tenant_id=get_current_tenant(request), actor_key=actor_key, actor_name=actor_name, autosave=bool(data.get("autosave")))
    return JSONResponse({"ok": True})


@router.post("/api/capacitacion/diapositivas/{diap_id}/elementos/{element_id}/duplicar")
def api_el_duplicate(diap_id: int, element_id: int, request: Request):
    actor_key, actor_name = _actor_meta(request)
    obj = duplicate_elemento(diap_id, element_id, actor_key=actor_key, actor_name=actor_name)
    if not obj:
        return JSONResponse({"error": "No encontrado"}, status_code=404)
    return JSONResponse(obj, status_code=201)


__all__ = ["router"]

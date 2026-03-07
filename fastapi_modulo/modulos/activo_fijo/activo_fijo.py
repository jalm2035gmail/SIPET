from __future__ import annotations

import os
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlalchemy.exc import IntegrityError

from fastapi_modulo.modulos.activo_fijo.af_models import (
    ActivoCreate,
    ActivoUpdate,
    AsignacionCreate,
    AsignacionUpdate,
    BajaCreate,
    DepreciarRequest,
    MantenimientoCreate,
    MantenimientoUpdate,
)
from fastapi_modulo.modulos.activo_fijo.af_store import (
    create_activo,
    create_asignacion,
    create_baja,
    create_mantenimiento,
    delete_activo,
    delete_asignacion,
    delete_baja,
    delete_depreciacion,
    delete_mantenimiento,
    depreciar_activo,
    get_activo,
    get_af_resumen,
    list_activos,
    list_asignaciones,
    list_bajas,
    list_depreciaciones,
    list_mantenimientos,
    update_activo,
    update_asignacion,
    update_mantenimiento,
)

_MODULE_DIR = os.path.dirname(__file__)


def _require_activo_fijo_access(request: Request) -> None:
    from fastapi_modulo.main import is_admin_or_superadmin, _get_user_app_access
    if is_admin_or_superadmin(request):
        return
    if "ActivoFijo" in _get_user_app_access(request):
        return
    raise HTTPException(status_code=403, detail="Acceso restringido al módulo Activo Fijo")


router = APIRouter(dependencies=[Depends(_require_activo_fijo_access)])


# ── Vista HTML ────────────────────────────────────────────────────────────────

@router.get("/activo-fijo", response_class=HTMLResponse)
def activo_fijo_page(request: Request):
    from fastapi_modulo.main import render_backend_page
    html_path = os.path.join(_MODULE_DIR, "activo_fijo.html")
    with open(html_path, encoding="utf-8") as f:
        content = f.read()
    return render_backend_page(
        request,
        title="Gestión de Activo Fijo",
        description="Depreciaciones, asignaciones, mantenimiento y bajas de activos.",
        content=content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/api/activo-fijo/assets/activo_fijo.js")
def activo_fijo_js():
    js_path = os.path.join(_MODULE_DIR, "activo_fijo.js")
    with open(js_path, encoding="utf-8") as f:
        content = f.read()
    return Response(content=content, media_type="application/javascript")


# ── Resumen / KPIs ────────────────────────────────────────────────────────────

@router.get("/api/activo-fijo/resumen")
def api_resumen():
    return get_af_resumen()


# ── Activos ───────────────────────────────────────────────────────────────────

@router.get("/api/activo-fijo/activos")
def api_list_activos(
    estado: Optional[str] = Query(default=None),
    categoria: Optional[str] = Query(default=None),
):
    return list_activos(estado=estado, categoria=categoria)


@router.get("/api/activo-fijo/activos/{activo_id}")
def api_get_activo(activo_id: int):
    obj = get_activo(activo_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Activo no encontrado")
    return obj


@router.post("/api/activo-fijo/activos", status_code=201)
def api_create_activo(body: ActivoCreate):
    try:
        return create_activo(body.model_dump(exclude_none=True))
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Ya existe un activo con ese código")


@router.put("/api/activo-fijo/activos/{activo_id}")
def api_update_activo(activo_id: int, body: ActivoUpdate):
    try:
        obj = update_activo(activo_id, body.model_dump(exclude_none=True))
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Código duplicado")
    if not obj:
        raise HTTPException(status_code=404, detail="Activo no encontrado")
    return obj


@router.delete("/api/activo-fijo/activos/{activo_id}", status_code=204)
def api_delete_activo(activo_id: int):
    if not delete_activo(activo_id):
        raise HTTPException(status_code=404, detail="Activo no encontrado")


# ── Depreciación ──────────────────────────────────────────────────────────────

@router.post("/api/activo-fijo/activos/{activo_id}/depreciar", status_code=201)
def api_depreciar(activo_id: int, body: DepreciarRequest):
    try:
        return depreciar_activo(
            activo_id=activo_id,
            periodo=body.periodo,
            tasa_sd=body.tasa_saldo_decreciente,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Ya existe una depreciación registrada para ese activo y periodo",
        )


@router.get("/api/activo-fijo/depreciaciones")
def api_list_depreciaciones(
    activo_id: Optional[int] = Query(default=None),
    periodo: Optional[str] = Query(default=None),
):
    return list_depreciaciones(activo_id=activo_id, periodo=periodo)


@router.delete("/api/activo-fijo/depreciaciones/{dep_id}", status_code=204)
def api_delete_depreciacion(dep_id: int):
    if not delete_depreciacion(dep_id):
        raise HTTPException(status_code=404, detail="Depreciación no encontrada")


# ── Asignaciones ──────────────────────────────────────────────────────────────

@router.get("/api/activo-fijo/asignaciones")
def api_list_asignaciones(
    activo_id: Optional[int] = Query(default=None),
    estado: Optional[str] = Query(default=None),
):
    return list_asignaciones(activo_id=activo_id, estado=estado)


@router.post("/api/activo-fijo/asignaciones", status_code=201)
def api_create_asignacion(body: AsignacionCreate):
    return create_asignacion(body.model_dump(exclude_none=True))


@router.put("/api/activo-fijo/asignaciones/{asig_id}")
def api_update_asignacion(asig_id: int, body: AsignacionUpdate):
    obj = update_asignacion(asig_id, body.model_dump(exclude_none=True))
    if not obj:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    return obj


@router.delete("/api/activo-fijo/asignaciones/{asig_id}", status_code=204)
def api_delete_asignacion(asig_id: int):
    if not delete_asignacion(asig_id):
        raise HTTPException(status_code=404, detail="Asignación no encontrada")


# ── Mantenimientos ────────────────────────────────────────────────────────────

@router.get("/api/activo-fijo/mantenimientos")
def api_list_mantenimientos(
    activo_id: Optional[int] = Query(default=None),
    estado: Optional[str] = Query(default=None),
):
    return list_mantenimientos(activo_id=activo_id, estado=estado)


@router.post("/api/activo-fijo/mantenimientos", status_code=201)
def api_create_mantenimiento(body: MantenimientoCreate):
    return create_mantenimiento(body.model_dump(exclude_none=True))


@router.put("/api/activo-fijo/mantenimientos/{mant_id}")
def api_update_mantenimiento(mant_id: int, body: MantenimientoUpdate):
    obj = update_mantenimiento(mant_id, body.model_dump(exclude_none=True))
    if not obj:
        raise HTTPException(status_code=404, detail="Mantenimiento no encontrado")
    return obj


@router.delete("/api/activo-fijo/mantenimientos/{mant_id}", status_code=204)
def api_delete_mantenimiento(mant_id: int):
    if not delete_mantenimiento(mant_id):
        raise HTTPException(status_code=404, detail="Mantenimiento no encontrado")


# ── Bajas ─────────────────────────────────────────────────────────────────────

@router.get("/api/activo-fijo/bajas")
def api_list_bajas():
    return list_bajas()


@router.post("/api/activo-fijo/bajas", status_code=201)
def api_create_baja(body: BajaCreate):
    try:
        return create_baja(body.model_dump(exclude_none=True))
    except IntegrityError:
        raise HTTPException(
            status_code=409, detail="El activo ya tiene un registro de baja"
        )


@router.delete("/api/activo-fijo/bajas/{baja_id}", status_code=204)
def api_delete_baja(baja_id: int):
    if not delete_baja(baja_id):
        raise HTTPException(status_code=404, detail="Baja no encontrada")

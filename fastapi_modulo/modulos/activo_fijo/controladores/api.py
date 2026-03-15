from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import IntegrityError

from fastapi_modulo.modulos.activo_fijo.schemas import (
    ActivoCreate,
    ActivoUpdate,
    AsignacionCreate,
    AsignacionUpdate,
    BajaCreate,
    DepreciarRequest,
    MantenimientoCreate,
    MantenimientoUpdate,
)
from fastapi_modulo.modulos.activo_fijo.service import (
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

router = APIRouter()


@router.get("/api/activo-fijo/resumen")
def api_resumen():
    return get_af_resumen()


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


@router.post("/api/activo-fijo/activos/{activo_id}/depreciar", status_code=201)
def api_depreciar(activo_id: int, body: DepreciarRequest):
    try:
        return depreciar_activo(
            activo_id=activo_id,
            periodo=body.periodo,
            tasa_sd=body.tasa_saldo_decreciente,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
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


@router.get("/api/activo-fijo/bajas")
def api_list_bajas():
    return list_bajas()


@router.post("/api/activo-fijo/bajas", status_code=201)
def api_create_baja(body: BajaCreate):
    try:
        return create_baja(body.model_dump(exclude_none=True))
    except IntegrityError:
        raise HTTPException(status_code=409, detail="El activo ya tiene un registro de baja")


@router.delete("/api/activo-fijo/bajas/{baja_id}", status_code=204)
def api_delete_baja(baja_id: int):
    if not delete_baja(baja_id):
        raise HTTPException(status_code=404, detail="Baja no encontrada")

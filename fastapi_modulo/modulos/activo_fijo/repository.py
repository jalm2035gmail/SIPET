from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import func

from fastapi_modulo.db import MAIN, SessionLocal, engine
from fastapi_modulo.modulos.activo_fijo.enums import EstadoActivo
from fastapi_modulo.modulos.activo_fijo.models import (
    AfActivo,
    AfAsignacion,
    AfBaja,
    AfDepreciacion,
    AfMantenimiento,
)

AF_TABLES = [
    AfActivo.__table__,
    AfDepreciacion.__table__,
    AfAsignacion.__table__,
    AfMantenimiento.__table__,
    AfBaja.__table__,
]


def ensure_schema() -> None:
    MAIN.metadata.create_all(bind=engine, tables=AF_TABLES, checkfirst=True)


def get_db():
    return SessionLocal()

def list_activos(db, estado: Optional[str] = None, categoria: Optional[str] = None) -> List[AfActivo]:
    query = db.query(AfActivo)
    if estado:
        query = query.filter(AfActivo.estado == estado)
    if categoria:
        query = query.filter(AfActivo.categoria == categoria)
    return query.order_by(AfActivo.id.desc()).all()


def get_activo(db, activo_id: int) -> Optional[AfActivo]:
    return db.query(AfActivo).filter(AfActivo.id == activo_id).first()


def create_activo(db, data: Dict[str, Any]) -> AfActivo:
    obj = AfActivo(**data)
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return obj


def update_activo(db, obj: AfActivo, data: Dict[str, Any]) -> AfActivo:
    for key, value in data.items():
        setattr(obj, key, value)
    db.flush()
    db.refresh(obj)
    return obj


def delete_record(db, obj) -> None:
    db.delete(obj)
    db.flush()


def get_depreciacion(db, dep_id: int) -> Optional[AfDepreciacion]:
    return db.query(AfDepreciacion).filter(AfDepreciacion.id == dep_id).first()


def get_depreciacion_by_periodo(db, activo_id: int, periodo: str) -> Optional[AfDepreciacion]:
    return (
        db.query(AfDepreciacion)
        .filter(AfDepreciacion.activo_id == activo_id, AfDepreciacion.periodo == periodo)
        .first()
    )


def list_depreciaciones(
    db,
    activo_id: Optional[int] = None,
    periodo: Optional[str] = None,
) -> List[AfDepreciacion]:
    query = db.query(AfDepreciacion)
    if activo_id:
        query = query.filter(AfDepreciacion.activo_id == activo_id)
    if periodo:
        query = query.filter(AfDepreciacion.periodo == periodo)
    return query.order_by(AfDepreciacion.id.desc()).all()


def create_depreciacion(db, data: Dict[str, Any]) -> AfDepreciacion:
    obj = AfDepreciacion(**data)
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return obj


def get_asignacion(db, asig_id: int) -> Optional[AfAsignacion]:
    return db.query(AfAsignacion).filter(AfAsignacion.id == asig_id).first()


def list_asignaciones(
    db,
    activo_id: Optional[int] = None,
    estado: Optional[str] = None,
) -> List[AfAsignacion]:
    query = db.query(AfAsignacion)
    if activo_id:
        query = query.filter(AfAsignacion.activo_id == activo_id)
    if estado:
        query = query.filter(AfAsignacion.estado == estado)
    return query.order_by(AfAsignacion.id.desc()).all()


def create_asignacion(db, data: Dict[str, Any]) -> AfAsignacion:
    obj = AfAsignacion(**data)
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return obj


def update_asignacion(db, obj: AfAsignacion, data: Dict[str, Any]) -> AfAsignacion:
    for key, value in data.items():
        setattr(obj, key, value)
    db.flush()
    db.refresh(obj)
    return obj


def get_mantenimiento(db, mant_id: int) -> Optional[AfMantenimiento]:
    return db.query(AfMantenimiento).filter(AfMantenimiento.id == mant_id).first()


def list_mantenimientos(
    db,
    activo_id: Optional[int] = None,
    estado: Optional[str] = None,
) -> List[AfMantenimiento]:
    query = db.query(AfMantenimiento)
    if activo_id:
        query = query.filter(AfMantenimiento.activo_id == activo_id)
    if estado:
        query = query.filter(AfMantenimiento.estado == estado)
    return query.order_by(AfMantenimiento.id.desc()).all()


def create_mantenimiento(db, data: Dict[str, Any]) -> AfMantenimiento:
    obj = AfMantenimiento(**data)
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return obj


def update_mantenimiento(db, obj: AfMantenimiento, data: Dict[str, Any]) -> AfMantenimiento:
    for key, value in data.items():
        setattr(obj, key, value)
    db.flush()
    db.refresh(obj)
    return obj


def get_baja(db, baja_id: int) -> Optional[AfBaja]:
    return db.query(AfBaja).filter(AfBaja.id == baja_id).first()


def list_bajas(db) -> List[AfBaja]:
    return db.query(AfBaja).order_by(AfBaja.id.desc()).all()


def create_baja(db, data: Dict[str, Any]) -> AfBaja:
    obj = AfBaja(**data)
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return obj


def count_activos(db) -> int:
    return db.query(AfActivo).count()


def count_activos_by_estado(db, estado: str) -> int:
    return db.query(AfActivo).filter(AfActivo.estado == estado).count()


def sum_valor_libro_activos(db):
    return (
        db.query(func.sum(AfActivo.valor_libro))
        .filter(AfActivo.estado != EstadoActivo.DADO_DE_BAJA.value)
        .scalar()
        or 0
    )


def sum_valor_adquisicion_activos(db):
    return (
        db.query(func.sum(AfActivo.valor_adquisicion))
        .filter(AfActivo.estado != EstadoActivo.DADO_DE_BAJA.value)
        .scalar()
        or 0
    )

from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from fastapi_modulo.modulos.control_interno.modelos.programa import ProgramaActividad, ProgramaAnual
from fastapi_modulo.modulos.control_interno.repositorios.base import get_current_tenant


def list_programas(db: Session, *, anio: int | None = None) -> list[ProgramaAnual]:
    query = db.query(ProgramaAnual).filter(ProgramaAnual.tenant_id == get_current_tenant())
    if anio:
        query = query.filter(ProgramaAnual.anio == anio)
    return query.order_by(ProgramaAnual.anio.desc()).all()


def get_programa(db: Session, programa_id: int) -> ProgramaAnual | None:
    return db.query(ProgramaAnual).filter(ProgramaAnual.id == programa_id, ProgramaAnual.tenant_id == get_current_tenant()).first()


def create_programa(db: Session, **data) -> ProgramaAnual:
    obj = ProgramaAnual(**data)
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return obj


def list_actividades(db: Session, *, programa_id: int, estado: str | None = None) -> list[ProgramaActividad]:
    query = db.query(ProgramaActividad).options(joinedload(ProgramaActividad.control)).filter(ProgramaActividad.programa_id == programa_id, ProgramaActividad.tenant_id == get_current_tenant())
    if estado:
        query = query.filter(ProgramaActividad.estado == estado)
    return query.order_by(ProgramaActividad.fecha_inicio_programada).all()


def list_all_actividades(db: Session) -> list[ProgramaActividad]:
    return db.query(ProgramaActividad).options(joinedload(ProgramaActividad.programa), joinedload(ProgramaActividad.control)).filter(ProgramaActividad.tenant_id == get_current_tenant()).all()


def get_actividad(db: Session, actividad_id: int) -> ProgramaActividad | None:
    return db.query(ProgramaActividad).options(joinedload(ProgramaActividad.control)).filter(ProgramaActividad.id == actividad_id, ProgramaActividad.tenant_id == get_current_tenant()).first()


def create_actividad(db: Session, **data) -> ProgramaActividad:
    obj = ProgramaActividad(**data)
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return get_actividad(db, obj.id)


def delete_programa(db: Session, obj: ProgramaAnual) -> None:
    db.delete(obj)


def delete_actividad(db: Session, obj: ProgramaActividad) -> None:
    db.delete(obj)


__all__ = [
    "create_actividad",
    "create_programa",
    "delete_actividad",
    "delete_programa",
    "get_actividad",
    "get_programa",
    "list_actividades",
    "list_all_actividades",
    "list_programas",
]

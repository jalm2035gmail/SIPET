from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from fastapi_modulo.modulos.control_interno.modelos.hallazgo import AccionCorrectiva, Hallazgo
from fastapi_modulo.modulos.control_interno.repositorios.base import get_current_tenant


def list_hallazgos(
    db: Session,
    *,
    nivel_riesgo: str | None = None,
    estado: str | None = None,
    control_id: int | None = None,
    componente_coso: str | None = None,
) -> list[Hallazgo]:
    query = db.query(Hallazgo).options(joinedload(Hallazgo.control), joinedload(Hallazgo.acciones)).filter(Hallazgo.tenant_id == get_current_tenant())
    if nivel_riesgo:
        query = query.filter(Hallazgo.nivel_riesgo == nivel_riesgo)
    if estado:
        query = query.filter(Hallazgo.estado == estado)
    if control_id:
        query = query.filter(Hallazgo.control_id == control_id)
    if componente_coso:
        query = query.filter(Hallazgo.componente_coso == componente_coso)
    return query.order_by(Hallazgo.fecha_deteccion.desc().nullslast(), Hallazgo.creado_en.desc()).all()


def list_all_hallazgos(db: Session) -> list[Hallazgo]:
    return db.query(Hallazgo).options(joinedload(Hallazgo.control), joinedload(Hallazgo.acciones)).filter(Hallazgo.tenant_id == get_current_tenant()).all()


def get_hallazgo(db: Session, hallazgo_id: int) -> Hallazgo | None:
    return db.query(Hallazgo).options(joinedload(Hallazgo.control), joinedload(Hallazgo.acciones)).filter(Hallazgo.id == hallazgo_id, Hallazgo.tenant_id == get_current_tenant()).first()


def create_hallazgo(db: Session, **data) -> Hallazgo:
    obj = Hallazgo(**data)
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return get_hallazgo(db, obj.id)


def delete_hallazgo(db: Session, obj: Hallazgo) -> None:
    db.delete(obj)


def list_acciones(db: Session, *, hallazgo_id: int) -> list[AccionCorrectiva]:
    return db.query(AccionCorrectiva).filter(AccionCorrectiva.hallazgo_id == hallazgo_id, AccionCorrectiva.tenant_id == get_current_tenant()).order_by(AccionCorrectiva.fecha_compromiso).all()


def list_all_acciones(db: Session) -> list[AccionCorrectiva]:
    return db.query(AccionCorrectiva).options(joinedload(AccionCorrectiva.hallazgo)).filter(AccionCorrectiva.tenant_id == get_current_tenant()).all()


def get_accion(db: Session, accion_id: int) -> AccionCorrectiva | None:
    return db.query(AccionCorrectiva).filter(AccionCorrectiva.id == accion_id, AccionCorrectiva.tenant_id == get_current_tenant()).first()


def create_accion(db: Session, **data) -> AccionCorrectiva:
    obj = AccionCorrectiva(**data)
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return obj


def delete_accion(db: Session, obj: AccionCorrectiva) -> None:
    db.delete(obj)


__all__ = [
    "create_accion",
    "create_hallazgo",
    "delete_accion",
    "delete_hallazgo",
    "get_accion",
    "get_hallazgo",
    "list_acciones",
    "list_all_acciones",
    "list_all_hallazgos",
    "list_hallazgos",
]

from __future__ import annotations

from sqlalchemy.orm import Session

from fastapi_modulo.modulos.control_interno.modelos.control import ControlInterno
from fastapi_modulo.modulos.control_interno.repositorios.base import get_current_tenant


def list_controles(db: Session, *, componente: str | None = None, area: str | None = None, estado: str | None = None) -> list[ControlInterno]:
    query = db.query(ControlInterno).filter(ControlInterno.tenant_id == get_current_tenant())
    if componente:
        query = query.filter(ControlInterno.componente == componente)
    if area:
        query = query.filter(ControlInterno.area == area)
    if estado:
        query = query.filter(ControlInterno.estado == estado)
    return query.order_by(ControlInterno.codigo).all()


def get_control(db: Session, control_id: int) -> ControlInterno | None:
    return db.query(ControlInterno).filter(ControlInterno.id == control_id, ControlInterno.tenant_id == get_current_tenant()).first()


def create_control(db: Session, **data) -> ControlInterno:
    obj = ControlInterno(**data)
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return obj


def delete_control(db: Session, obj: ControlInterno) -> None:
    db.delete(obj)


def distinct_componentes(db: Session) -> list[str]:
    return [row.componente for row in db.query(ControlInterno.componente).filter(ControlInterno.tenant_id == get_current_tenant()).distinct().all()]


def distinct_areas(db: Session) -> list[str]:
    return [row.area for row in db.query(ControlInterno.area).filter(ControlInterno.tenant_id == get_current_tenant()).distinct().all()]


__all__ = [
    "create_control",
    "delete_control",
    "distinct_areas",
    "distinct_componentes",
    "get_control",
    "list_controles",
]

from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from fastapi_modulo.modulos.control_interno.modelos.evidencia import Evidencia
from fastapi_modulo.modulos.control_interno.repositorios.base import get_current_tenant


def list_evidencias(
    db: Session,
    *,
    actividad_id: int | None = None,
    control_id: int | None = None,
    tipo: str | None = None,
    resultado_evaluacion: str | None = None,
) -> list[Evidencia]:
    query = db.query(Evidencia).options(joinedload(Evidencia.actividad), joinedload(Evidencia.control)).filter(Evidencia.tenant_id == get_current_tenant())
    if actividad_id:
        query = query.filter(Evidencia.actividad_id == actividad_id)
    if control_id:
        query = query.filter(Evidencia.control_id == control_id)
    if tipo:
        query = query.filter(Evidencia.tipo == tipo)
    if resultado_evaluacion:
        query = query.filter(Evidencia.resultado_evaluacion == resultado_evaluacion)
    return query.order_by(Evidencia.fecha_evidencia.desc().nullslast(), Evidencia.creado_en.desc()).all()


def list_all_evidencias(db: Session) -> list[Evidencia]:
    return db.query(Evidencia).options(joinedload(Evidencia.control)).filter(Evidencia.tenant_id == get_current_tenant()).all()


def get_evidencia(db: Session, evidencia_id: int) -> Evidencia | None:
    return db.query(Evidencia).options(joinedload(Evidencia.actividad), joinedload(Evidencia.control)).filter(Evidencia.id == evidencia_id, Evidencia.tenant_id == get_current_tenant()).first()


def create_evidencia(db: Session, **data) -> Evidencia:
    obj = Evidencia(**data)
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return get_evidencia(db, obj.id)


def delete_evidencia(db: Session, obj: Evidencia) -> None:
    db.delete(obj)


def list_resultados(db: Session) -> list[str]:
    return [row.resultado_evaluacion for row in db.query(Evidencia.resultado_evaluacion).filter(Evidencia.tenant_id == get_current_tenant()).all()]


__all__ = [
    "create_evidencia",
    "delete_evidencia",
    "get_evidencia",
    "list_all_evidencias",
    "list_evidencias",
    "list_resultados",
]

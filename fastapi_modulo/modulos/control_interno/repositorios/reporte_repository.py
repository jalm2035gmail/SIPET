from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from fastapi_modulo.modulos.control_interno.modelos.control import ControlInterno
from fastapi_modulo.modulos.control_interno.modelos.evidencia import Evidencia
from fastapi_modulo.modulos.control_interno.modelos.hallazgo import AccionCorrectiva, Hallazgo
from fastapi_modulo.modulos.control_interno.modelos.programa import ProgramaActividad
from fastapi_modulo.modulos.control_interno.repositorios.base import get_current_tenant


def list_controles(db: Session) -> list[ControlInterno]:
    return db.query(ControlInterno).filter(ControlInterno.tenant_id == get_current_tenant()).order_by(ControlInterno.componente, ControlInterno.codigo).all()


def list_actividades(db: Session) -> list[ProgramaActividad]:
    return db.query(ProgramaActividad).options(joinedload(ProgramaActividad.programa), joinedload(ProgramaActividad.control)).filter(ProgramaActividad.tenant_id == get_current_tenant()).all()


def list_evidencias(db: Session) -> list[Evidencia]:
    return db.query(Evidencia).options(joinedload(Evidencia.control)).filter(Evidencia.tenant_id == get_current_tenant()).order_by(Evidencia.fecha_evidencia.desc().nullslast()).all()


def list_hallazgos(db: Session) -> list[Hallazgo]:
    return db.query(Hallazgo).options(joinedload(Hallazgo.control), joinedload(Hallazgo.acciones)).filter(Hallazgo.tenant_id == get_current_tenant()).order_by(Hallazgo.fecha_deteccion.desc().nullslast()).all()


def list_acciones(db: Session) -> list[AccionCorrectiva]:
    return db.query(AccionCorrectiva).options(joinedload(AccionCorrectiva.hallazgo)).filter(AccionCorrectiva.tenant_id == get_current_tenant()).order_by(AccionCorrectiva.fecha_compromiso).all()


__all__ = ["list_acciones", "list_actividades", "list_controles", "list_evidencias", "list_hallazgos"]

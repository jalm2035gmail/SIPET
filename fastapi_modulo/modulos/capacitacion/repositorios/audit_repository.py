import json

from fastapi_modulo.db import SessionLocal, engine
from fastapi_modulo.modulos.capacitacion.modelos.db_models import CapEventoEntidad


def get_db():
    return SessionLocal()


def ensure_schema():
    CapEventoEntidad.__table__.create(bind=engine, checkfirst=True)


def create_evento(db, data):
    payload = dict(data)
    detalle = payload.get("detalle_json")
    if isinstance(detalle, dict):
        payload["detalle_json"] = json.dumps(detalle)
    obj = CapEventoEntidad(**payload)
    db.add(obj)
    db.flush()
    return obj


def list_eventos(db, entidad_tipo, entidad_id):
    return (
        db.query(CapEventoEntidad)
        .filter(CapEventoEntidad.entidad_tipo == entidad_tipo, CapEventoEntidad.entidad_id == entidad_id)
        .order_by(CapEventoEntidad.creado_en.desc(), CapEventoEntidad.id.desc())
        .all()
    )

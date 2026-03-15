from fastapi_modulo.db import SessionLocal
from fastapi_modulo.modulos.capacitacion.modelos.db_models import CapArchivo


def get_db():
    return SessionLocal()


def create_archivo(db, data):
    obj = CapArchivo(**data)
    db.add(obj)
    db.flush()
    return obj


def list_archivos(db, entidad_tipo=None, entidad_id=None, categoria=None):
    query = db.query(CapArchivo)
    if entidad_tipo:
        query = query.filter(CapArchivo.entidad_tipo == entidad_tipo)
    if entidad_id is not None:
        query = query.filter(CapArchivo.entidad_id == entidad_id)
    if categoria:
        query = query.filter(CapArchivo.categoria == categoria)
    return query.order_by(CapArchivo.id.desc()).all()


def get_archivo(db, archivo_id):
    return db.query(CapArchivo).filter(CapArchivo.id == archivo_id).first()

from fastapi_modulo.db import SessionLocal, engine
from fastapi_modulo.modulos.capacitacion.modelos.db_models import MAIN, CapAssetBiblioteca, CapCategoria, CapCurso, CapDiapositiva, CapElemento, CapPresentacion, CapPresentacionVersion


def get_db():
    return SessionLocal()


def ensure_schema():
    MAIN.metadata.create_all(
        bind=engine,
        tables=[CapCategoria.__table__, CapCurso.__table__, CapPresentacion.__table__, CapDiapositiva.__table__, CapElemento.__table__, CapPresentacionVersion.__table__, CapAssetBiblioteca.__table__],
        checkfirst=True,
    )


def list_presentaciones(db, autor_key=None, estado=None, curso_id=None):
    query = db.query(CapPresentacion)
    if autor_key:
        query = query.filter(CapPresentacion.autor_key == autor_key)
    if estado:
        query = query.filter(CapPresentacion.estado == estado)
    if curso_id:
        query = query.filter(CapPresentacion.curso_id == curso_id)
    return query.order_by(CapPresentacion.id.desc()).all()


def get_presentacion(db, pres_id):
    return db.query(CapPresentacion).filter(CapPresentacion.id == pres_id).first()


def create_presentacion(db, data):
    obj = CapPresentacion(**data)
    db.add(obj)
    db.flush()
    return obj


def update_presentacion(db, pres_id, data):
    obj = get_presentacion(db, pres_id)
    if not obj:
        return None
    for key, value in data.items():
        setattr(obj, key, value)
    db.flush()
    return obj


def delete_presentacion(db, pres_id):
    obj = get_presentacion(db, pres_id)
    if not obj:
        return False
    db.delete(obj)
    return True


def list_diapositivas(db, pres_id):
    return db.query(CapDiapositiva).filter(CapDiapositiva.presentacion_id == pres_id).order_by(CapDiapositiva.orden).all()


def get_diapositiva(db, diap_id):
    return db.query(CapDiapositiva).filter(CapDiapositiva.id == diap_id).first()


def create_diapositiva(db, data):
    obj = CapDiapositiva(**data)
    db.add(obj)
    db.flush()
    return obj


def delete_diapositiva(db, diap_id):
    obj = get_diapositiva(db, diap_id)
    if not obj:
        return False
    db.delete(obj)
    return True


def list_elementos(db, diap_id):
    return db.query(CapElemento).filter(CapElemento.diapositiva_id == diap_id).order_by(CapElemento.z_index).all()


def delete_elementos(db, diap_id):
    db.query(CapElemento).filter(CapElemento.diapositiva_id == diap_id).delete()


def create_elemento(db, data):
    obj = CapElemento(**data)
    db.add(obj)
    db.flush()
    return obj


def create_version(db, data):
    obj = CapPresentacionVersion(**data)
    db.add(obj)
    db.flush()
    return obj


def list_versions(db, pres_id, limit=20):
    return db.query(CapPresentacionVersion).filter(CapPresentacionVersion.presentacion_id == pres_id).order_by(CapPresentacionVersion.id.desc()).limit(limit).all()


def get_version(db, version_id):
    return db.query(CapPresentacionVersion).filter(CapPresentacionVersion.id == version_id).first()


def create_asset(db, data):
    obj = CapAssetBiblioteca(**data)
    db.add(obj)
    db.flush()
    return obj


def list_assets(db, pres_id=None, asset_type=None):
    query = db.query(CapAssetBiblioteca)
    if pres_id:
        query = query.filter((CapAssetBiblioteca.presentacion_id == pres_id) | (CapAssetBiblioteca.presentacion_id == None))
    if asset_type:
        query = query.filter(CapAssetBiblioteca.tipo == asset_type)
    return query.order_by(CapAssetBiblioteca.id.desc()).all()

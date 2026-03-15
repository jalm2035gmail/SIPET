from fastapi_modulo.db import SessionLocal
from fastapi_modulo.modulos.capacitacion.modelos.db_models import CapCategoria, CapCurso, CapLeccion, CapRutaAprendizaje, CapRutaCurso


def get_db():
    return SessionLocal()


def list_categorias(db):
    return db.query(CapCategoria).order_by(CapCategoria.nombre).all()


def get_categoria(db, cat_id):
    return db.query(CapCategoria).filter(CapCategoria.id == cat_id).first()


def create_categoria(db, data):
    obj = CapCategoria(**data)
    db.add(obj)
    db.flush()
    return obj


def update_categoria(db, cat_id, data):
    obj = get_categoria(db, cat_id)
    if not obj:
        return None
    for key, value in data.items():
        setattr(obj, key, value)
    db.flush()
    return obj


def delete_categoria(db, cat_id):
    obj = get_categoria(db, cat_id)
    if not obj:
        return False
    db.delete(obj)
    return True


def list_cursos(db, estado=None, categoria_id=None, nivel=None):
    query = db.query(CapCurso)
    if estado:
        query = query.filter(CapCurso.estado == estado)
    if categoria_id:
        query = query.filter(CapCurso.categoria_id == categoria_id)
    if nivel:
        query = query.filter(CapCurso.nivel == nivel)
    return query.order_by(CapCurso.id.desc()).all()


def list_cursos_by_ids(db, curso_ids):
    if not curso_ids:
        return []
    return db.query(CapCurso).filter(CapCurso.id.in_(curso_ids)).all()


def get_curso(db, curso_id):
    return db.query(CapCurso).filter(CapCurso.id == curso_id).first()


def get_curso_by_codigo(db, codigo):
    return db.query(CapCurso).filter(CapCurso.codigo == codigo).first()


def create_curso(db, data):
    obj = CapCurso(**data)
    db.add(obj)
    db.flush()
    return obj


def update_curso(db, curso_id, data):
    obj = get_curso(db, curso_id)
    if not obj:
        return None
    for key, value in data.items():
        setattr(obj, key, value)
    db.flush()
    return obj


def delete_curso(db, curso_id):
    obj = get_curso(db, curso_id)
    if not obj:
        return False
    db.delete(obj)
    return True


def list_cursos_completados_por_colaborador(db, colaborador_key):
    from fastapi_modulo.modulos.capacitacion.modelos.db_models import CapInscripcion

    return (
        db.query(CapInscripcion.curso_id)
        .filter(CapInscripcion.colaborador_key == colaborador_key, CapInscripcion.estado == "completado")
        .all()
    )


def list_lecciones(db, curso_id):
    return db.query(CapLeccion).filter(CapLeccion.curso_id == curso_id).order_by(CapLeccion.orden).all()


def get_leccion(db, leccion_id):
    return db.query(CapLeccion).filter(CapLeccion.id == leccion_id).first()


def create_leccion(db, data):
    obj = CapLeccion(**data)
    db.add(obj)
    db.flush()
    return obj


def update_leccion(db, leccion_id, data):
    obj = get_leccion(db, leccion_id)
    if not obj:
        return None
    for key, value in data.items():
        setattr(obj, key, value)
    db.flush()
    return obj


def delete_leccion(db, leccion_id):
    obj = get_leccion(db, leccion_id)
    if not obj:
        return False
    db.delete(obj)
    return True


def reorder_lecciones(db, curso_id, orden_ids):
    existing = list_lecciones(db, curso_id)
    offset = len(existing) + 1000
    for index, lesson in enumerate(existing):
        lesson.orden = offset + index
    db.flush()
    for pos, leccion_id in enumerate(orden_ids):
        db.query(CapLeccion).filter(CapLeccion.id == leccion_id, CapLeccion.curso_id == curso_id).update({"orden": pos})
    db.flush()


def create_ruta(db, data):
    obj = CapRutaAprendizaje(**data)
    db.add(obj)
    db.flush()
    return obj


def get_ruta(db, ruta_id):
    return db.query(CapRutaAprendizaje).filter(CapRutaAprendizaje.id == ruta_id).first()


def list_rutas(db):
    return db.query(CapRutaAprendizaje).order_by(CapRutaAprendizaje.id.desc()).all()


def create_ruta_curso(db, data):
    obj = CapRutaCurso(**data)
    db.add(obj)
    db.flush()
    return obj

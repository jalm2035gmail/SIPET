from fastapi_modulo.db import SessionLocal
from fastapi_modulo.modulos.capacitacion.modelos.db_models import CapCertificado, CapEvaluacion, CapInscripcion, CapIntentoEvaluacion, CapOpcion, CapPregunta


def get_db():
    return SessionLocal()


def list_evaluaciones(db, curso_id):
    return db.query(CapEvaluacion).filter(CapEvaluacion.curso_id == curso_id).all()


def get_evaluacion(db, eval_id):
    return db.query(CapEvaluacion).filter(CapEvaluacion.id == eval_id).first()


def create_evaluacion(db, data):
    obj = CapEvaluacion(**data)
    db.add(obj)
    db.flush()
    return obj


def list_preguntas(db, eval_id):
    return db.query(CapPregunta).filter(CapPregunta.evaluacion_id == eval_id).order_by(CapPregunta.orden).all()


def create_pregunta(db, data):
    obj = CapPregunta(**data)
    db.add(obj)
    db.flush()
    return obj


def create_opcion(db, data):
    obj = CapOpcion(**data)
    db.add(obj)
    db.flush()
    return obj


def get_pregunta(db, pregunta_id):
    return db.query(CapPregunta).filter(CapPregunta.id == pregunta_id).first()


def delete_pregunta(db, pregunta_id):
    obj = get_pregunta(db, pregunta_id)
    if not obj:
        return False
    db.delete(obj)
    return True


def get_inscripcion(db, inscripcion_id):
    return db.query(CapInscripcion).filter(CapInscripcion.id == inscripcion_id).first()


def count_intentos(db, inscripcion_id, evaluacion_id):
    return db.query(CapIntentoEvaluacion).filter(CapIntentoEvaluacion.inscripcion_id == inscripcion_id, CapIntentoEvaluacion.evaluacion_id == evaluacion_id).count()


def list_intentos(db, inscripcion_id, evaluacion_id):
    return db.query(CapIntentoEvaluacion).filter(CapIntentoEvaluacion.inscripcion_id == inscripcion_id, CapIntentoEvaluacion.evaluacion_id == evaluacion_id).all()


def create_intento(db, data):
    obj = CapIntentoEvaluacion(**data)
    db.add(obj)
    db.flush()
    return obj


def get_intento(db, intento_id):
    return db.query(CapIntentoEvaluacion).filter(CapIntentoEvaluacion.id == intento_id).first()


def get_certificado(db, cert_id):
    return db.query(CapCertificado).filter(CapCertificado.id == cert_id).first()


def get_certificado_por_folio(db, folio):
    return db.query(CapCertificado).filter(CapCertificado.folio == folio.upper()).first()


def create_certificado(db, data):
    obj = CapCertificado(**data)
    db.add(obj)
    db.flush()
    return obj


def list_inscripciones_con_certificado(db, colaborador_key):
    return db.query(CapInscripcion).filter(CapInscripcion.colaborador_key == colaborador_key).all()

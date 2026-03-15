from fastapi_modulo.db import SessionLocal
from fastapi_modulo.modulos.capacitacion.modelos.db_models import CapCertificado, CapColaboradorInsignia, CapInscripcion, CapInsignia, CapIntentoEvaluacion, CapProgresoLeccion, CapPuntosLog


def get_db():
    return SessionLocal()


def count_insignias(db, tenant_id):
    return db.query(CapInsignia).filter(CapInsignia.tenant_id == tenant_id).count()


def list_insignias(db, tenant_id):
    return db.query(CapInsignia).filter(CapInsignia.tenant_id == tenant_id).order_by(CapInsignia.orden).all()


def get_insignia(db, insignia_id, tenant_id):
    return db.query(CapInsignia).filter(CapInsignia.id == insignia_id, CapInsignia.tenant_id == tenant_id).first()


def create_insignia(db, data):
    obj = CapInsignia(**data)
    db.add(obj)
    db.flush()
    return obj


def create_puntos_log(db, data):
    obj = CapPuntosLog(**data)
    db.add(obj)
    db.flush()
    return obj


def get_puntos_log(db, tenant_id, colaborador_key, motivo, referencia_tipo=None, referencia_id=None):
    return (
        db.query(CapPuntosLog)
        .filter(
            CapPuntosLog.tenant_id == tenant_id,
            CapPuntosLog.colaborador_key == colaborador_key,
            CapPuntosLog.motivo == motivo,
            CapPuntosLog.referencia_tipo == referencia_tipo,
            CapPuntosLog.referencia_id == referencia_id,
        )
        .first()
    )


def get_puntos_sum(db, colaborador_key, tenant_id):
    from sqlalchemy import func
    return db.query(func.sum(CapPuntosLog.puntos)).filter(CapPuntosLog.colaborador_key == colaborador_key, CapPuntosLog.tenant_id == tenant_id).scalar()


def count_condicion(db, colaborador_key, condicion_tipo, tenant_id):
    if condicion_tipo == "lecciones_completadas":
        return db.query(CapProgresoLeccion).join(CapInscripcion, CapProgresoLeccion.inscripcion_id == CapInscripcion.id).filter(CapInscripcion.colaborador_key == colaborador_key, CapInscripcion.tenant_id == tenant_id, CapProgresoLeccion.completada == True, CapProgresoLeccion.tenant_id == tenant_id).count()
    if condicion_tipo == "cursos_completados":
        return db.query(CapInscripcion).filter(CapInscripcion.colaborador_key == colaborador_key, CapInscripcion.tenant_id == tenant_id, CapInscripcion.estado == "completado").count()
    if condicion_tipo == "certificados_obtenidos":
        return db.query(CapCertificado).join(CapInscripcion, CapCertificado.inscripcion_id == CapInscripcion.id).filter(CapInscripcion.colaborador_key == colaborador_key, CapInscripcion.tenant_id == tenant_id, CapCertificado.tenant_id == tenant_id).count()
    if condicion_tipo == "puntaje_perfecto":
        return db.query(CapIntentoEvaluacion).join(CapInscripcion, CapIntentoEvaluacion.inscripcion_id == CapInscripcion.id).filter(CapInscripcion.colaborador_key == colaborador_key, CapInscripcion.tenant_id == tenant_id, CapIntentoEvaluacion.tenant_id == tenant_id, CapIntentoEvaluacion.puntaje >= 100.0, CapIntentoEvaluacion.aprobado == True).count()
    return 0


def list_colaborador_insignias(db, colaborador_key, tenant_id):
    return db.query(CapColaboradorInsignia).filter(CapColaboradorInsignia.colaborador_key == colaborador_key, CapColaboradorInsignia.tenant_id == tenant_id).all()


def create_colaborador_insignia(db, data):
    obj = CapColaboradorInsignia(**data)
    db.add(obj)
    db.flush()
    return obj


def recent_puntos_logs(db, colaborador_key, tenant_id, limit=10):
    return db.query(CapPuntosLog).filter(CapPuntosLog.colaborador_key == colaborador_key, CapPuntosLog.tenant_id == tenant_id, CapPuntosLog.puntos > 0).order_by(CapPuntosLog.fecha.desc()).limit(limit).all()


def ranking_rows(db, limit, tenant_id, fecha_desde=None, fecha_hasta=None):
    from sqlalchemy import func
    query = db.query(CapPuntosLog.colaborador_key, func.sum(CapPuntosLog.puntos).label("total_puntos")).filter(CapPuntosLog.tenant_id == tenant_id)
    if fecha_desde is not None:
        query = query.filter(CapPuntosLog.fecha >= fecha_desde)
    if fecha_hasta is not None:
        query = query.filter(CapPuntosLog.fecha <= fecha_hasta)
    return query.group_by(CapPuntosLog.colaborador_key).order_by(func.sum(CapPuntosLog.puntos).desc()).limit(limit).all()


def count_colaborador_insignias(db, colaborador_key, tenant_id):
    return db.query(CapColaboradorInsignia).filter(CapColaboradorInsignia.colaborador_key == colaborador_key, CapColaboradorInsignia.tenant_id == tenant_id).count()


def get_colaborador_nombre(db, colaborador_key, tenant_id):
    return db.query(CapInscripcion.colaborador_nombre).filter(CapInscripcion.colaborador_key == colaborador_key, CapInscripcion.tenant_id == tenant_id, CapInscripcion.colaborador_nombre != None).first()


def list_puntos_logs(db, colaborador_key, tenant_id, positivos_solo=False, fecha_desde=None, fecha_hasta=None):
    query = db.query(CapPuntosLog).filter(CapPuntosLog.colaborador_key == colaborador_key, CapPuntosLog.tenant_id == tenant_id)
    if positivos_solo:
        query = query.filter(CapPuntosLog.puntos > 0)
    if fecha_desde is not None:
        query = query.filter(CapPuntosLog.fecha >= fecha_desde)
    if fecha_hasta is not None:
        query = query.filter(CapPuntosLog.fecha <= fecha_hasta)
    return query.order_by(CapPuntosLog.fecha.asc()).all()


def list_inscripciones_en_progreso(db, colaborador_key, tenant_id, updated_before=None):
    query = db.query(CapInscripcion).filter(
        CapInscripcion.colaborador_key == colaborador_key,
        CapInscripcion.tenant_id == tenant_id,
        CapInscripcion.estado == "en_progreso",
    )
    if updated_before is not None:
        query = query.filter(CapInscripcion.actualizado_en <= updated_before)
    return query.all()


def list_ultima_inscripcion_por_colaborador(db, tenant_id):
    rows = (
        db.query(CapInscripcion)
        .filter(CapInscripcion.tenant_id == tenant_id)
        .order_by(CapInscripcion.colaborador_key.asc(), CapInscripcion.actualizado_en.desc(), CapInscripcion.id.desc())
        .all()
    )
    result = {}
    for row in rows:
        result.setdefault(row.colaborador_key, row)
    return result


def departamentos_meta_rows(db, tenant_id, fecha_desde=None, fecha_hasta=None):
    from sqlalchemy import case, func

    query = (
        db.query(
            CapInscripcion.departamento,
            func.count(CapInscripcion.id).label("inscritos"),
            func.sum(case((CapInscripcion.estado == "completado", 1), else_=0)).label("completados"),
        )
        .filter(CapInscripcion.tenant_id == tenant_id, CapInscripcion.departamento != None)
    )
    if fecha_desde is not None:
        query = query.filter(CapInscripcion.fecha_inscripcion >= fecha_desde)
    if fecha_hasta is not None:
        query = query.filter(CapInscripcion.fecha_inscripcion <= fecha_hasta)
    return query.group_by(CapInscripcion.departamento).order_by(func.count(CapInscripcion.id).desc()).all()

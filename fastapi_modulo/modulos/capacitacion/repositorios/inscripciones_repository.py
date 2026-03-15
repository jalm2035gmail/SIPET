from fastapi_modulo.db import SessionLocal
from fastapi_modulo.modulos.capacitacion.modelos.db_models import CapCertificado, CapCurso, CapEncuestaSatisfaccion, CapInscripcion, CapLeccion, CapProgresoLeccion


def get_db():
    return SessionLocal()


def list_inscripciones(db, curso_id=None, colaborador_key=None, estado=None, departamento=None, fecha_desde=None, fecha_hasta=None):
    query = db.query(CapInscripcion)
    if curso_id:
        query = query.filter(CapInscripcion.curso_id == curso_id)
    if colaborador_key:
        query = query.filter(CapInscripcion.colaborador_key == colaborador_key)
    if estado:
        query = query.filter(CapInscripcion.estado == estado)
    if departamento:
        query = query.filter(CapInscripcion.departamento == departamento)
    if fecha_desde:
        query = query.filter(CapInscripcion.fecha_inscripcion >= fecha_desde)
    if fecha_hasta:
        query = query.filter(CapInscripcion.fecha_inscripcion <= fecha_hasta + "T23:59:59")
    return query.order_by(CapInscripcion.id.desc()).all()


def get_inscripcion(db, insc_id):
    return db.query(CapInscripcion).filter(CapInscripcion.id == insc_id).first()


def get_existing_inscripcion(db, colaborador_key, curso_id):
    return db.query(CapInscripcion).filter(CapInscripcion.colaborador_key == colaborador_key, CapInscripcion.curso_id == curso_id).first()


def create_inscripcion(db, data):
    obj = CapInscripcion(**data)
    db.add(obj)
    db.flush()
    return obj


def list_inscripciones_activas_por_curso(db, curso_id):
    return db.query(CapInscripcion).filter(CapInscripcion.curso_id == curso_id, CapInscripcion.estado.in_(["pendiente", "en_progreso", "completado"])).all()


def list_inscripciones_vencibles(db, now):
    return (
        db.query(CapInscripcion)
        .join(CapCurso, CapInscripcion.curso_id == CapCurso.id)
        .filter(CapCurso.es_obligatorio == True, CapInscripcion.fecha_vencimiento != None, CapInscripcion.fecha_vencimiento <= now)
        .all()
    )


def list_recordatorios_pendientes(db, now):
    from sqlalchemy import or_

    return (
        db.query(CapInscripcion)
        .join(CapCurso, CapInscripcion.curso_id == CapCurso.id)
        .filter(
            CapCurso.es_obligatorio == True,
            CapInscripcion.fecha_vencimiento != None,
            CapInscripcion.fecha_vencimiento > now,
            CapCurso.recordatorio_dias != None,
            or_(CapInscripcion.recordatorio_enviado_en == None, CapInscripcion.recordatorio_enviado_en < CapInscripcion.fecha_vencimiento),
        )
        .all()
    )


def get_satisfaccion(db, inscripcion_id):
    return db.query(CapEncuestaSatisfaccion).filter(CapEncuestaSatisfaccion.inscripcion_id == inscripcion_id).first()


def create_satisfaccion(db, data):
    obj = CapEncuestaSatisfaccion(**data)
    db.add(obj)
    db.flush()
    return obj


def get_leccion(db, leccion_id):
    return db.query(CapLeccion).filter(CapLeccion.id == leccion_id).first()


def get_progreso(db, inscripcion_id, leccion_id):
    return db.query(CapProgresoLeccion).filter(CapProgresoLeccion.inscripcion_id == inscripcion_id, CapProgresoLeccion.leccion_id == leccion_id).first()


def create_progreso(db, data):
    obj = CapProgresoLeccion(**data)
    db.add(obj)
    db.flush()
    return obj


def list_progreso_curso(db, inscripcion_id):
    return db.query(CapProgresoLeccion).filter(CapProgresoLeccion.inscripcion_id == inscripcion_id).all()


def count_lecciones_obligatorias(db, curso_id):
    return db.query(CapLeccion).filter(CapLeccion.curso_id == curso_id, CapLeccion.es_obligatoria == True).count()


def count_lecciones_obligatorias_completadas(db, inscripcion_id):
    return (
        db.query(CapProgresoLeccion)
        .join(CapLeccion, CapProgresoLeccion.leccion_id == CapLeccion.id)
        .filter(CapProgresoLeccion.inscripcion_id == inscripcion_id, CapProgresoLeccion.completada == True, CapLeccion.es_obligatoria == True)
        .count()
    )


def dashboard_counts(db):
    from sqlalchemy import case, func

    promedio_finalizacion = db.query(func.avg(func.julianday(CapInscripcion.fecha_completado) - func.julianday(CapInscripcion.fecha_inscripcion))).filter(
        CapInscripcion.estado == "completado",
        CapInscripcion.fecha_completado != None,
        CapInscripcion.fecha_inscripcion != None,
    ).scalar()
    return {
        "total_inscs": db.query(CapInscripcion).count(),
        "completadas": db.query(CapInscripcion).filter(CapInscripcion.estado == "completado").count(),
        "en_progreso": db.query(CapInscripcion).filter(CapInscripcion.estado == "en_progreso").count(),
        "reprobadas": db.query(CapInscripcion).filter(CapInscripcion.estado == "reprobado").count(),
        "pendientes": db.query(CapInscripcion).filter(CapInscripcion.estado == "pendiente").count(),
        "cursos_publicados": db.query(CapCurso).filter(CapCurso.estado == "publicado").count(),
        "cursos_archivados": db.query(CapCurso).filter(CapCurso.estado == "archivado").count(),
        "certificados": db.query(CapCertificado).count(),
        "colaboradores_unicos": db.query(func.count(func.distinct(CapInscripcion.colaborador_key))).scalar() or 0,
        "promedio_finalizacion_dias": round(float(promedio_finalizacion or 0.0), 1),
        "top_completados": (
            db.query(CapInscripcion.curso_id, CapCurso.nombre, func.count(CapInscripcion.id).label("total"))
            .join(CapCurso, CapInscripcion.curso_id == CapCurso.id)
            .filter(CapInscripcion.estado == "completado")
            .group_by(CapInscripcion.curso_id, CapCurso.nombre)
            .order_by(func.count(CapInscripcion.id).desc())
            .limit(5)
            .all()
        ),
        "top_abandonados": (
            db.query(CapInscripcion.curso_id, CapCurso.nombre, func.count(CapInscripcion.id).label("total"))
            .join(CapCurso, CapInscripcion.curso_id == CapCurso.id)
            .filter(CapInscripcion.estado.in_(["pendiente", "en_progreso"]))
            .group_by(CapInscripcion.curso_id, CapCurso.nombre)
            .order_by(func.count(CapInscripcion.id).desc())
            .limit(5)
            .all()
        ),
        "cursos_sin_avance": (
            db.query(CapInscripcion.colaborador_key, CapInscripcion.colaborador_nombre, CapCurso.nombre, CapInscripcion.departamento)
            .join(CapCurso, CapInscripcion.curso_id == CapCurso.id)
            .filter(CapInscripcion.pct_avance <= 0.0)
            .order_by(CapInscripcion.fecha_inscripcion.desc())
            .limit(10)
            .all()
        ),
        "aprobacion_baja": (
            db.query(
                CapCurso.id,
                CapCurso.nombre,
                func.count(CapInscripcion.id).label("total"),
                func.sum(case((CapInscripcion.aprobado == True, 1), else_=0)).label("aprobados"),
            )
            .join(CapInscripcion, CapInscripcion.curso_id == CapCurso.id)
            .group_by(CapCurso.id, CapCurso.nombre)
            .having(func.count(CapInscripcion.id) > 0)
            .order_by((func.sum(case((CapInscripcion.aprobado == True, 1), else_=0)) * 1.0 / func.count(CapInscripcion.id)).asc())
            .limit(5)
            .all()
        ),
        "inscripcion_por_curso": (
            db.query(CapCurso.id, CapCurso.nombre, func.count(CapInscripcion.id).label("total"))
            .outerjoin(CapInscripcion, CapInscripcion.curso_id == CapCurso.id)
            .group_by(CapCurso.id, CapCurso.nombre)
            .order_by(func.count(CapInscripcion.id).desc())
            .limit(8)
            .all()
        ),
        "estados_dist": db.query(CapInscripcion.estado, func.count(CapInscripcion.id).label("n")).group_by(CapInscripcion.estado).all(),
        "dept_dist": (
            db.query(CapInscripcion.departamento, func.count(CapInscripcion.id).label("n"))
            .filter(CapInscripcion.departamento != None)
            .group_by(CapInscripcion.departamento)
            .order_by(func.count(CapInscripcion.id).desc())
            .limit(10)
            .all()
        ),
        "dept_avance": (
            db.query(CapInscripcion.departamento, func.avg(CapInscripcion.pct_avance).label("avance"))
            .filter(CapInscripcion.departamento != None)
            .group_by(CapInscripcion.departamento)
            .order_by(func.avg(CapInscripcion.pct_avance).desc())
            .limit(10)
            .all()
        ),
        "certificados_periodo": (
            db.query(func.date(CapCertificado.fecha_emision).label("periodo"), func.count(CapCertificado.id).label("total"))
            .filter(CapCertificado.fecha_emision != None)
            .group_by(func.date(CapCertificado.fecha_emision))
            .order_by(func.date(CapCertificado.fecha_emision).desc())
            .limit(8)
            .all()
        ),
        "obligatorios_vencidos": (
            db.query(CapCurso.id, CapCurso.nombre, func.count(CapInscripcion.id).label("total"))
            .join(CapInscripcion, CapInscripcion.curso_id == CapCurso.id)
            .filter(CapCurso.es_obligatorio == True, CapCurso.fecha_fin != None, CapCurso.fecha_fin < func.current_date(), CapInscripcion.estado != "completado")
            .group_by(CapCurso.id, CapCurso.nombre)
            .order_by(func.count(CapInscripcion.id).desc())
            .all()
        ),
    }

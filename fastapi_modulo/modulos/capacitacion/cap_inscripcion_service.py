"""Servicio — Inscripciones y Progreso de Lecciones."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from fastapi_modulo.db import SessionLocal
from fastapi_modulo.modulos.capacitacion.cap_db_models import (
    CapCurso,
    CapInscripcion,
    CapLeccion,
    CapProgresoLeccion,
)


def _db():
    return SessionLocal()


def _dt(v) -> Optional[str]:
    if v is None:
        return None
    return v.isoformat() if isinstance(v, datetime) else str(v)


# ── Serializadores ──────────────────────────────────────────────────────────────

def _insc_dict(obj: CapInscripcion) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "colaborador_key": obj.colaborador_key,
        "colaborador_nombre": obj.colaborador_nombre,
        "departamento": obj.departamento,
        "curso_id": obj.curso_id,
        "curso_nombre": obj.curso.nombre if obj.curso else None,
        "estado": obj.estado,
        "pct_avance": obj.pct_avance,
        "puntaje_final": obj.puntaje_final,
        "aprobado": obj.aprobado,
        "fecha_inscripcion": _dt(obj.fecha_inscripcion),
        "fecha_inicio_real": _dt(obj.fecha_inicio_real),
        "fecha_completado": _dt(obj.fecha_completado),
    }


def _progreso_dict(obj: CapProgresoLeccion) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "inscripcion_id": obj.inscripcion_id,
        "leccion_id": obj.leccion_id,
        "completada": obj.completada,
        "intentos": obj.intentos,
        "tiempo_seg": obj.tiempo_seg,
        "fecha_completado": _dt(obj.fecha_completado),
    }


# ── Inscripciones ───────────────────────────────────────────────────────────────

def list_inscripciones(
    curso_id: Optional[int] = None,
    colaborador_key: Optional[str] = None,
    estado: Optional[str] = None,
    departamento: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> List[Dict]:
    db = _db()
    try:
        q = db.query(CapInscripcion)
        if curso_id:
            q = q.filter(CapInscripcion.curso_id == curso_id)
        if colaborador_key:
            q = q.filter(CapInscripcion.colaborador_key == colaborador_key)
        if estado:
            q = q.filter(CapInscripcion.estado == estado)
        if departamento:
            q = q.filter(CapInscripcion.departamento == departamento)
        if fecha_desde:
            q = q.filter(CapInscripcion.fecha_inscripcion >= fecha_desde)
        if fecha_hasta:
            q = q.filter(CapInscripcion.fecha_inscripcion <= fecha_hasta + 'T23:59:59')
        return [_insc_dict(o) for o in q.order_by(CapInscripcion.id.desc()).all()]
    finally:
        db.close()


def get_dashboard_stats() -> Dict[str, Any]:
    """KPIs globales para el dashboard admin."""
    db = _db()
    try:
        from fastapi_modulo.modulos.capacitacion.cap_db_models import CapCurso, CapCertificado
        from sqlalchemy import func

        total_inscs = db.query(CapInscripcion).count()
        completadas = db.query(CapInscripcion).filter(CapInscripcion.estado == 'completado').count()
        en_progreso = db.query(CapInscripcion).filter(CapInscripcion.estado == 'en_progreso').count()
        reprobadas  = db.query(CapInscripcion).filter(CapInscripcion.estado == 'reprobado').count()
        cursos_pub  = db.query(CapCurso).filter(CapCurso.estado == 'publicado').count()
        certificados= db.query(CapCertificado).count()

        # Cobertura: colaboradores únicos inscritos / total inscripciones (proxy)
        colaboradores_unicos = db.query(
            func.count(func.distinct(CapInscripcion.colaborador_key))
        ).scalar() or 0

        # Tasa de completado
        tasa = round(completadas / total_inscs * 100, 1) if total_inscs else 0.0

        # Top 5 cursos por completado
        top_completados = (
            db.query(CapInscripcion.curso_id, CapCurso.nombre,
                     func.count(CapInscripcion.id).label('total'))
            .join(CapCurso, CapInscripcion.curso_id == CapCurso.id)
            .filter(CapInscripcion.estado == 'completado')
            .group_by(CapInscripcion.curso_id, CapCurso.nombre)
            .order_by(func.count(CapInscripcion.id).desc())
            .limit(5)
            .all()
        )

        # Distribución por estado
        estados_dist = (
            db.query(CapInscripcion.estado, func.count(CapInscripcion.id).label('n'))
            .group_by(CapInscripcion.estado)
            .all()
        )

        # Distribución por departamento
        dept_dist = (
            db.query(CapInscripcion.departamento, func.count(CapInscripcion.id).label('n'))
            .filter(CapInscripcion.departamento != None)
            .group_by(CapInscripcion.departamento)
            .order_by(func.count(CapInscripcion.id).desc())
            .limit(10)
            .all()
        )

        return {
            'total_inscripciones': total_inscs,
            'completadas': completadas,
            'en_progreso': en_progreso,
            'reprobadas': reprobadas,
            'cursos_publicados': cursos_pub,
            'certificados_emitidos': certificados,
            'colaboradores_unicos': colaboradores_unicos,
            'tasa_completado': tasa,
            'top_cursos_completados': [
                {'curso_id': r[0], 'nombre': r[1], 'total': r[2]} for r in top_completados
            ],
            'estados': [
                {'estado': r[0], 'n': r[1]} for r in estados_dist
            ],
            'departamentos': [
                {'departamento': r[0] or 'Sin departamento', 'n': r[1]} for r in dept_dist
            ],
        }
    finally:
        db.close()


def get_inscripcion(insc_id: int) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(CapInscripcion).filter(CapInscripcion.id == insc_id).first()
        return _insc_dict(obj) if obj else None
    finally:
        db.close()


def inscribir_colaborador(data: Dict[str, Any]) -> tuple[Dict[str, Any], bool]:
    """
    Inscribe al colaborador si no existe la inscripción.
    Devuelve (dict, created) — created=False si ya existía.
    """
    db = _db()
    try:
        existing = (
            db.query(CapInscripcion)
            .filter(
                CapInscripcion.colaborador_key == data["colaborador_key"],
                CapInscripcion.curso_id == data["curso_id"],
            )
            .first()
        )
        if existing:
            return _insc_dict(existing), False

        obj = CapInscripcion(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return _insc_dict(obj), True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def inscribir_masivo(
    curso_id: int, colaboradores: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    data = [{"colaborador_key": ..., "colaborador_nombre": ..., "departamento": ...}, ...]
    Retorna {"creados": n, "ya_inscritos": n, "errores": n}
    """
    creados = ya_inscritos = errores = 0
    for colab in colaboradores:
        try:
            _, created = inscribir_colaborador({**colab, "curso_id": curso_id})
            if created:
                creados += 1
            else:
                ya_inscritos += 1
        except Exception:
            errores += 1
    return {"creados": creados, "ya_inscritos": ya_inscritos, "errores": errores}


# ── Progreso ────────────────────────────────────────────────────────────────────

def _recalcular_avance(db, insc: CapInscripcion) -> None:
    """Recalcula pct_avance y actualiza estado de la inscripción."""
    lecciones_obl = (
        db.query(CapLeccion)
        .filter(
            CapLeccion.curso_id == insc.curso_id,
            CapLeccion.es_obligatoria == True,
        )
        .count()
    )
    if lecciones_obl == 0:
        insc.pct_avance = 100.0
    else:
        completadas = (
            db.query(CapProgresoLeccion)
            .filter(
                CapProgresoLeccion.inscripcion_id == insc.id,
                CapProgresoLeccion.completada == True,
            )
            .join(CapLeccion, CapProgresoLeccion.leccion_id == CapLeccion.id)
            .filter(CapLeccion.es_obligatoria == True)
            .count()
        )
        insc.pct_avance = round(completadas / lecciones_obl * 100, 2)

    if insc.estado == "pendiente" and insc.pct_avance > 0:
        insc.estado = "en_progreso"
        insc.fecha_inicio_real = insc.fecha_inicio_real or datetime.utcnow()

    insc.actualizado_en = datetime.utcnow()


def marcar_leccion_completada(
    inscripcion_id: int,
    leccion_id: int,
    tiempo_seg: Optional[int] = None,
) -> Optional[Dict]:
    """
    Marca la lección como completada y recalcula el avance.
    Retorna el dict de progreso o None si la inscripción/lección no existe.
    """
    db = _db()
    try:
        insc = db.query(CapInscripcion).filter(CapInscripcion.id == inscripcion_id).first()
        if not insc:
            return None
        leccion = db.query(CapLeccion).filter(CapLeccion.id == leccion_id).first()
        if not leccion or leccion.curso_id != insc.curso_id:
            return None

        prog = (
            db.query(CapProgresoLeccion)
            .filter(
                CapProgresoLeccion.inscripcion_id == inscripcion_id,
                CapProgresoLeccion.leccion_id == leccion_id,
            )
            .first()
        )

        es_primera_vez = (not prog) or (not prog.completada)

        if not prog:
            prog = CapProgresoLeccion(
                inscripcion_id=inscripcion_id,
                leccion_id=leccion_id,
                completada=True,
                intentos=1,
                tiempo_seg=tiempo_seg,
                fecha_completado=datetime.utcnow(),
            )
            db.add(prog)
        else:
            if not prog.completada:
                prog.completada = True
                prog.fecha_completado = datetime.utcnow()
            prog.intentos += 1
            if tiempo_seg is not None:
                prog.tiempo_seg = (prog.tiempo_seg or 0) + tiempo_seg

        _recalcular_avance(db, insc)
        db.commit()
        db.refresh(prog)

        if es_primera_vez:
            try:
                from fastapi_modulo.modulos.capacitacion.cap_gamificacion_service import (
                    otorgar_puntos, check_y_otorgar_insignias,
                )
                otorgar_puntos(insc.colaborador_key, 'leccion_completada', 10, 'leccion', leccion_id)
                check_y_otorgar_insignias(insc.colaborador_key)
            except Exception:
                pass

        return _progreso_dict(prog)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def get_progreso_curso(inscripcion_id: int) -> List[Dict]:
    db = _db()
    try:
        objs = (
            db.query(CapProgresoLeccion)
            .filter(CapProgresoLeccion.inscripcion_id == inscripcion_id)
            .all()
        )
        return [_progreso_dict(o) for o in objs]
    finally:
        db.close()

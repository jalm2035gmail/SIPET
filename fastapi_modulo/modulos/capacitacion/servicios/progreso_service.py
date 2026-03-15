from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy.exc import SQLAlchemyError

from fastapi_modulo.modulos.capacitacion.modelos.db_models import CapInscripcion, CapProgresoLeccion
from fastapi_modulo.modulos.capacitacion.controladores.dependencies import load_colab_meta
from fastapi_modulo.modulos.capacitacion.repositorios import inscripciones_repository as repo
from fastapi_modulo.modulos.capacitacion.repositorios import cursos_repository as cursos_repo


def _dt(value):
    if value is None:
        return None
    return value.isoformat() if isinstance(value, datetime) else str(value)


def _insc_dict(obj: CapInscripcion):
    return {
        "id": obj.id,
        "colaborador_key": obj.colaborador_key,
        "colaborador_nombre": obj.colaborador_nombre,
        "departamento": obj.departamento,
        "rol": getattr(obj, "rol", None),
        "puesto": getattr(obj, "puesto", None),
        "curso_id": obj.curso_id,
        "curso_nombre": obj.curso.nombre if obj.curso else None,
        "estado": obj.estado,
        "pct_avance": obj.pct_avance,
        "puntaje_final": obj.puntaje_final,
        "aprobado": obj.aprobado,
        "fecha_inscripcion": _dt(obj.fecha_inscripcion),
        "fecha_inicio_real": _dt(obj.fecha_inicio_real),
        "fecha_completado": _dt(obj.fecha_completado),
        "fecha_vencimiento": _dt(getattr(obj, "fecha_vencimiento", None)),
        "recordatorio_enviado_en": _dt(getattr(obj, "recordatorio_enviado_en", None)),
        "origen_regla": getattr(obj, "origen_regla", None),
        "encuesta_satisfaccion_completa": bool(getattr(obj, "satisfaccion", None)),
    }


def _progreso_dict(obj: CapProgresoLeccion):
    return {
        "id": obj.id,
        "inscripcion_id": obj.inscripcion_id,
        "leccion_id": obj.leccion_id,
        "completada": obj.completada,
        "intentos": obj.intentos,
        "tiempo_seg": obj.tiempo_seg,
        "fecha_completado": _dt(obj.fecha_completado),
    }


def _recalcular_avance(db, insc):
    lecciones_obl = repo.count_lecciones_obligatorias(db, insc.curso_id)
    if lecciones_obl == 0:
        insc.pct_avance = 100.0
    else:
        insc.pct_avance = round(repo.count_lecciones_obligatorias_completadas(db, insc.id) / lecciones_obl * 100, 2)
    if insc.estado == "pendiente" and insc.pct_avance > 0:
        insc.estado = "en_progreso"
        insc.fecha_inicio_real = insc.fecha_inicio_real or datetime.utcnow()
    insc.actualizado_en = datetime.utcnow()


def _loads_list(value):
    if not value:
        return []
    try:
        data = json.loads(value)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _fecha_vencimiento(curso, base_dt):
    if getattr(curso, "vence_dias", None):
        return base_dt + timedelta(days=int(curso.vence_dias))
    if getattr(curso, "fecha_fin", None):
        return datetime.combine(curso.fecha_fin, datetime.min.time())
    return None


def _course_rules_match(curso, payload):
    departamentos = [str(item).strip().lower() for item in _loads_list(getattr(curso, "departamentos_json", None)) if str(item).strip()]
    if departamentos:
        if str(payload.get("departamento") or "").strip().lower() not in departamentos:
            return False
    if getattr(curso, "rol_objetivo", None) and str(payload.get("rol") or "").strip().lower() != str(curso.rol_objetivo).strip().lower():
        return False
    if getattr(curso, "puesto_objetivo", None) and str(payload.get("puesto") or "").strip().lower() != str(curso.puesto_objetivo).strip().lower():
        return False
    return True


def _prerequisitos_cumplidos(db, colaborador_key, curso):
    prereqs = _loads_list(getattr(curso, "prerrequisitos_json", None))
    if not prereqs:
        return True, []
    completados = {row[0] for row in cursos_repo.list_cursos_completados_por_colaborador(db, colaborador_key)}
    faltantes = [curso_id for curso_id in prereqs if curso_id not in completados]
    return not faltantes, faltantes


def list_inscripciones(curso_id=None, colaborador_key=None, estado=None, departamento=None, fecha_desde=None, fecha_hasta=None):
    db = repo.get_db()
    try:
        return [_insc_dict(item) for item in repo.list_inscripciones(db, curso_id, colaborador_key, estado, departamento, fecha_desde, fecha_hasta)]
    finally:
        db.close()


def get_dashboard_stats():
    db = repo.get_db()
    try:
        counts = repo.dashboard_counts(db)
        total_inscs = counts["total_inscs"]
        completadas = counts["completadas"]
        aprobadas = total_inscs - counts["reprobadas"] if total_inscs else 0
        tasa = round(completadas / total_inscs * 100, 1) if total_inscs else 0.0
        tasa_aprobacion = round((aprobadas / total_inscs) * 100, 1) if total_inscs else 0.0
        return {
            "total_inscripciones": total_inscs,
            "completadas": completadas,
            "en_progreso": counts["en_progreso"],
            "reprobadas": counts["reprobadas"],
            "pendientes": counts["pendientes"],
            "cursos_publicados": counts["cursos_publicados"],
            "cursos_archivados": counts["cursos_archivados"],
            "certificados_emitidos": counts["certificados"],
            "colaboradores_unicos": counts["colaboradores_unicos"],
            "tasa_completado": tasa,
            "tasa_aprobacion": tasa_aprobacion,
            "promedio_finalizacion_dias": counts["promedio_finalizacion_dias"],
            "obligatorios_vencidos_total": sum(int(row[2] or 0) for row in counts["obligatorios_vencidos"]),
            "top_cursos_completados": [{"curso_id": row[0], "nombre": row[1], "total": row[2]} for row in counts["top_completados"]],
            "top_cursos_abandonados": [{"curso_id": row[0], "nombre": row[1], "total": row[2]} for row in counts["top_abandonados"]],
            "sin_avance": [{"colaborador_key": row[0], "colaborador_nombre": row[1], "curso_nombre": row[2], "departamento": row[3]} for row in counts["cursos_sin_avance"]],
            "cursos_peor_aprobacion": [
                {
                    "curso_id": row[0],
                    "nombre": row[1],
                    "total": int(row[2] or 0),
                    "aprobados": int(row[3] or 0),
                    "tasa_aprobacion": round((float(row[3] or 0) / float(row[2] or 1)) * 100, 1),
                }
                for row in counts["aprobacion_baja"]
            ],
            "inscripciones_por_curso": [{"curso_id": row[0], "nombre": row[1], "total": row[2]} for row in counts["inscripcion_por_curso"]],
            "estados": [{"estado": row[0], "n": row[1]} for row in counts["estados_dist"]],
            "departamentos": [{"departamento": row[0] or "Sin departamento", "n": row[1]} for row in counts["dept_dist"]],
            "avance_departamento": [{"departamento": row[0] or "Sin departamento", "avance": round(float(row[1] or 0.0), 1)} for row in counts["dept_avance"]],
            "certificados_por_periodo": [{"periodo": str(row[0]), "total": int(row[1] or 0)} for row in counts["certificados_periodo"]],
            "obligatorios_vencidos": [{"curso_id": row[0], "nombre": row[1], "total": int(row[2] or 0)} for row in counts["obligatorios_vencidos"]],
        }
    finally:
        db.close()


def get_inscripcion(insc_id):
    db = repo.get_db()
    try:
        obj = repo.get_inscripcion(db, insc_id)
        return _insc_dict(obj) if obj else None
    finally:
        db.close()


def inscribir_colaborador(data):
    db = repo.get_db()
    try:
        curso = cursos_repo.get_curso(db, data["curso_id"])
        if not curso:
            raise ValueError("Curso no encontrado")
        if not _course_rules_match(curso, data):
            raise ValueError("El colaborador no cumple la segmentacion del curso")
        prereqs_ok, faltantes = _prerequisitos_cumplidos(db, data["colaborador_key"], curso)
        if not prereqs_ok:
            raise ValueError("Faltan prerrequisitos para inscribirse")
        existing = repo.get_existing_inscripcion(db, data["colaborador_key"], data["curso_id"])
        if existing:
            return _insc_dict(existing), False
        payload = dict(data)
        payload["fecha_vencimiento"] = _fecha_vencimiento(curso, datetime.utcnow())
        obj = repo.create_inscripcion(db, payload)
        db.commit()
        db.refresh(obj)
        return _insc_dict(obj), True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def inscribir_masivo(curso_id, colaboradores):
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


def asignar_por_reglas(curso_id):
    db = repo.get_db()
    try:
        curso = cursos_repo.get_curso(db, curso_id)
        if not curso:
            return {"creados": 0, "ya_inscritos": 0, "errores": 1}
    finally:
        db.close()
    meta = load_colab_meta()
    candidatos = []
    if isinstance(meta, dict):
        for key, row in meta.items():
            payload = {
                "colaborador_key": str(key),
                "colaborador_nombre": row.get("full_name") or row.get("nombre") or str(key),
                "departamento": row.get("departamento"),
                "rol": row.get("role") or row.get("rol"),
                "puesto": row.get("puesto"),
                "curso_id": curso_id,
                "origen_regla": "regla_automatica",
            }
            candidatos.append(payload)
    return inscribir_masivo(curso_id, candidatos)


def marcar_leccion_completada(inscripcion_id, leccion_id, tiempo_seg=None):
    db = repo.get_db()
    try:
        insc = repo.get_inscripcion(db, inscripcion_id)
        if not insc:
            return None
        leccion = repo.get_leccion(db, leccion_id)
        if not leccion or leccion.curso_id != insc.curso_id:
            return None
        prog = repo.get_progreso(db, inscripcion_id, leccion_id)
        es_primera_vez = (not prog) or (not prog.completada)
        if not prog:
            prog = repo.create_progreso(db, {"inscripcion_id": inscripcion_id, "leccion_id": leccion_id, "completada": True, "intentos": 1, "tiempo_seg": tiempo_seg, "fecha_completado": datetime.utcnow()})
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
                from fastapi_modulo.modulos.capacitacion.servicios.gamificacion_service import check_y_otorgar_insignias, otorgar_puntos
                otorgar_puntos(insc.colaborador_key, "leccion_completada", 10, "leccion", leccion_id)
                check_y_otorgar_insignias(insc.colaborador_key)
            except Exception:
                pass
        return _progreso_dict(prog)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def get_progreso_curso(inscripcion_id):
    db = repo.get_db()
    try:
        return [_progreso_dict(item) for item in repo.list_progreso_curso(db, inscripcion_id)]
    finally:
        db.close()


def registrar_encuesta_satisfaccion(inscripcion_id, calificacion, comentario=None):
    db = repo.get_db()
    try:
        insc = repo.get_inscripcion(db, inscripcion_id)
        if not insc:
            return None
        obj = repo.get_satisfaccion(db, inscripcion_id)
        if obj:
            obj.calificacion = calificacion
            obj.comentario = comentario
            obj.respondida_en = datetime.utcnow()
        else:
            obj = repo.create_satisfaccion(
                db,
                {
                    "tenant_id": insc.tenant_id,
                    "inscripcion_id": inscripcion_id,
                    "calificacion": calificacion,
                    "comentario": comentario,
                    "respondida_en": datetime.utcnow(),
                },
            )
        db.commit()
        return {"inscripcion_id": inscripcion_id, "calificacion": obj.calificacion, "comentario": obj.comentario, "respondida_en": _dt(obj.respondida_en)}
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def ejecutar_operacion_cursos():
    db = repo.get_db()
    try:
        now = datetime.utcnow()
        recordatorios = []
        reinscripciones = 0
        for insc in repo.list_recordatorios_pendientes(db, now):
            dias = int((insc.fecha_vencimiento - now).total_seconds() // 86400)
            if dias <= int(getattr(insc.curso, "recordatorio_dias", 7) or 7):
                insc.recordatorio_enviado_en = now
                recordatorios.append({"inscripcion_id": insc.id, "curso_id": insc.curso_id, "colaborador_key": insc.colaborador_key, "vence_en_dias": dias})
        for insc in repo.list_inscripciones_vencibles(db, now):
            if insc.estado != "completado":
                insc.estado = "reprobado"
            if getattr(insc.curso, "reinscripcion_automatica", False):
                existing = repo.get_existing_inscripcion(db, insc.colaborador_key, insc.curso_id)
                if existing and existing.id != insc.id and existing.fecha_inscripcion and existing.fecha_inscripcion > insc.fecha_inscripcion:
                    continue
                insc.estado = "pendiente"
                insc.pct_avance = 0.0
                insc.aprobado = None
                insc.puntaje_final = None
                insc.fecha_inscripcion = now
                insc.fecha_inicio_real = None
                insc.fecha_completado = None
                insc.fecha_vencimiento = _fecha_vencimiento(insc.curso, now)
                insc.origen_regla = "reinscripcion_automatica"
                reinscripciones += 1
        db.commit()
        return {"recordatorios": recordatorios, "reinscripciones": reinscripciones}
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()

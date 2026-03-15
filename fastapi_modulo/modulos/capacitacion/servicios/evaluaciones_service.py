from __future__ import annotations

import json
import random
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError

from fastapi_modulo.modulos.capacitacion.modelos.db_models import CapEvaluacion, CapIntentoEvaluacion, CapPregunta
from fastapi_modulo.modulos.capacitacion.repositorios import evaluaciones_repository as repo
from fastapi_modulo.modulos.capacitacion.servicios.audit_service import registrar_evento
from fastapi_modulo.modulos.capacitacion.servicios.certificados_service import cert_dict, emitir_certificado


def _dt(value):
    if value is None:
        return None
    return value.isoformat() if isinstance(value, datetime) else str(value)


def _eval_dict(obj: CapEvaluacion):
    return {
        "id": obj.id,
        "curso_id": obj.curso_id,
        "titulo": obj.titulo,
        "instrucciones": obj.instrucciones,
        "puntaje_minimo": obj.puntaje_minimo,
        "max_intentos": obj.max_intentos,
        "preguntas_por_intento": obj.preguntas_por_intento,
        "tiempo_limite_min": obj.tiempo_limite_min,
        "creado_por": obj.creado_por,
        "actualizado_por": obj.actualizado_por,
        "publicado_por": obj.publicado_por,
        "publicado_en": _dt(obj.publicado_en),
        "creado_en": _dt(obj.creado_en),
    }


def _pregunta_dict(obj: CapPregunta, incluir_correctas: bool = False):
    opciones = []
    for opcion in obj.opciones:
        data = {"id": opcion.id, "texto": opcion.texto, "orden": opcion.orden}
        if incluir_correctas:
            data["es_correcta"] = opcion.es_correcta
        opciones.append(data)
    return {
        "id": obj.id,
        "evaluacion_id": obj.evaluacion_id,
        "enunciado": obj.enunciado,
        "tipo": obj.tipo,
        "explicacion": obj.explicacion if incluir_correctas else None,
        "puntaje": obj.puntaje,
        "orden": obj.orden,
        "opciones": opciones,
    }


def list_evaluaciones(curso_id, tenant_id=None):
    db = repo.get_db()
    try:
        return [_eval_dict(item) for item in repo.list_evaluaciones(db, curso_id)]
    finally:
        db.close()


def get_evaluacion(eval_id, tenant_id=None):
    db = repo.get_db()
    try:
        obj = repo.get_evaluacion(db, eval_id)
        return _eval_dict(obj) if obj else None
    finally:
        db.close()


def create_evaluacion(data, tenant_id=None, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        data = dict(data)
        preguntas_data = data.pop("preguntas", [])
        if tenant_id:
            data["tenant_id"] = tenant_id
        if actor_key:
            data.setdefault("creado_por", actor_key)
            data.setdefault("actualizado_por", actor_key)
        obj = repo.create_evaluacion(db, data)
        for pregunta_data in preguntas_data:
            opciones_data = pregunta_data.pop("opciones", [])
            pregunta = repo.create_pregunta(db, {**pregunta_data, "evaluacion_id": obj.id, "tenant_id": obj.tenant_id})
            for opcion_data in opciones_data:
                repo.create_opcion(db, {**opcion_data, "pregunta_id": pregunta.id, "tenant_id": obj.tenant_id})
        registrar_evento(db, "evaluacion", obj.id, "created", actor_key=actor_key, actor_nombre=actor_name, tenant_id=obj.tenant_id, detalle={"titulo": obj.titulo, "curso_id": obj.curso_id})
        db.commit()
        db.refresh(obj)
        return _eval_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def list_preguntas(eval_id, tenant_id=None, incluir_correctas: bool = False):
    db = repo.get_db()
    try:
        return [_pregunta_dict(item, incluir_correctas) for item in repo.list_preguntas(db, eval_id)]
    finally:
        db.close()


def create_pregunta(data, tenant_id=None, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        data = dict(data)
        opciones = data.pop("opciones", [])
        evaluacion = repo.get_evaluacion(db, data["evaluacion_id"])
        if tenant_id:
            data["tenant_id"] = tenant_id
        elif evaluacion:
            data["tenant_id"] = evaluacion.tenant_id
        obj = repo.create_pregunta(db, data)
        for opcion in opciones:
            repo.create_opcion(db, {**opcion, "pregunta_id": obj.id, "tenant_id": obj.tenant_id})
        if evaluacion:
            evaluacion.actualizado_por = actor_key
        registrar_evento(db, "evaluacion", obj.evaluacion_id, "question_created", actor_key=actor_key, actor_nombre=actor_name, tenant_id=obj.tenant_id, detalle={"pregunta_id": obj.id, "enunciado": obj.enunciado})
        db.commit()
        db.refresh(obj)
        return _pregunta_dict(obj, incluir_correctas=True)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_pregunta(pregunta_id, tenant_id=None, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        obj = repo.get_pregunta(db, pregunta_id)
        if obj:
            evaluacion = repo.get_evaluacion(db, obj.evaluacion_id)
            if evaluacion:
                evaluacion.actualizado_por = actor_key
            registrar_evento(db, "evaluacion", obj.evaluacion_id, "question_deleted", actor_key=actor_key, actor_nombre=actor_name, tenant_id=obj.tenant_id, detalle={"pregunta_id": obj.id, "enunciado": obj.enunciado})
        ok = repo.delete_pregunta(db, pregunta_id)
        if not ok:
            return False
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def iniciar_intento(inscripcion_id, evaluacion_id, tenant_id=None):
    db = repo.get_db()
    try:
        evaluacion = repo.get_evaluacion(db, evaluacion_id)
        if not evaluacion:
            raise ValueError("Evaluación no encontrada")
        insc = repo.get_inscripcion(db, inscripcion_id)
        if not insc:
            raise ValueError("Inscripción no encontrada")
        if insc.curso_id != evaluacion.curso_id:
            raise ValueError("La inscripción no corresponde al curso de esta evaluación")
        intentos_previos = repo.count_intentos(db, inscripcion_id, evaluacion_id)
        if intentos_previos >= evaluacion.max_intentos:
            raise ValueError(f"Se han agotado los {evaluacion.max_intentos} intentos permitidos")
        preguntas = evaluacion.preguntas[:]
        if evaluacion.preguntas_por_intento and evaluacion.preguntas_por_intento < len(preguntas):
            preguntas = random.sample(preguntas, evaluacion.preguntas_por_intento)
        else:
            random.shuffle(preguntas)
        intento = repo.create_intento(db, {"inscripcion_id": inscripcion_id, "evaluacion_id": evaluacion_id, "numero_intento": intentos_previos + 1, "fecha_inicio": datetime.utcnow()})
        db.commit()
        db.refresh(intento)
        return {
            "intento_id": intento.id,
            "numero_intento": intento.numero_intento,
            "max_intentos": evaluacion.max_intentos,
            "tiempo_limite_min": evaluacion.tiempo_limite_min,
            "preguntas": [_pregunta_dict(item, False) for item in preguntas],
        }
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def enviar_respuestas(intento_id, tenant_id=None, respuestas=None, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        respuestas = respuestas or {}
        intento = repo.get_intento(db, intento_id)
        if not intento:
            raise ValueError("Intento no encontrado")
        if intento.fecha_fin:
            raise ValueError("Este intento ya fue calificado")
        evaluacion = repo.get_evaluacion(db, intento.evaluacion_id)
        puntaje_obtenido = 0.0
        puntaje_maximo = 0.0
        for pregunta in evaluacion.preguntas:
            puntaje_maximo += pregunta.puntaje
            clave = str(pregunta.id)
            if clave not in respuestas:
                continue
            resp = respuestas[clave]
            if pregunta.tipo in ("opcion_multiple", "verdadero_falso"):
                try:
                    opcion_id = int(resp)
                except (TypeError, ValueError):
                    continue
                opcion = next((item for item in pregunta.opciones if item.id == opcion_id), None)
                if opcion and opcion.es_correcta:
                    puntaje_obtenido += pregunta.puntaje
        pct = round(puntaje_obtenido / puntaje_maximo * 100, 2) if puntaje_maximo else 0.0
        aprobado = pct >= evaluacion.puntaje_minimo
        intento.puntaje = pct
        intento.puntaje_maximo = puntaje_maximo
        intento.aprobado = aprobado
        intento.respuestas_json = json.dumps(respuestas)
        intento.fecha_fin = datetime.utcnow()
        insc = repo.get_inscripcion(db, intento.inscripcion_id)
        estado_previo = insc.estado if insc else None
        cert_previo = insc.certificado is not None if insc else False
        if insc and aprobado:
            if insc.puntaje_final is None or pct > insc.puntaje_final:
                insc.puntaje_final = pct
            insc.aprobado = True
            if insc.pct_avance >= 100:
                insc.estado = "completado"
                insc.fecha_completado = insc.fecha_completado or datetime.utcnow()
                emitir_certificado(db, insc, pct, actor_key=actor_key or insc.colaborador_key, actor_name=actor_name, tenant_id=tenant_id or getattr(insc, "tenant_id", None))
        elif insc and not aprobado:
            if repo.count_intentos(db, insc.id, evaluacion.id) >= evaluacion.max_intentos:
                all_failed = not any(item.aprobado for item in repo.list_intentos(db, insc.id, evaluacion.id) if item.id != intento.id)
                if all_failed:
                    insc.estado = "reprobado"
        db.commit()
        if insc:
            try:
                from fastapi_modulo.modulos.capacitacion.servicios.gamificacion_service import check_y_otorgar_insignias, otorgar_puntos
                if aprobado:
                    otorgar_puntos(insc.colaborador_key, "evaluacion_aprobada", 30, "evaluacion", evaluacion.id)
                if aprobado and intento.numero_intento == 1:
                    otorgar_puntos(insc.colaborador_key, "aprobado_primer_intento", 40, "evaluacion", evaluacion.id)
                if pct >= 100.0 and aprobado:
                    otorgar_puntos(insc.colaborador_key, "evaluacion_perfecta", 0, "evaluacion_perfecta", evaluacion.id)
                if estado_previo != "completado" and insc.estado == "completado":
                    otorgar_puntos(insc.colaborador_key, "curso_completado", 50, "curso", insc.curso_id)
                if not cert_previo and insc.certificado:
                    otorgar_puntos(insc.colaborador_key, "certificado_obtenido", 100, "certificado", insc.certificado.id)
                check_y_otorgar_insignias(insc.colaborador_key)
            except Exception:
                pass
        return {
            "intento_id": intento.id,
            "puntaje": pct,
            "puntaje_maximo": puntaje_maximo,
            "aprobado": aprobado,
            "puntaje_minimo_aprobacion": evaluacion.puntaje_minimo,
            "certificado": cert_dict(insc.certificado) if insc and insc.certificado else None,
        }
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()

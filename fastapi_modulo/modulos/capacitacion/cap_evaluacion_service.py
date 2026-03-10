"""Servicio — Motor de Evaluaciones y Certificación."""
from __future__ import annotations

import json
import random
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError

from fastapi_modulo.db import SessionLocal
from fastapi_modulo.modulos.capacitacion.cap_db_models import (
    CapCertificado,
    CapEvaluacion,
    CapInscripcion,
    CapIntentoEvaluacion,
    CapOpcion,
    CapPregunta,
)


def _db():
    return SessionLocal()


def _dt(v) -> Optional[str]:
    if v is None:
        return None
    return v.isoformat() if isinstance(v, datetime) else str(v)


# ── Serializadores ──────────────────────────────────────────────────────────────

def _eval_dict(obj: CapEvaluacion) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "curso_id": obj.curso_id,
        "titulo": obj.titulo,
        "instrucciones": obj.instrucciones,
        "puntaje_minimo": obj.puntaje_minimo,
        "max_intentos": obj.max_intentos,
        "preguntas_por_intento": obj.preguntas_por_intento,
        "tiempo_limite_min": obj.tiempo_limite_min,
        "creado_en": _dt(obj.creado_en),
    }


def _pregunta_dict(obj: CapPregunta, incluir_correctas: bool = False) -> Dict[str, Any]:
    opciones = []
    for op in obj.opciones:
        o: Dict[str, Any] = {"id": op.id, "texto": op.texto, "orden": op.orden}
        if incluir_correctas:
            o["es_correcta"] = op.es_correcta
        opciones.append(o)
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


def _intento_dict(obj: CapIntentoEvaluacion) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "inscripcion_id": obj.inscripcion_id,
        "evaluacion_id": obj.evaluacion_id,
        "numero_intento": obj.numero_intento,
        "puntaje": obj.puntaje,
        "puntaje_maximo": obj.puntaje_maximo,
        "aprobado": obj.aprobado,
        "fecha_inicio": _dt(obj.fecha_inicio),
        "fecha_fin": _dt(obj.fecha_fin),
    }


def _cert_dict(obj: CapCertificado) -> Dict[str, Any]:
    insc = obj.inscripcion
    return {
        "id": obj.id,
        "folio": obj.folio,
        "puntaje_final": obj.puntaje_final,
        "fecha_emision": _dt(obj.fecha_emision),
        "url_pdf": obj.url_pdf,
        "inscripcion_id": obj.inscripcion_id,
        "colaborador_key": insc.colaborador_key if insc else None,
        "colaborador_nombre": insc.colaborador_nombre if insc else None,
        "curso_id": insc.curso_id if insc else None,
        "curso_nombre": insc.curso.nombre if (insc and insc.curso) else None,
    }


# ── Evaluaciones CRUD ───────────────────────────────────────────────────────────

def list_evaluaciones(curso_id: int) -> List[Dict]:
    db = _db()
    try:
        objs = (
            db.query(CapEvaluacion)
            .filter(CapEvaluacion.curso_id == curso_id)
            .all()
        )
        return [_eval_dict(o) for o in objs]
    finally:
        db.close()


def get_evaluacion(eval_id: int) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(CapEvaluacion).filter(CapEvaluacion.id == eval_id).first()
        return _eval_dict(obj) if obj else None
    finally:
        db.close()


def create_evaluacion(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        preguntas_data = data.pop("preguntas", [])
        obj = CapEvaluacion(**data)
        db.add(obj)
        db.flush()
        for p_data in preguntas_data:
            opciones_data = p_data.pop("opciones", [])
            pregunta = CapPregunta(evaluacion_id=obj.id, **p_data)
            db.add(pregunta)
            db.flush()
            for o_data in opciones_data:
                opcion = CapOpcion(pregunta_id=pregunta.id, **o_data)
                db.add(opcion)
        db.commit()
        db.refresh(obj)
        return _eval_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


# ── Preguntas ───────────────────────────────────────────────────────────────────

def list_preguntas(eval_id: int, incluir_correctas: bool = False) -> List[Dict]:
    db = _db()
    try:
        objs = (
            db.query(CapPregunta)
            .filter(CapPregunta.evaluacion_id == eval_id)
            .order_by(CapPregunta.orden)
            .all()
        )
        return [_pregunta_dict(o, incluir_correctas) for o in objs]
    finally:
        db.close()


def create_pregunta(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        opciones_data = data.pop("opciones", [])
        obj = CapPregunta(**data)
        db.add(obj)
        db.flush()
        for o_data in opciones_data:
            opcion = CapOpcion(pregunta_id=obj.id, **o_data)
            db.add(opcion)
        db.commit()
        db.refresh(obj)
        return _pregunta_dict(obj, incluir_correctas=True)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_pregunta(pregunta_id: int) -> bool:
    db = _db()
    try:
        obj = db.query(CapPregunta).filter(CapPregunta.id == pregunta_id).first()
        if not obj:
            return False
        db.delete(obj)
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


# ── Motor de intentos ───────────────────────────────────────────────────────────

def iniciar_intento(inscripcion_id: int, evaluacion_id: int) -> Dict[str, Any]:
    """
    Crea un nuevo intento. Lanza ValueError si se excede max_intentos.
    Devuelve las preguntas seleccionadas para este intento (sin indicar correctas).
    """
    db = _db()
    try:
        evaluacion = db.query(CapEvaluacion).filter(CapEvaluacion.id == evaluacion_id).first()
        if not evaluacion:
            raise ValueError("Evaluación no encontrada")

        insc = db.query(CapInscripcion).filter(CapInscripcion.id == inscripcion_id).first()
        if not insc:
            raise ValueError("Inscripción no encontrada")
        if insc.curso_id != evaluacion.curso_id:
            raise ValueError("La inscripción no corresponde al curso de esta evaluación")

        intentos_anteriores = (
            db.query(CapIntentoEvaluacion)
            .filter(
                CapIntentoEvaluacion.inscripcion_id == inscripcion_id,
                CapIntentoEvaluacion.evaluacion_id == evaluacion_id,
            )
            .count()
        )
        if intentos_anteriores >= evaluacion.max_intentos:
            raise ValueError(
                f"Se han agotado los {evaluacion.max_intentos} intentos permitidos"
            )

        # Seleccionar preguntas
        preguntas = evaluacion.preguntas[:]
        n = evaluacion.preguntas_por_intento
        if n and n < len(preguntas):
            preguntas = random.sample(preguntas, n)
        else:
            random.shuffle(preguntas)

        intento = CapIntentoEvaluacion(
            inscripcion_id=inscripcion_id,
            evaluacion_id=evaluacion_id,
            numero_intento=intentos_anteriores + 1,
            fecha_inicio=datetime.utcnow(),
        )
        db.add(intento)
        db.commit()
        db.refresh(intento)

        return {
            "intento_id": intento.id,
            "numero_intento": intento.numero_intento,
            "max_intentos": evaluacion.max_intentos,
            "tiempo_limite_min": evaluacion.tiempo_limite_min,
            "preguntas": [_pregunta_dict(p, incluir_correctas=False) for p in preguntas],
        }
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def enviar_respuestas(
    intento_id: int,
    respuestas: Dict[str, Any],  # {str(pregunta_id): opcion_id | texto}
) -> Dict[str, Any]:
    """
    Califica el intento, actualiza puntaje en la inscripción y emite certificado si corresponde.
    Retorna dict con resultado.
    """
    db = _db()
    try:
        intento = db.query(CapIntentoEvaluacion).filter(CapIntentoEvaluacion.id == intento_id).first()
        if not intento:
            raise ValueError("Intento no encontrado")
        if intento.fecha_fin:
            raise ValueError("Este intento ya fue calificado")

        evaluacion = db.query(CapEvaluacion).filter(CapEvaluacion.id == intento.evaluacion_id).first()

        # Calificar
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
                opcion = next(
                    (o for o in pregunta.opciones if o.id == opcion_id), None
                )
                if opcion and opcion.es_correcta:
                    puntaje_obtenido += pregunta.puntaje
            elif pregunta.tipo == "texto_libre":
                # texto libre no se califica automáticamente
                puntaje_obtenido += 0

        pct = round(puntaje_obtenido / puntaje_maximo * 100, 2) if puntaje_maximo else 0.0
        aprobado = pct >= evaluacion.puntaje_minimo

        intento.puntaje = pct
        intento.puntaje_maximo = puntaje_maximo
        intento.aprobado = aprobado
        intento.respuestas_json = json.dumps(respuestas)
        intento.fecha_fin = datetime.utcnow()

        # Actualizar atributos de la inscripción
        insc = db.query(CapInscripcion).filter(CapInscripcion.id == intento.inscripcion_id).first()
        estado_previo = insc.estado if insc else None
        cert_previo = insc.certificado is not None if insc else False
        if insc and aprobado:
            if insc.puntaje_final is None or pct > insc.puntaje_final:
                insc.puntaje_final = pct
            insc.aprobado = True
            if insc.pct_avance >= 100:
                insc.estado = "completado"
                insc.fecha_completado = insc.fecha_completado or datetime.utcnow()
                _emitir_certificado(db, insc, pct)
        elif insc and not aprobado:
            intentos_totales = (
                db.query(CapIntentoEvaluacion)
                .filter(
                    CapIntentoEvaluacion.inscripcion_id == insc.id,
                    CapIntentoEvaluacion.evaluacion_id == evaluacion.id,
                )
                .count()
            )
            if intentos_totales >= evaluacion.max_intentos:
                all_failed = not any(
                    i.aprobado
                    for i in db.query(CapIntentoEvaluacion).filter(
                        CapIntentoEvaluacion.inscripcion_id == insc.id,
                        CapIntentoEvaluacion.evaluacion_id == evaluacion.id,
                    ).all()
                    if i.id != intento.id
                )
                if all_failed:
                    insc.estado = "reprobado"

        db.commit()

        # ── Gamificación ────────────────────────────────────────────────
        if insc:
            try:
                from fastapi_modulo.modulos.capacitacion.cap_gamificacion_service import (
                    otorgar_puntos, check_y_otorgar_insignias,
                )
                if aprobado:
                    otorgar_puntos(insc.colaborador_key, 'evaluacion_aprobada', 30, 'evaluacion', evaluacion.id)
                if pct >= 100.0 and aprobado:
                    otorgar_puntos(insc.colaborador_key, 'evaluacion_perfecta', 0, 'evaluacion_perfecta', evaluacion.id)
                if estado_previo != 'completado' and insc.estado == 'completado':
                    otorgar_puntos(insc.colaborador_key, 'curso_completado', 50, 'curso', insc.curso_id)
                if not cert_previo and insc.certificado:
                    otorgar_puntos(insc.colaborador_key, 'certificado_obtenido', 100, 'certificado', insc.certificado.id)
                check_y_otorgar_insignias(insc.colaborador_key)
            except Exception:
                pass

        cert = None
        if insc and insc.certificado:
            cert = _cert_dict(insc.certificado)

        return {
            "intento_id": intento.id,
            "puntaje": pct,
            "puntaje_maximo": puntaje_maximo,
            "aprobado": aprobado,
            "puntaje_minimo_aprobacion": evaluacion.puntaje_minimo,
            "certificado": cert,
        }
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def _emitir_certificado(db, insc: CapInscripcion, puntaje: float) -> Optional[CapCertificado]:
    """Crea el certificado si no existe ya."""
    if insc.certificado:
        return insc.certificado
    folio = uuid.uuid4().hex[:12].upper()
    cert = CapCertificado(
        inscripcion_id=insc.id,
        folio=folio,
        puntaje_final=puntaje,
        fecha_emision=datetime.utcnow(),
    )
    db.add(cert)
    return cert


# ── Certificados ────────────────────────────────────────────────────────────────

def get_certificado(cert_id: int) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(CapCertificado).filter(CapCertificado.id == cert_id).first()
        return _cert_dict(obj) if obj else None
    finally:
        db.close()


def get_certificado_por_folio(folio: str) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(CapCertificado).filter(CapCertificado.folio == folio.upper()).first()
        return _cert_dict(obj) if obj else None
    finally:
        db.close()


def get_certificados_colaborador(colaborador_key: str) -> List[Dict]:
    db = _db()
    try:
        inscs = (
            db.query(CapInscripcion)
            .filter(CapInscripcion.colaborador_key == colaborador_key)
            .all()
        )
        result = []
        for i in inscs:
            if i.certificado:
                result.append(_cert_dict(i.certificado))
        return result
    finally:
        db.close()

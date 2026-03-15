from __future__ import annotations

import random
import string
import json
from datetime import date
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError

from fastapi_modulo.modulos.capacitacion.modelos.db_models import CapCategoria, CapCurso, CapLeccion
from fastapi_modulo.modulos.capacitacion.repositorios import cursos_repository as repo
from fastapi_modulo.modulos.capacitacion.servicios.audit_service import registrar_evento


def _dt(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _d(value):
    if value is None:
        return None
    return str(value)


def _loads_list(value):
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        data = json.loads(value)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _normalize_course_payload(data):
    payload = dict(data)
    for field in ("fecha_inicio", "fecha_fin"):
        if isinstance(payload.get(field), str) and payload.get(field):
            payload[field] = date.fromisoformat(payload[field])
    for field in ("prerrequisitos", "departamentos"):
        if field in payload:
            payload[field + "_json"] = json.dumps(payload.pop(field) or [])
    return payload


def _cat_dict(obj: CapCategoria):
    return {"id": obj.id, "nombre": obj.nombre, "descripcion": obj.descripcion, "color": obj.color, "creado_en": _dt(obj.creado_en)}


def _leccion_dict(obj: CapLeccion):
    return {
        "id": obj.id,
        "curso_id": obj.curso_id,
        "titulo": obj.titulo,
        "tipo": obj.tipo,
        "contenido": obj.contenido,
        "url_archivo": obj.url_archivo,
        "duracion_min": obj.duracion_min,
        "orden": obj.orden,
        "es_obligatoria": obj.es_obligatoria,
        "creado_en": _dt(obj.creado_en),
    }


def _curso_dict(obj: CapCurso, with_lecciones: bool = False):
    data = {
        "id": obj.id,
        "codigo": obj.codigo,
        "nombre": obj.nombre,
        "descripcion": obj.descripcion,
        "objetivo": obj.objetivo,
        "categoria_id": obj.categoria_id,
        "categoria_nombre": obj.categoria.nombre if obj.categoria else None,
        "nivel": obj.nivel,
        "estado": obj.estado,
        "responsable": obj.responsable,
        "duracion_horas": obj.duracion_horas,
        "puntaje_aprobacion": obj.puntaje_aprobacion,
        "imagen_url": obj.imagen_url,
        "fecha_inicio": _d(obj.fecha_inicio),
        "fecha_fin": _d(obj.fecha_fin),
        "es_obligatorio": obj.es_obligatorio,
        "vence_dias": obj.vence_dias,
        "recordatorio_dias": obj.recordatorio_dias,
        "reinscripcion_automatica": obj.reinscripcion_automatica,
        "prerrequisitos": _loads_list(obj.prerrequisitos_json),
        "departamentos": _loads_list(obj.departamentos_json),
        "rol_objetivo": obj.rol_objetivo,
        "puesto_objetivo": obj.puesto_objetivo,
        "bloquear_certificado_encuesta": obj.bloquear_certificado_encuesta,
        "requiere_encuesta_satisfaccion": obj.requiere_encuesta_satisfaccion,
        "version_numero": obj.version_numero,
        "version_padre_id": obj.version_padre_id,
        "version_actual": obj.version_actual,
        "creado_por": obj.creado_por,
        "actualizado_por": obj.actualizado_por,
        "publicado_por": obj.publicado_por,
        "publicado_en": _dt(obj.publicado_en),
        "total_lecciones": len(obj.lecciones),
        "total_inscripciones": len(obj.inscripciones),
        "creado_en": _dt(obj.creado_en),
        "actualizado_en": _dt(obj.actualizado_en),
    }
    if with_lecciones:
        data["lecciones"] = [_leccion_dict(item) for item in obj.lecciones]
    return data


def _gen_codigo():
    chars = string.ascii_uppercase + string.digits
    return "CAP-" + "".join(random.choices(chars, k=6))


def list_categorias(tenant_id=None):
    db = repo.get_db()
    try:
        return [_cat_dict(item) for item in repo.list_categorias(db)]
    finally:
        db.close()


def get_categoria(cat_id, tenant_id=None):
    db = repo.get_db()
    try:
        obj = repo.get_categoria(db, cat_id)
        return _cat_dict(obj) if obj else None
    finally:
        db.close()


def create_categoria(data, tenant_id=None, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        data = dict(data)
        if tenant_id:
            data["tenant_id"] = tenant_id
        obj = repo.create_categoria(db, data)
        db.commit()
        db.refresh(obj)
        return _cat_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_categoria(cat_id, data, tenant_id=None, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        obj = repo.update_categoria(db, cat_id, data)
        if not obj:
            return None
        db.commit()
        db.refresh(obj)
        return _cat_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_categoria(cat_id, tenant_id=None, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        ok = repo.delete_categoria(db, cat_id)
        if not ok:
            return False
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def list_cursos(tenant_id=None, estado=None, categoria_id=None, nivel=None):
    db = repo.get_db()
    try:
        return [_curso_dict(item) for item in repo.list_cursos(db, estado, categoria_id, nivel)]
    finally:
        db.close()


def get_curso(curso_id, tenant_id=None, with_lecciones: bool = False):
    db = repo.get_db()
    try:
        obj = repo.get_curso(db, curso_id)
        return _curso_dict(obj, with_lecciones=with_lecciones) if obj else None
    finally:
        db.close()


def create_curso(data, tenant_id=None, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        data = _normalize_course_payload(data)
        codigo = None
        for _ in range(10):
            codigo = _gen_codigo()
            if not repo.get_curso_by_codigo(db, codigo):
                break
        data["codigo"] = codigo
        if tenant_id:
            data["tenant_id"] = tenant_id
        if actor_key:
            data.setdefault("creado_por", actor_key)
            data.setdefault("actualizado_por", actor_key)
        if str(data.get("estado") or "") == "publicado":
            data["publicado_por"] = actor_key
            data["publicado_en"] = datetime.utcnow()
        obj = repo.create_curso(db, data)
        registrar_evento(
            db,
            "curso",
            obj.id,
            "created",
            actor_key=actor_key,
            actor_nombre=actor_name,
            tenant_id=obj.tenant_id,
            detalle={"nombre": obj.nombre, "estado": str(obj.estado)},
        )
        if str(obj.estado) == "publicado":
            registrar_evento(
                db,
                "curso",
                obj.id,
                "published",
                actor_key=actor_key,
                actor_nombre=actor_name,
                tenant_id=obj.tenant_id,
                detalle={"estado": str(obj.estado)},
            )
        db.commit()
        db.refresh(obj)
        return _curso_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_curso(curso_id, data, tenant_id=None, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        data = _normalize_course_payload(data)
        data.pop("codigo", None)
        current = repo.get_curso(db, curso_id)
        if not current:
            return None
        prev_estado = str(current.estado)
        data["actualizado_en"] = datetime.utcnow()
        if actor_key:
            data["actualizado_por"] = actor_key
        next_estado = str(data.get("estado") or prev_estado)
        if next_estado == "publicado" and prev_estado != "publicado":
            data["publicado_por"] = actor_key
            data["publicado_en"] = datetime.utcnow()
        obj = repo.update_curso(db, curso_id, data)
        if not obj:
            return None
        registrar_evento(
            db,
            "curso",
            obj.id,
            "updated",
            actor_key=actor_key,
            actor_nombre=actor_name,
            tenant_id=obj.tenant_id,
            detalle={"estado_anterior": prev_estado, "estado_nuevo": str(obj.estado)},
        )
        if prev_estado != "publicado" and str(obj.estado) == "publicado":
            registrar_evento(
                db,
                "curso",
                obj.id,
                "published",
                actor_key=actor_key,
                actor_nombre=actor_name,
                tenant_id=obj.tenant_id,
                detalle={"estado_anterior": prev_estado, "estado_nuevo": str(obj.estado)},
            )
        db.commit()
        db.refresh(obj)
        return _curso_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def duplicate_as_new_version(curso_id, tenant_id=None, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        current = repo.get_curso(db, curso_id)
        if not current:
            return None
        current.version_actual = False
        data = {
            "tenant_id": tenant_id or current.tenant_id,
            "codigo": _gen_codigo(),
            "nombre": f"{current.nombre} v{int(current.version_numero or 1) + 1}",
            "descripcion": current.descripcion,
            "objetivo": current.objetivo,
            "categoria_id": current.categoria_id,
            "nivel": current.nivel,
            "estado": "borrador",
            "responsable": current.responsable,
            "duracion_horas": current.duracion_horas,
            "puntaje_aprobacion": current.puntaje_aprobacion,
            "imagen_url": current.imagen_url,
            "fecha_inicio": current.fecha_inicio,
            "fecha_fin": current.fecha_fin,
            "es_obligatorio": current.es_obligatorio,
            "vence_dias": current.vence_dias,
            "recordatorio_dias": current.recordatorio_dias,
            "reinscripcion_automatica": current.reinscripcion_automatica,
            "prerrequisitos_json": current.prerrequisitos_json,
            "departamentos_json": current.departamentos_json,
            "rol_objetivo": current.rol_objetivo,
            "puesto_objetivo": current.puesto_objetivo,
            "bloquear_certificado_encuesta": current.bloquear_certificado_encuesta,
            "requiere_encuesta_satisfaccion": current.requiere_encuesta_satisfaccion,
            "version_numero": int(current.version_numero or 1) + 1,
            "version_padre_id": current.id,
            "version_actual": True,
            "creado_por": actor_key,
            "actualizado_por": actor_key,
        }
        new_course = repo.create_curso(db, data)
        for leccion in current.lecciones:
            repo.create_leccion(
                db,
                {
                    "tenant_id": tenant_id or current.tenant_id,
                    "curso_id": new_course.id,
                    "titulo": leccion.titulo,
                    "tipo": leccion.tipo,
                    "contenido": leccion.contenido,
                    "url_archivo": leccion.url_archivo,
                    "duracion_min": leccion.duracion_min,
                    "orden": leccion.orden,
                    "es_obligatoria": leccion.es_obligatoria,
                },
            )
        registrar_evento(db, "curso", new_course.id, "version_created", actor_key=actor_key, actor_nombre=actor_name, tenant_id=new_course.tenant_id, detalle={"version_padre_id": current.id})
        db.commit()
        db.refresh(new_course)
        return _curso_dict(new_course, with_lecciones=True)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def create_ruta(data, tenant_id=None):
    db = repo.get_db()
    try:
        payload = dict(data)
        cursos = payload.pop("cursos", [])
        payload["tenant_id"] = tenant_id or payload.get("tenant_id") or "default"
        if "departamentos" in payload:
            payload["departamentos_json"] = json.dumps(payload.pop("departamentos") or [])
        ruta = repo.create_ruta(db, payload)
        for idx, curso in enumerate(cursos):
            repo.create_ruta_curso(
                db,
                {
                    "tenant_id": payload["tenant_id"],
                    "ruta_id": ruta.id,
                    "curso_id": curso["curso_id"] if isinstance(curso, dict) else int(curso),
                    "orden": curso.get("orden", idx) if isinstance(curso, dict) else idx,
                    "obligatorio": curso.get("obligatorio", True) if isinstance(curso, dict) else True,
                },
            )
        db.commit()
        db.refresh(ruta)
        return {
            "id": ruta.id,
            "nombre": ruta.nombre,
            "descripcion": ruta.descripcion,
            "rol_objetivo": ruta.rol_objetivo,
            "puesto_objetivo": ruta.puesto_objetivo,
            "departamentos": _loads_list(ruta.departamentos_json),
            "cursos": [{"curso_id": item.curso_id, "orden": item.orden, "obligatorio": item.obligatorio} for item in ruta.cursos],
        }
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def list_rutas():
    db = repo.get_db()
    try:
        result = []
        for ruta in repo.list_rutas(db):
            result.append(
                {
                    "id": ruta.id,
                    "nombre": ruta.nombre,
                    "descripcion": ruta.descripcion,
                    "rol_objetivo": ruta.rol_objetivo,
                    "puesto_objetivo": ruta.puesto_objetivo,
                    "departamentos": _loads_list(ruta.departamentos_json),
                    "cursos": [{"curso_id": item.curso_id, "orden": item.orden, "obligatorio": item.obligatorio} for item in ruta.cursos],
                }
            )
        return result
    finally:
        db.close()


def delete_curso(curso_id, tenant_id=None, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        obj = repo.get_curso(db, curso_id)
        if obj:
            registrar_evento(
                db,
                "curso",
                obj.id,
                "deleted",
                actor_key=actor_key,
                actor_nombre=actor_name,
                tenant_id=obj.tenant_id,
                detalle={"nombre": obj.nombre},
            )
        ok = repo.delete_curso(db, curso_id)
        if not ok:
            return False
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def list_lecciones(curso_id, tenant_id=None):
    db = repo.get_db()
    try:
        return [_leccion_dict(item) for item in repo.list_lecciones(db, curso_id)]
    finally:
        db.close()


def get_leccion(leccion_id, tenant_id=None):
    db = repo.get_db()
    try:
        obj = repo.get_leccion(db, leccion_id)
        return _leccion_dict(obj) if obj else None
    finally:
        db.close()


def create_leccion(data, tenant_id=None, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        data = dict(data)
        if tenant_id:
            data["tenant_id"] = tenant_id
        obj = repo.create_leccion(db, data)
        db.commit()
        db.refresh(obj)
        return _leccion_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_leccion(leccion_id, data, tenant_id=None, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        obj = repo.update_leccion(db, leccion_id, data)
        if not obj:
            return None
        db.commit()
        db.refresh(obj)
        return _leccion_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_leccion(leccion_id, tenant_id=None, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        ok = repo.delete_leccion(db, leccion_id)
        if not ok:
            return False
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def reordenar_lecciones(curso_id, orden_ids, tenant_id=None, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        repo.reorder_lecciones(db, curso_id, orden_ids)
        db.commit()
        return [_leccion_dict(item) for item in repo.list_lecciones(db, curso_id)]
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()

"""Servicio CRUD — Categorías, Cursos y Lecciones."""
from __future__ import annotations

import string
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError

from fastapi_modulo.db import SessionLocal
from fastapi_modulo.modulos.capacitacion.cap_db_models import (
    CapCategoria,
    CapCurso,
    CapLeccion,
)


def _db():
    return SessionLocal()


def _dt(v) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v)


def _d(v) -> Optional[str]:
    if v is None:
        return None
    return str(v)


# ── Serializadores ─────────────────────────────────────────────────────────────

def _cat_dict(obj: CapCategoria) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "nombre": obj.nombre,
        "descripcion": obj.descripcion,
        "color": obj.color,
        "creado_en": _dt(obj.creado_en),
    }


def _curso_dict(obj: CapCurso, with_lecciones: bool = False) -> Dict[str, Any]:
    d = {
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
        "total_lecciones": len(obj.lecciones),
        "total_inscripciones": len(obj.inscripciones),
        "creado_en": _dt(obj.creado_en),
        "actualizado_en": _dt(obj.actualizado_en),
    }
    if with_lecciones:
        d["lecciones"] = [_leccion_dict(l) for l in obj.lecciones]
    return d


def _leccion_dict(obj: CapLeccion) -> Dict[str, Any]:
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


# ── Utilidad ────────────────────────────────────────────────────────────────────

def _gen_codigo() -> str:
    chars = string.ascii_uppercase + string.digits
    return "CAP-" + "".join(random.choices(chars, k=6))


# ── Categorías ──────────────────────────────────────────────────────────────────

def list_categorias() -> List[Dict]:
    db = _db()
    try:
        return [_cat_dict(o) for o in db.query(CapCategoria).order_by(CapCategoria.nombre).all()]
    finally:
        db.close()


def get_categoria(cat_id: int) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(CapCategoria).filter(CapCategoria.id == cat_id).first()
        return _cat_dict(obj) if obj else None
    finally:
        db.close()


def create_categoria(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        obj = CapCategoria(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return _cat_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_categoria(cat_id: int, data: Dict[str, Any]) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(CapCategoria).filter(CapCategoria.id == cat_id).first()
        if not obj:
            return None
        for k, v in data.items():
            setattr(obj, k, v)
        db.commit()
        db.refresh(obj)
        return _cat_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_categoria(cat_id: int) -> bool:
    db = _db()
    try:
        obj = db.query(CapCategoria).filter(CapCategoria.id == cat_id).first()
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


# ── Cursos ──────────────────────────────────────────────────────────────────────

def list_cursos(
    estado: Optional[str] = None,
    categoria_id: Optional[int] = None,
    nivel: Optional[str] = None,
) -> List[Dict]:
    db = _db()
    try:
        q = db.query(CapCurso)
        if estado:
            q = q.filter(CapCurso.estado == estado)
        if categoria_id:
            q = q.filter(CapCurso.categoria_id == categoria_id)
        if nivel:
            q = q.filter(CapCurso.nivel == nivel)
        return [_curso_dict(o) for o in q.order_by(CapCurso.id.desc()).all()]
    finally:
        db.close()


def get_curso(curso_id: int, with_lecciones: bool = False) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(CapCurso).filter(CapCurso.id == curso_id).first()
        return _curso_dict(obj, with_lecciones=with_lecciones) if obj else None
    finally:
        db.close()


def create_curso(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        # Generar código único
        for _ in range(10):
            codigo = _gen_codigo()
            if not db.query(CapCurso).filter(CapCurso.codigo == codigo).first():
                break
        data["codigo"] = codigo
        obj = CapCurso(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return _curso_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_curso(curso_id: int, data: Dict[str, Any]) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(CapCurso).filter(CapCurso.id == curso_id).first()
        if not obj:
            return None
        data.pop("codigo", None)  # no se cambia el código
        for k, v in data.items():
            setattr(obj, k, v)
        obj.actualizado_en = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return _curso_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_curso(curso_id: int) -> bool:
    db = _db()
    try:
        obj = db.query(CapCurso).filter(CapCurso.id == curso_id).first()
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


# ── Lecciones ───────────────────────────────────────────────────────────────────

def list_lecciones(curso_id: int) -> List[Dict]:
    db = _db()
    try:
        objs = (
            db.query(CapLeccion)
            .filter(CapLeccion.curso_id == curso_id)
            .order_by(CapLeccion.orden)
            .all()
        )
        return [_leccion_dict(o) for o in objs]
    finally:
        db.close()


def get_leccion(leccion_id: int) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(CapLeccion).filter(CapLeccion.id == leccion_id).first()
        return _leccion_dict(obj) if obj else None
    finally:
        db.close()


def create_leccion(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        obj = CapLeccion(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return _leccion_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_leccion(leccion_id: int, data: Dict[str, Any]) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(CapLeccion).filter(CapLeccion.id == leccion_id).first()
        if not obj:
            return None
        for k, v in data.items():
            setattr(obj, k, v)
        db.commit()
        db.refresh(obj)
        return _leccion_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_leccion(leccion_id: int) -> bool:
    db = _db()
    try:
        obj = db.query(CapLeccion).filter(CapLeccion.id == leccion_id).first()
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


def reordenar_lecciones(curso_id: int, orden_ids: List[int]) -> List[Dict]:
    """Recibe lista de leccion_id en el orden deseado y actualiza campo `orden`."""
    db = _db()
    try:
        for pos, lid in enumerate(orden_ids):
            db.query(CapLeccion).filter(
                CapLeccion.id == lid,
                CapLeccion.curso_id == curso_id,
            ).update({"orden": pos})
        db.commit()
        return list_lecciones(curso_id)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()

"""Servicio — Presentaciones tipo Genially."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError

from fastapi_modulo.db import SessionLocal
from fastapi_modulo.modulos.capacitacion.cap_db_models import (
    CapDiapositiva,
    CapElemento,
    CapPresentacion,
)


def _db():
    return SessionLocal()


def _dt(v) -> Optional[str]:
    if v is None:
        return None
    return v.isoformat() if isinstance(v, datetime) else str(v)


# ── Serializadores ──────────────────────────────────────────────────────────────

def _pres_dict(obj: CapPresentacion, include_diapositivas: bool = False) -> Dict[str, Any]:
    d = {
        "id":             obj.id,
        "titulo":         obj.titulo,
        "descripcion":    obj.descripcion,
        "autor_key":      obj.autor_key,
        "estado":         obj.estado,
        "curso_id":       obj.curso_id,
        "miniatura_url":  obj.miniatura_url,
        "num_diapositivas": len(obj.diapositivas) if obj.diapositivas else 0,
        "creado_en":      _dt(obj.creado_en),
        "actualizado_en": _dt(obj.actualizado_en),
    }
    if include_diapositivas:
        d["diapositivas"] = [_diap_dict(s) for s in sorted(obj.diapositivas, key=lambda s: s.orden)]
    return d


def _diap_dict(obj: CapDiapositiva, include_elementos: bool = False) -> Dict[str, Any]:
    d = {
        "id":              obj.id,
        "presentacion_id": obj.presentacion_id,
        "orden":           obj.orden,
        "titulo":          obj.titulo,
        "bg_color":        obj.bg_color or "#ffffff",
        "bg_image_url":    obj.bg_image_url,
        "notas":           obj.notas,
        "creado_en":       _dt(obj.creado_en),
    }
    if include_elementos:
        d["elementos"] = [_el_dict(e) for e in sorted(obj.elementos, key=lambda e: e.z_index)]
    return d


def _el_dict(obj: CapElemento) -> Dict[str, Any]:
    # Deserialize contenido_json if stored as string
    contenido = obj.contenido_json
    if isinstance(contenido, str):
        try:
            contenido = json.loads(contenido)
        except (json.JSONDecodeError, TypeError):
            contenido = {}
    return {
        "id":             obj.id,
        "diapositiva_id": obj.diapositiva_id,
        "tipo":           obj.tipo,
        "contenido_json": contenido or {},
        "pos_x":          obj.pos_x,
        "pos_y":          obj.pos_y,
        "width":          obj.width,
        "height":         obj.height,
        "z_index":        obj.z_index,
    }


# ── Presentaciones ────────────────────────────────────────────────────────────────

def list_presentaciones(
    autor_key: Optional[str] = None,
    estado: Optional[str] = None,
    curso_id: Optional[int] = None,
) -> List[Dict]:
    db = _db()
    try:
        q = db.query(CapPresentacion)
        if autor_key:
            q = q.filter(CapPresentacion.autor_key == autor_key)
        if estado:
            q = q.filter(CapPresentacion.estado == estado)
        if curso_id:
            q = q.filter(CapPresentacion.curso_id == curso_id)
        return [_pres_dict(o) for o in q.order_by(CapPresentacion.id.desc()).all()]
    finally:
        db.close()


def get_presentacion(pres_id: int) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(CapPresentacion).filter(CapPresentacion.id == pres_id).first()
        return _pres_dict(obj) if obj else None
    finally:
        db.close()


def create_presentacion(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        obj = CapPresentacion(
            titulo=data.get("titulo", "Nueva presentación"),
            descripcion=data.get("descripcion"),
            autor_key=data.get("autor_key"),
            estado=data.get("estado", "borrador"),
            curso_id=data.get("curso_id"),
            creado_en=datetime.utcnow(),
            actualizado_en=datetime.utcnow(),
        )
        db.add(obj)
        db.flush()
        # Create first blank slide automatically
        diap = CapDiapositiva(
            presentacion_id=obj.id,
            orden=0,
            titulo="Diapositiva 1",
            bg_color="#ffffff",
            creado_en=datetime.utcnow(),
        )
        db.add(diap)
        db.commit()
        db.refresh(obj)
        return _pres_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_presentacion(pres_id: int, data: Dict[str, Any]) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(CapPresentacion).filter(CapPresentacion.id == pres_id).first()
        if not obj:
            return None
        for field in ("titulo", "descripcion", "estado", "curso_id", "miniatura_url"):
            if field in data:
                setattr(obj, field, data[field])
        obj.actualizado_en = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return _pres_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_presentacion(pres_id: int) -> bool:
    db = _db()
    try:
        obj = db.query(CapPresentacion).filter(CapPresentacion.id == pres_id).first()
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


# ── Diapositivas ──────────────────────────────────────────────────────────────────

def list_diapositivas(pres_id: int) -> List[Dict]:
    db = _db()
    try:
        objs = (
            db.query(CapDiapositiva)
            .filter(CapDiapositiva.presentacion_id == pres_id)
            .order_by(CapDiapositiva.orden)
            .all()
        )
        return [_diap_dict(o, include_elementos=True) for o in objs]
    finally:
        db.close()


def create_diapositiva(pres_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        max_orden = db.query(CapDiapositiva).filter(
            CapDiapositiva.presentacion_id == pres_id
        ).count()
        obj = CapDiapositiva(
            presentacion_id=pres_id,
            orden=max_orden,
            titulo=data.get("titulo", f"Diapositiva {max_orden + 1}"),
            bg_color=data.get("bg_color", "#ffffff"),
            bg_image_url=data.get("bg_image_url"),
            notas=data.get("notas"),
            creado_en=datetime.utcnow(),
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return _diap_dict(obj, include_elementos=True)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_diapositiva(diap_id: int, data: Dict[str, Any]) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(CapDiapositiva).filter(CapDiapositiva.id == diap_id).first()
        if not obj:
            return None
        for field in ("titulo", "bg_color", "bg_image_url", "notas"):
            if field in data:
                setattr(obj, field, data[field])
        db.commit()
        db.refresh(obj)
        return _diap_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_diapositiva(diap_id: int) -> bool:
    db = _db()
    try:
        obj = db.query(CapDiapositiva).filter(CapDiapositiva.id == diap_id).first()
        if not obj:
            return False
        pres_id = obj.presentacion_id
        db.delete(obj)
        db.flush()
        # Re-number remaining slides
        remaining = (
            db.query(CapDiapositiva)
            .filter(CapDiapositiva.presentacion_id == pres_id)
            .order_by(CapDiapositiva.orden)
            .all()
        )
        for i, s in enumerate(remaining):
            s.orden = i
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def reordenar_diapositivas(pres_id: int, orden_ids: List[int]) -> bool:
    db = _db()
    try:
        for i, diap_id in enumerate(orden_ids):
            db.query(CapDiapositiva).filter(
                CapDiapositiva.id == diap_id,
                CapDiapositiva.presentacion_id == pres_id,
            ).update({"orden": i})
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def duplicate_diapositiva(diap_id: int) -> Optional[Dict]:
    db = _db()
    try:
        orig = db.query(CapDiapositiva).filter(CapDiapositiva.id == diap_id).first()
        if not orig:
            return None
        # Determine order right after orig
        subs = (
            db.query(CapDiapositiva)
            .filter(CapDiapositiva.presentacion_id == orig.presentacion_id)
            .order_by(CapDiapositiva.orden)
            .all()
        )
        new_orden = orig.orden + 1
        # Shift slides after
        for s in subs:
            if s.orden >= new_orden:
                s.orden += 1
        new_diap = CapDiapositiva(
            presentacion_id=orig.presentacion_id,
            orden=new_orden,
            titulo=(orig.titulo or "Diapositiva") + " (copia)",
            bg_color=orig.bg_color,
            bg_image_url=orig.bg_image_url,
            notas=orig.notas,
            creado_en=datetime.utcnow(),
        )
        db.add(new_diap)
        db.flush()
        # Copy elements
        for el in orig.elementos:
            new_el = CapElemento(
                diapositiva_id=new_diap.id,
                tipo=el.tipo,
                contenido_json=el.contenido_json,
                pos_x=el.pos_x,
                pos_y=el.pos_y,
                width=el.width,
                height=el.height,
                z_index=el.z_index,
                creado_en=datetime.utcnow(),
            )
            db.add(new_el)
        db.commit()
        db.refresh(new_diap)
        return _diap_dict(new_diap, include_elementos=True)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


# ── Elementos ─────────────────────────────────────────────────────────────────────

def list_elementos(diap_id: int) -> List[Dict]:
    db = _db()
    try:
        objs = (
            db.query(CapElemento)
            .filter(CapElemento.diapositiva_id == diap_id)
            .order_by(CapElemento.z_index)
            .all()
        )
        return [_el_dict(o) for o in objs]
    finally:
        db.close()


def save_elementos(diap_id: int, elementos: List[Dict[str, Any]]) -> List[Dict]:
    """Full replace — deletes all existing elements and inserts the given list."""
    db = _db()
    try:
        db.query(CapElemento).filter(CapElemento.diapositiva_id == diap_id).delete()
        nuevos = []
        for data in elementos:
            cj = data.get("contenido_json", {})
            if isinstance(cj, dict):
                cj = json.dumps(cj)
            obj = CapElemento(
                diapositiva_id=diap_id,
                tipo=data.get("tipo", "texto"),
                contenido_json=cj,
                pos_x=float(data.get("pos_x", 10)),
                pos_y=float(data.get("pos_y", 10)),
                width=float(data.get("width", 30)),
                height=float(data.get("height", 20)),
                z_index=int(data.get("z_index", 1)),
                creado_en=datetime.utcnow(),
            )
            db.add(obj)
            nuevos.append(obj)
        db.commit()
        for o in nuevos:
            db.refresh(o)
        return [_el_dict(o) for o in nuevos]
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()

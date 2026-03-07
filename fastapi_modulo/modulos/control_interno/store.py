from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from fastapi_modulo.db import SessionLocal
from fastapi_modulo.modulos.control_interno.models import ControlInterno


# ── helpers ───────────────────────────────────────────────────────────────────

def _db() -> Session:
    return SessionLocal()


def _to_dict(obj: ControlInterno) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "codigo": obj.codigo,
        "nombre": obj.nombre,
        "componente": obj.componente,
        "area": obj.area,
        "tipo_riesgo": obj.tipo_riesgo or "",
        "periodicidad": obj.periodicidad,
        "descripcion": obj.descripcion or "",
        "normativa": obj.normativa or "",
        "estado": obj.estado,
        "creado_en": obj.creado_en.isoformat() if obj.creado_en else "",
        "actualizado_en": obj.actualizado_en.isoformat() if obj.actualizado_en else "",
    }


# ── CRUD ──────────────────────────────────────────────────────────────────────

def listar_controles(componente: Optional[str] = None, area: Optional[str] = None,
                     estado: Optional[str] = None) -> List[Dict[str, Any]]:
    db = _db()
    try:
        q = db.query(ControlInterno)
        if componente:
            q = q.filter(ControlInterno.componente == componente)
        if area:
            q = q.filter(ControlInterno.area == area)
        if estado:
            q = q.filter(ControlInterno.estado == estado)
        return [_to_dict(r) for r in q.order_by(ControlInterno.codigo).all()]
    finally:
        db.close()


def obtener_control(control_id: int) -> Optional[Dict[str, Any]]:
    db = _db()
    try:
        obj = db.query(ControlInterno).filter(ControlInterno.id == control_id).first()
        return _to_dict(obj) if obj else None
    finally:
        db.close()


def crear_control(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        now = datetime.utcnow()
        obj = ControlInterno(
            codigo=data["codigo"].strip().upper(),
            nombre=data["nombre"].strip(),
            componente=data["componente"],
            area=data["area"].strip(),
            tipo_riesgo=(data.get("tipo_riesgo") or "").strip() or None,
            periodicidad=data.get("periodicidad", "Mensual"),
            descripcion=(data.get("descripcion") or "").strip() or None,
            normativa=(data.get("normativa") or "").strip() or None,
            estado=data.get("estado", "Activo"),
            creado_en=now,
            actualizado_en=now,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return _to_dict(obj)
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def actualizar_control(control_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db = _db()
    try:
        obj = db.query(ControlInterno).filter(ControlInterno.id == control_id).first()
        if not obj:
            return None
        campos = ["nombre", "componente", "area", "tipo_riesgo", "periodicidad",
                  "descripcion", "normativa", "estado"]
        for campo in campos:
            if campo in data:
                val = data[campo]
                setattr(obj, campo, (val.strip() if isinstance(val, str) else val) or None
                        if campo in ("tipo_riesgo", "descripcion", "normativa") else
                        (val.strip() if isinstance(val, str) else val))
        if "codigo" in data:
            obj.codigo = data["codigo"].strip().upper()
        obj.actualizado_en = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return _to_dict(obj)
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def eliminar_control(control_id: int) -> bool:
    db = _db()
    try:
        obj = db.query(ControlInterno).filter(ControlInterno.id == control_id).first()
        if not obj:
            return False
        db.delete(obj)
        db.commit()
        return True
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def opciones_filtro() -> Dict[str, List[str]]:
    """Devuelve los valores únicos de componente y área para los filtros."""
    db = _db()
    try:
        componentes = [r.componente for r in db.query(ControlInterno.componente).distinct().all()]
        areas = [r.area for r in db.query(ControlInterno.area).distinct().all()]
        return {"componentes": sorted(set(componentes)), "areas": sorted(set(areas))}
    finally:
        db.close()

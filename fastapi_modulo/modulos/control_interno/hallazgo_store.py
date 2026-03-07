from __future__ import annotations

from datetime import datetime, date
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError

from fastapi_modulo.db import SessionLocal
from fastapi_modulo.modulos.control_interno.hallazgo_models import Hallazgo, AccionCorrectiva


def _db() -> Session:
    return SessionLocal()


def _parse_date(val: Any) -> Optional[date]:
    if not val:
        return None
    if isinstance(val, date):
        return val
    try:
        return date.fromisoformat(str(val))
    except ValueError:
        return None


# ── Serializers ───────────────────────────────────────────────────────────────

def _hallazgo_dict(h: Hallazgo, include_acciones: bool = False) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "id":              h.id,
        "evidencia_id":    h.evidencia_id,
        "actividad_id":    h.actividad_id,
        "control_id":      h.control_id,
        "codigo":          h.codigo or "",
        "titulo":          h.titulo,
        "descripcion":     h.descripcion or "",
        "causa":           h.causa or "",
        "efecto":          h.efecto or "",
        "componente_coso": h.componente_coso or "",
        "nivel_riesgo":    h.nivel_riesgo,
        "estado":          h.estado,
        "fecha_deteccion": h.fecha_deteccion.isoformat() if h.fecha_deteccion else "",
        "fecha_limite":    h.fecha_limite.isoformat() if h.fecha_limite else "",
        "responsable":     h.responsable or "",
        "creado_en":       h.creado_en.isoformat() if h.creado_en else "",
        "actualizado_en":  h.actualizado_en.isoformat() if h.actualizado_en else "",
        "control_codigo":  h.control.codigo if h.control else "",
        "control_nombre":  h.control.nombre if h.control else "",
        "total_acciones":  len(h.acciones) if h.acciones else 0,
    }
    if include_acciones:
        d["acciones"] = [_accion_dict(a) for a in (h.acciones or [])]
    return d


def _accion_dict(a: AccionCorrectiva) -> Dict[str, Any]:
    return {
        "id":                    a.id,
        "hallazgo_id":           a.hallazgo_id,
        "descripcion":           a.descripcion,
        "responsable":           a.responsable or "",
        "fecha_compromiso":      a.fecha_compromiso.isoformat() if a.fecha_compromiso else "",
        "fecha_ejecucion":       a.fecha_ejecucion.isoformat() if a.fecha_ejecucion else "",
        "estado":                a.estado,
        "evidencia_seguimiento": a.evidencia_seguimiento or "",
        "creado_en":             a.creado_en.isoformat() if a.creado_en else "",
        "actualizado_en":        a.actualizado_en.isoformat() if a.actualizado_en else "",
    }


# ── Hallazgos ─────────────────────────────────────────────────────────────────

def listar_hallazgos(
    nivel_riesgo:    Optional[str] = None,
    estado:          Optional[str] = None,
    control_id:      Optional[int] = None,
    componente_coso: Optional[str] = None,
    q:               Optional[str] = None,
) -> List[Dict[str, Any]]:
    db = _db()
    try:
        query = (db.query(Hallazgo)
                   .options(joinedload(Hallazgo.control),
                            joinedload(Hallazgo.acciones)))
        if nivel_riesgo:
            query = query.filter(Hallazgo.nivel_riesgo == nivel_riesgo)
        if estado:
            query = query.filter(Hallazgo.estado == estado)
        if control_id:
            query = query.filter(Hallazgo.control_id == control_id)
        if componente_coso:
            query = query.filter(Hallazgo.componente_coso == componente_coso)
        hallazgos = query.order_by(Hallazgo.fecha_deteccion.desc().nullslast(),
                                   Hallazgo.creado_en.desc()).all()
        result = [_hallazgo_dict(h) for h in hallazgos]
        if q:
            ql = q.lower()
            result = [
                h for h in result
                if ql in h["titulo"].lower()
                or ql in h["codigo"].lower()
                or ql in h["descripcion"].lower()
                or ql in h["responsable"].lower()
            ]
        return result
    finally:
        db.close()


def obtener_hallazgo(hallazgo_id: int) -> Optional[Dict[str, Any]]:
    db = _db()
    try:
        h = (db.query(Hallazgo)
               .options(joinedload(Hallazgo.control),
                        joinedload(Hallazgo.acciones))
               .filter(Hallazgo.id == hallazgo_id).first())
        return _hallazgo_dict(h, include_acciones=True) if h else None
    finally:
        db.close()


def crear_hallazgo(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        now = datetime.utcnow()
        h = Hallazgo(
            evidencia_id=int(data["evidencia_id"]) if data.get("evidencia_id") else None,
            actividad_id=int(data["actividad_id"]) if data.get("actividad_id") else None,
            control_id=int(data["control_id"]) if data.get("control_id") else None,
            codigo=(data.get("codigo") or "").strip().upper() or None,
            titulo=data["titulo"].strip(),
            descripcion=(data.get("descripcion") or "").strip() or None,
            causa=(data.get("causa") or "").strip() or None,
            efecto=(data.get("efecto") or "").strip() or None,
            componente_coso=(data.get("componente_coso") or "").strip() or None,
            nivel_riesgo=data.get("nivel_riesgo", "Medio"),
            estado=data.get("estado", "Abierto"),
            fecha_deteccion=_parse_date(data.get("fecha_deteccion")),
            fecha_limite=_parse_date(data.get("fecha_limite")),
            responsable=(data.get("responsable") or "").strip() or None,
            creado_en=now,
            actualizado_en=now,
        )
        db.add(h)
        db.commit()
        db.refresh(h)
        h = (db.query(Hallazgo)
               .options(joinedload(Hallazgo.control), joinedload(Hallazgo.acciones))
               .filter(Hallazgo.id == h.id).first())
        return _hallazgo_dict(h, include_acciones=True)
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def actualizar_hallazgo(hallazgo_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db = _db()
    try:
        h = (db.query(Hallazgo)
               .options(joinedload(Hallazgo.control), joinedload(Hallazgo.acciones))
               .filter(Hallazgo.id == hallazgo_id).first())
        if not h:
            return None
        simple = ["titulo", "descripcion", "causa", "efecto",
                  "componente_coso", "nivel_riesgo", "estado", "responsable"]
        for campo in simple:
            if campo in data:
                val = (data[campo] or "").strip() or None
                setattr(h, campo, val)
        if "codigo" in data:
            h.codigo = (data["codigo"] or "").strip().upper() or None
        if "control_id" in data:
            h.control_id = int(data["control_id"]) if data["control_id"] else None
        if "evidencia_id" in data:
            h.evidencia_id = int(data["evidencia_id"]) if data["evidencia_id"] else None
        if "actividad_id" in data:
            h.actividad_id = int(data["actividad_id"]) if data["actividad_id"] else None
        for fld in ("fecha_deteccion", "fecha_limite"):
            if fld in data:
                setattr(h, fld, _parse_date(data[fld]))
        h.actualizado_en = datetime.utcnow()
        db.commit()
        db.refresh(h)
        h = (db.query(Hallazgo)
               .options(joinedload(Hallazgo.control), joinedload(Hallazgo.acciones))
               .filter(Hallazgo.id == h.id).first())
        return _hallazgo_dict(h, include_acciones=True)
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def eliminar_hallazgo(hallazgo_id: int) -> bool:
    db = _db()
    try:
        h = db.query(Hallazgo).filter(Hallazgo.id == hallazgo_id).first()
        if not h:
            return False
        db.delete(h)
        db.commit()
        return True
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


# ── Acciones correctivas ──────────────────────────────────────────────────────

def listar_acciones(hallazgo_id: int) -> List[Dict[str, Any]]:
    db = _db()
    try:
        acciones = (db.query(AccionCorrectiva)
                      .filter(AccionCorrectiva.hallazgo_id == hallazgo_id)
                      .order_by(AccionCorrectiva.fecha_compromiso)
                      .all())
        return [_accion_dict(a) for a in acciones]
    finally:
        db.close()


def crear_accion(hallazgo_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        now = datetime.utcnow()
        a = AccionCorrectiva(
            hallazgo_id=hallazgo_id,
            descripcion=data["descripcion"].strip(),
            responsable=(data.get("responsable") or "").strip() or None,
            fecha_compromiso=_parse_date(data.get("fecha_compromiso")),
            fecha_ejecucion=_parse_date(data.get("fecha_ejecucion")),
            estado=data.get("estado", "Pendiente"),
            evidencia_seguimiento=(data.get("evidencia_seguimiento") or "").strip() or None,
            creado_en=now,
            actualizado_en=now,
        )
        db.add(a)
        db.commit()
        db.refresh(a)
        return _accion_dict(a)
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def actualizar_accion(accion_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db = _db()
    try:
        a = db.query(AccionCorrectiva).filter(AccionCorrectiva.id == accion_id).first()
        if not a:
            return None
        if "descripcion" in data:
            a.descripcion = data["descripcion"].strip()
        if "responsable" in data:
            a.responsable = (data["responsable"] or "").strip() or None
        if "estado" in data:
            a.estado = data["estado"]
        if "evidencia_seguimiento" in data:
            a.evidencia_seguimiento = (data["evidencia_seguimiento"] or "").strip() or None
        for fld in ("fecha_compromiso", "fecha_ejecucion"):
            if fld in data:
                setattr(a, fld, _parse_date(data[fld]))
        a.actualizado_en = datetime.utcnow()
        db.commit()
        db.refresh(a)
        return _accion_dict(a)
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def eliminar_accion(accion_id: int) -> bool:
    db = _db()
    try:
        a = db.query(AccionCorrectiva).filter(AccionCorrectiva.id == accion_id).first()
        if not a:
            return False
        db.delete(a)
        db.commit()
        return True
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


# ── Resumen ───────────────────────────────────────────────────────────────────

def resumen_hallazgos() -> Dict[str, Any]:
    db = _db()
    try:
        hallazgos = db.query(Hallazgo).all()
        total = len(hallazgos)
        por_estado: Dict[str, int] = {}
        por_riesgo: Dict[str, int] = {}
        for h in hallazgos:
            por_estado[h.estado]       = por_estado.get(h.estado, 0) + 1
            por_riesgo[h.nivel_riesgo] = por_riesgo.get(h.nivel_riesgo, 0) + 1
        return {
            "total":      total,
            "por_estado": por_estado,
            "por_riesgo": por_riesgo,
        }
    finally:
        db.close()

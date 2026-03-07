from __future__ import annotations

from datetime import datetime, date
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError

from fastapi_modulo.db import SessionLocal
from fastapi_modulo.modulos.control_interno.programa_models import ProgramaAnual, ProgramaActividad


def _db() -> Session:
    return SessionLocal()


# ── serializers ───────────────────────────────────────────────────────────────

def _programa_dict(p: ProgramaAnual) -> Dict[str, Any]:
    return {
        "id":             p.id,
        "anio":           p.anio,
        "nombre":         p.nombre,
        "descripcion":    p.descripcion or "",
        "estado":         p.estado,
        "creado_en":      p.creado_en.isoformat() if p.creado_en else "",
        "actualizado_en": p.actualizado_en.isoformat() if p.actualizado_en else "",
    }


def _actividad_dict(a: ProgramaActividad, include_control: bool = True) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "id":                      a.id,
        "programa_id":             a.programa_id,
        "control_id":              a.control_id,
        "descripcion":             a.descripcion or "",
        "responsable":             a.responsable or "",
        "fecha_inicio_programada": a.fecha_inicio_programada.isoformat() if a.fecha_inicio_programada else "",
        "fecha_fin_programada":    a.fecha_fin_programada.isoformat() if a.fecha_fin_programada else "",
        "fecha_inicio_real":       a.fecha_inicio_real.isoformat() if a.fecha_inicio_real else "",
        "fecha_fin_real":          a.fecha_fin_real.isoformat() if a.fecha_fin_real else "",
        "estado":                  a.estado,
        "observaciones":           a.observaciones or "",
        "creado_en":               a.creado_en.isoformat() if a.creado_en else "",
        "actualizado_en":          a.actualizado_en.isoformat() if a.actualizado_en else "",
    }
    if include_control and a.control:
        d["control_codigo"] = a.control.codigo
        d["control_nombre"] = a.control.nombre
        d["control_componente"] = a.control.componente
    else:
        d["control_codigo"] = ""
        d["control_nombre"] = ""
        d["control_componente"] = ""
    return d


# ── Programas ─────────────────────────────────────────────────────────────────

def listar_programas(anio: Optional[int] = None) -> List[Dict[str, Any]]:
    db = _db()
    try:
        q = db.query(ProgramaAnual)
        if anio:
            q = q.filter(ProgramaAnual.anio == anio)
        return [_programa_dict(p) for p in q.order_by(ProgramaAnual.anio.desc()).all()]
    finally:
        db.close()


def obtener_programa(programa_id: int) -> Optional[Dict[str, Any]]:
    db = _db()
    try:
        p = db.query(ProgramaAnual).filter(ProgramaAnual.id == programa_id).first()
        return _programa_dict(p) if p else None
    finally:
        db.close()


def crear_programa(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        now = datetime.utcnow()
        p = ProgramaAnual(
            anio=int(data["anio"]),
            nombre=data["nombre"].strip(),
            descripcion=(data.get("descripcion") or "").strip() or None,
            estado=data.get("estado", "Borrador"),
            creado_en=now,
            actualizado_en=now,
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        return _programa_dict(p)
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def actualizar_programa(programa_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db = _db()
    try:
        p = db.query(ProgramaAnual).filter(ProgramaAnual.id == programa_id).first()
        if not p:
            return None
        if "anio" in data:
            p.anio = int(data["anio"])
        if "nombre" in data:
            p.nombre = data["nombre"].strip()
        if "descripcion" in data:
            p.descripcion = (data["descripcion"] or "").strip() or None
        if "estado" in data:
            p.estado = data["estado"]
        p.actualizado_en = datetime.utcnow()
        db.commit()
        db.refresh(p)
        return _programa_dict(p)
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def eliminar_programa(programa_id: int) -> bool:
    db = _db()
    try:
        p = db.query(ProgramaAnual).filter(ProgramaAnual.id == programa_id).first()
        if not p:
            return False
        db.delete(p)
        db.commit()
        return True
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


# ── Actividades ───────────────────────────────────────────────────────────────

def listar_actividades(programa_id: int,
                        estado: Optional[str] = None) -> List[Dict[str, Any]]:
    db = _db()
    try:
        q = (db.query(ProgramaActividad)
               .options(joinedload(ProgramaActividad.control))
               .filter(ProgramaActividad.programa_id == programa_id))
        if estado:
            q = q.filter(ProgramaActividad.estado == estado)
        return [_actividad_dict(a) for a in
                q.order_by(ProgramaActividad.fecha_inicio_programada).all()]
    finally:
        db.close()


def obtener_actividad(actividad_id: int) -> Optional[Dict[str, Any]]:
    db = _db()
    try:
        a = (db.query(ProgramaActividad)
               .options(joinedload(ProgramaActividad.control))
               .filter(ProgramaActividad.id == actividad_id).first())
        return _actividad_dict(a) if a else None
    finally:
        db.close()


def _parse_date(val: Any) -> Optional[date]:
    if not val:
        return None
    if isinstance(val, date):
        return val
    try:
        return date.fromisoformat(str(val))
    except ValueError:
        return None


def crear_actividad(programa_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        now = datetime.utcnow()
        a = ProgramaActividad(
            programa_id=programa_id,
            control_id=int(data["control_id"]) if data.get("control_id") else None,
            descripcion=(data.get("descripcion") or "").strip() or None,
            responsable=(data.get("responsable") or "").strip() or None,
            fecha_inicio_programada=_parse_date(data.get("fecha_inicio_programada")),
            fecha_fin_programada=_parse_date(data.get("fecha_fin_programada")),
            fecha_inicio_real=_parse_date(data.get("fecha_inicio_real")),
            fecha_fin_real=_parse_date(data.get("fecha_fin_real")),
            estado=data.get("estado", "Programado"),
            observaciones=(data.get("observaciones") or "").strip() or None,
            creado_en=now,
            actualizado_en=now,
        )
        db.add(a)
        db.commit()
        db.refresh(a)
        # reload with relation
        a = (db.query(ProgramaActividad)
               .options(joinedload(ProgramaActividad.control))
               .filter(ProgramaActividad.id == a.id).first())
        return _actividad_dict(a)
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def actualizar_actividad(actividad_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db = _db()
    try:
        a = (db.query(ProgramaActividad)
               .options(joinedload(ProgramaActividad.control))
               .filter(ProgramaActividad.id == actividad_id).first())
        if not a:
            return None
        if "control_id" in data:
            a.control_id = int(data["control_id"]) if data["control_id"] else None
        if "descripcion" in data:
            a.descripcion = (data["descripcion"] or "").strip() or None
        if "responsable" in data:
            a.responsable = (data["responsable"] or "").strip() or None
        for fld in ("fecha_inicio_programada", "fecha_fin_programada",
                    "fecha_inicio_real", "fecha_fin_real"):
            if fld in data:
                setattr(a, fld, _parse_date(data[fld]))
        if "estado" in data:
            a.estado = data["estado"]
        if "observaciones" in data:
            a.observaciones = (data["observaciones"] or "").strip() or None
        a.actualizado_en = datetime.utcnow()
        db.commit()
        db.refresh(a)
        a = (db.query(ProgramaActividad)
               .options(joinedload(ProgramaActividad.control))
               .filter(ProgramaActividad.id == a.id).first())
        return _actividad_dict(a)
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def eliminar_actividad(actividad_id: int) -> bool:
    db = _db()
    try:
        a = db.query(ProgramaActividad).filter(ProgramaActividad.id == actividad_id).first()
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


def resumen_programa(programa_id: int) -> Dict[str, Any]:
    """Contadores de estado para el tablero del programa."""
    db = _db()
    try:
        actividades = db.query(ProgramaActividad).filter(
            ProgramaActividad.programa_id == programa_id).all()
        total = len(actividades)
        conteo: Dict[str, int] = {}
        for a in actividades:
            conteo[a.estado] = conteo.get(a.estado, 0) + 1
        completado = conteo.get("Completado", 0)
        pct = round(completado * 100 / total) if total else 0
        return {
            "total":       total,
            "conteo":      conteo,
            "completado":  completado,
            "porcentaje":  pct,
        }
    finally:
        db.close()

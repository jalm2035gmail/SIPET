from __future__ import annotations

import os
from datetime import datetime, date
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError

from fastapi_modulo.db import SessionLocal
from fastapi_modulo.modulos.control_interno.evidencia_models import Evidencia

UPLOAD_DIR = "fastapi_modulo/uploads/documentos"


def _db() -> Session:
    return SessionLocal()


def _to_dict(e: Evidencia) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "id":                   e.id,
        "actividad_id":         e.actividad_id,
        "control_id":           e.control_id,
        "titulo":               e.titulo,
        "tipo":                 e.tipo,
        "descripcion":          e.descripcion or "",
        "fecha_evidencia":      e.fecha_evidencia.isoformat() if e.fecha_evidencia else "",
        "resultado_evaluacion": e.resultado_evaluacion,
        "observaciones":        e.observaciones or "",
        "archivo_nombre":       e.archivo_nombre or "",
        "archivo_mime":         e.archivo_mime or "",
        "archivo_tamanio":      e.archivo_tamanio or 0,
        "tiene_archivo":        bool(e.archivo_ruta and os.path.exists(e.archivo_ruta)),
        "creado_en":            e.creado_en.isoformat() if e.creado_en else "",
        "actualizado_en":       e.actualizado_en.isoformat() if e.actualizado_en else "",
    }
    # Vínculos enriquecidos
    if e.actividad:
        d["actividad_desc"] = (e.actividad.descripcion or "")[:80]
    else:
        d["actividad_desc"] = ""
    if e.control:
        d["control_codigo"] = e.control.codigo
        d["control_nombre"] = e.control.nombre
    else:
        d["control_codigo"] = ""
        d["control_nombre"] = ""
    return d


def _parse_date(val: Any) -> Optional[date]:
    if not val:
        return None
    if isinstance(val, date):
        return val
    try:
        return date.fromisoformat(str(val))
    except ValueError:
        return None


# ── Listar ────────────────────────────────────────────────────────────────────

def listar_evidencias(
    actividad_id:         Optional[int] = None,
    control_id:           Optional[int] = None,
    tipo:                 Optional[str] = None,
    resultado_evaluacion: Optional[str] = None,
    q:                    Optional[str] = None,
) -> List[Dict[str, Any]]:
    db = _db()
    try:
        query = (db.query(Evidencia)
                   .options(joinedload(Evidencia.actividad),
                            joinedload(Evidencia.control)))
        if actividad_id:
            query = query.filter(Evidencia.actividad_id == actividad_id)
        if control_id:
            query = query.filter(Evidencia.control_id == control_id)
        if tipo:
            query = query.filter(Evidencia.tipo == tipo)
        if resultado_evaluacion:
            query = query.filter(Evidencia.resultado_evaluacion == resultado_evaluacion)
        evidencias = query.order_by(Evidencia.fecha_evidencia.desc().nullslast(),
                                    Evidencia.creado_en.desc()).all()
        result = [_to_dict(e) for e in evidencias]
        if q:
            q_lower = q.lower()
            result = [
                e for e in result
                if q_lower in e["titulo"].lower()
                or q_lower in e["descripcion"].lower()
                or q_lower in e["control_codigo"].lower()
                or q_lower in e["actividad_desc"].lower()
            ]
        return result
    finally:
        db.close()


def obtener_evidencia(evidencia_id: int) -> Optional[Dict[str, Any]]:
    db = _db()
    try:
        e = (db.query(Evidencia)
               .options(joinedload(Evidencia.actividad),
                        joinedload(Evidencia.control))
               .filter(Evidencia.id == evidencia_id).first())
        return _to_dict(e) if e else None
    finally:
        db.close()


def obtener_ruta_archivo(evidencia_id: int) -> Optional[str]:
    """Devuelve la ruta interna del archivo adjunto o None."""
    db = _db()
    try:
        e = db.query(Evidencia).filter(Evidencia.id == evidencia_id).first()
        if e and e.archivo_ruta:
            return e.archivo_ruta
        return None
    finally:
        db.close()


# ── Crear / Actualizar / Eliminar ─────────────────────────────────────────────

def crear_evidencia(data: Dict[str, Any],
                    archivo_nombre: Optional[str] = None,
                    archivo_ruta:   Optional[str] = None,
                    archivo_mime:   Optional[str] = None,
                    archivo_tamanio: Optional[int] = None) -> Dict[str, Any]:
    db = _db()
    try:
        now = datetime.utcnow()
        e = Evidencia(
            actividad_id=int(data["actividad_id"]) if data.get("actividad_id") else None,
            control_id=int(data["control_id"]) if data.get("control_id") else None,
            titulo=data["titulo"].strip(),
            tipo=data.get("tipo", "Documento"),
            descripcion=(data.get("descripcion") or "").strip() or None,
            fecha_evidencia=_parse_date(data.get("fecha_evidencia")),
            resultado_evaluacion=data.get("resultado_evaluacion", "Por evaluar"),
            observaciones=(data.get("observaciones") or "").strip() or None,
            archivo_nombre=archivo_nombre,
            archivo_ruta=archivo_ruta,
            archivo_mime=archivo_mime,
            archivo_tamanio=archivo_tamanio,
            creado_en=now,
            actualizado_en=now,
        )
        db.add(e)
        db.commit()
        db.refresh(e)
        e = (db.query(Evidencia)
               .options(joinedload(Evidencia.actividad), joinedload(Evidencia.control))
               .filter(Evidencia.id == e.id).first())
        return _to_dict(e)
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def actualizar_evidencia(evidencia_id: int, data: Dict[str, Any],
                          archivo_nombre: Optional[str] = None,
                          archivo_ruta:   Optional[str] = None,
                          archivo_mime:   Optional[str] = None,
                          archivo_tamanio: Optional[int] = None) -> Optional[Dict[str, Any]]:
    db = _db()
    try:
        e = (db.query(Evidencia)
               .options(joinedload(Evidencia.actividad), joinedload(Evidencia.control))
               .filter(Evidencia.id == evidencia_id).first())
        if not e:
            return None
        old_ruta = e.archivo_ruta

        if "actividad_id" in data:
            e.actividad_id = int(data["actividad_id"]) if data["actividad_id"] else None
        if "control_id" in data:
            e.control_id = int(data["control_id"]) if data["control_id"] else None
        if "titulo" in data:
            e.titulo = data["titulo"].strip()
        if "tipo" in data:
            e.tipo = data["tipo"]
        if "descripcion" in data:
            e.descripcion = (data["descripcion"] or "").strip() or None
        if "fecha_evidencia" in data:
            e.fecha_evidencia = _parse_date(data["fecha_evidencia"])
        if "resultado_evaluacion" in data:
            e.resultado_evaluacion = data["resultado_evaluacion"]
        if "observaciones" in data:
            e.observaciones = (data["observaciones"] or "").strip() or None
        if archivo_ruta:
            # Eliminar archivo anterior si hay uno nuevo
            _delete_file(old_ruta)
            e.archivo_nombre  = archivo_nombre
            e.archivo_ruta    = archivo_ruta
            e.archivo_mime    = archivo_mime
            e.archivo_tamanio = archivo_tamanio
        e.actualizado_en = datetime.utcnow()
        db.commit()
        db.refresh(e)
        e = (db.query(Evidencia)
               .options(joinedload(Evidencia.actividad), joinedload(Evidencia.control))
               .filter(Evidencia.id == e.id).first())
        return _to_dict(e)
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def eliminar_evidencia(evidencia_id: int) -> bool:
    db = _db()
    try:
        e = db.query(Evidencia).filter(Evidencia.id == evidencia_id).first()
        if not e:
            return False
        _delete_file(e.archivo_ruta)
        db.delete(e)
        db.commit()
        return True
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def _delete_file(path: Optional[str]) -> None:
    if not path:
        return
    safe_root = os.path.abspath(UPLOAD_DIR)
    target = os.path.abspath(path)
    if target.startswith(safe_root) and os.path.exists(target):
        os.remove(target)


# ── Resumen por control ───────────────────────────────────────────────────────

def resumen_por_resultado() -> Dict[str, int]:
    db = _db()
    try:
        rows = db.query(Evidencia.resultado_evaluacion).all()
        conteo: Dict[str, int] = {}
        for (r,) in rows:
            conteo[r] = conteo.get(r, 0) + 1
        return conteo
    finally:
        db.close()

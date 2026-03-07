from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError

from fastapi_modulo.db import Base, SessionLocal, engine
from fastapi_modulo.modulos.auditoria.aud_db_models import (
    AudAuditoria,
    AudHallazgo,
    AudRecomendacion,
    AudSeguimiento,
)

_AUD_TABLES = [
    AudAuditoria.__table__,
    AudHallazgo.__table__,
    AudRecomendacion.__table__,
    AudSeguimiento.__table__,
]


def ensure_aud_schema() -> None:
    Base.metadata.create_all(bind=engine, tables=_AUD_TABLES, checkfirst=True)


def _db():
    ensure_aud_schema()
    return SessionLocal()


def _date_str(v) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return str(v)


# ── Serializers ───────────────────────────────────────────────────────────────

def _auditoria_dict(obj: AudAuditoria) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "codigo": obj.codigo,
        "nombre": obj.nombre,
        "tipo": obj.tipo,
        "area_auditada": obj.area_auditada,
        "objetivo": obj.objetivo,
        "alcance": obj.alcance,
        "periodo": obj.periodo,
        "fecha_inicio": _date_str(obj.fecha_inicio),
        "fecha_fin_est": _date_str(obj.fecha_fin_est),
        "fecha_fin_real": _date_str(obj.fecha_fin_real),
        "estado": obj.estado,
        "responsable": obj.responsable,
        "auditor_lider": obj.auditor_lider,
        "creado_en": _date_str(obj.creado_en),
        "actualizado_en": _date_str(obj.actualizado_en),
    }


def _hallazgo_dict(obj: AudHallazgo) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "auditoria_id": obj.auditoria_id,
        "auditoria_nombre": obj.auditoria.nombre if obj.auditoria else None,
        "codigo": obj.codigo,
        "titulo": obj.titulo,
        "descripcion": obj.descripcion,
        "criterio": obj.criterio,
        "condicion": obj.condicion,
        "causa": obj.causa,
        "efecto": obj.efecto,
        "nivel_riesgo": obj.nivel_riesgo,
        "estado": obj.estado,
        "responsable": obj.responsable,
        "fecha_limite": _date_str(obj.fecha_limite),
        "creado_en": _date_str(obj.creado_en),
        "actualizado_en": _date_str(obj.actualizado_en),
    }


def _recomendacion_dict(obj: AudRecomendacion) -> Dict[str, Any]:
    h = obj.hallazgo
    return {
        "id": obj.id,
        "hallazgo_id": obj.hallazgo_id,
        "hallazgo_titulo": h.titulo if h else None,
        "auditoria_id": h.auditoria_id if h else None,
        "descripcion": obj.descripcion,
        "responsable": obj.responsable,
        "prioridad": obj.prioridad,
        "fecha_compromiso": _date_str(obj.fecha_compromiso),
        "estado": obj.estado,
        "porcentaje_avance": obj.porcentaje_avance,
        "creado_en": _date_str(obj.creado_en),
        "actualizado_en": _date_str(obj.actualizado_en),
    }


def _seguimiento_dict(obj: AudSeguimiento) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "recomendacion_id": obj.recomendacion_id,
        "fecha": _date_str(obj.fecha),
        "descripcion": obj.descripcion,
        "porcentaje_avance": obj.porcentaje_avance,
        "evidencia": obj.evidencia,
        "registrado_por": obj.registrado_por,
        "creado_en": _date_str(obj.creado_en),
    }


# ── Auditorías ────────────────────────────────────────────────────────────────

def list_auditorias(estado: Optional[str] = None, tipo: Optional[str] = None) -> List[Dict]:
    db = _db()
    try:
        q = db.query(AudAuditoria)
        if estado:
            q = q.filter(AudAuditoria.estado == estado)
        if tipo:
            q = q.filter(AudAuditoria.tipo == tipo)
        return [_auditoria_dict(o) for o in q.order_by(AudAuditoria.id.desc()).all()]
    finally:
        db.close()


def get_auditoria(auditoria_id: int) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(AudAuditoria).filter(AudAuditoria.id == auditoria_id).first()
        return _auditoria_dict(obj) if obj else None
    finally:
        db.close()


def create_auditoria(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        obj = AudAuditoria(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return _auditoria_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_auditoria(auditoria_id: int, data: Dict[str, Any]) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(AudAuditoria).filter(AudAuditoria.id == auditoria_id).first()
        if not obj:
            return None
        for k, v in data.items():
            setattr(obj, k, v)
        db.commit()
        db.refresh(obj)
        return _auditoria_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_auditoria(auditoria_id: int) -> bool:
    db = _db()
    try:
        obj = db.query(AudAuditoria).filter(AudAuditoria.id == auditoria_id).first()
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


# ── Hallazgos ─────────────────────────────────────────────────────────────────

def list_hallazgos(auditoria_id: Optional[int] = None,
                   nivel_riesgo: Optional[str] = None,
                   estado: Optional[str] = None) -> List[Dict]:
    db = _db()
    try:
        q = db.query(AudHallazgo)
        if auditoria_id:
            q = q.filter(AudHallazgo.auditoria_id == auditoria_id)
        if nivel_riesgo:
            q = q.filter(AudHallazgo.nivel_riesgo == nivel_riesgo)
        if estado:
            q = q.filter(AudHallazgo.estado == estado)
        return [_hallazgo_dict(o) for o in q.order_by(AudHallazgo.id.desc()).all()]
    finally:
        db.close()


def get_hallazgo(hallazgo_id: int) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(AudHallazgo).filter(AudHallazgo.id == hallazgo_id).first()
        return _hallazgo_dict(obj) if obj else None
    finally:
        db.close()


def create_hallazgo(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        obj = AudHallazgo(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        # reload with relationship
        obj = db.query(AudHallazgo).filter(AudHallazgo.id == obj.id).first()
        return _hallazgo_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_hallazgo(hallazgo_id: int, data: Dict[str, Any]) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(AudHallazgo).filter(AudHallazgo.id == hallazgo_id).first()
        if not obj:
            return None
        for k, v in data.items():
            setattr(obj, k, v)
        db.commit()
        obj = db.query(AudHallazgo).filter(AudHallazgo.id == hallazgo_id).first()
        return _hallazgo_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_hallazgo(hallazgo_id: int) -> bool:
    db = _db()
    try:
        obj = db.query(AudHallazgo).filter(AudHallazgo.id == hallazgo_id).first()
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


# ── Recomendaciones ───────────────────────────────────────────────────────────

def list_recomendaciones(hallazgo_id: Optional[int] = None,
                         estado: Optional[str] = None,
                         auditoria_id: Optional[int] = None) -> List[Dict]:
    db = _db()
    try:
        q = db.query(AudRecomendacion)
        if hallazgo_id:
            q = q.filter(AudRecomendacion.hallazgo_id == hallazgo_id)
        if estado:
            q = q.filter(AudRecomendacion.estado == estado)
        if auditoria_id:
            q = q.join(AudHallazgo).filter(AudHallazgo.auditoria_id == auditoria_id)
        return [_recomendacion_dict(o) for o in q.order_by(AudRecomendacion.id.desc()).all()]
    finally:
        db.close()


def get_recomendacion(rec_id: int) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(AudRecomendacion).filter(AudRecomendacion.id == rec_id).first()
        return _recomendacion_dict(obj) if obj else None
    finally:
        db.close()


def create_recomendacion(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        obj = AudRecomendacion(**data)
        db.add(obj)
        db.commit()
        obj = db.query(AudRecomendacion).filter(AudRecomendacion.id == obj.id).first()
        return _recomendacion_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_recomendacion(rec_id: int, data: Dict[str, Any]) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(AudRecomendacion).filter(AudRecomendacion.id == rec_id).first()
        if not obj:
            return None
        for k, v in data.items():
            setattr(obj, k, v)
        db.commit()
        obj = db.query(AudRecomendacion).filter(AudRecomendacion.id == rec_id).first()
        return _recomendacion_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_recomendacion(rec_id: int) -> bool:
    db = _db()
    try:
        obj = db.query(AudRecomendacion).filter(AudRecomendacion.id == rec_id).first()
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


# ── Seguimiento ───────────────────────────────────────────────────────────────

def list_seguimiento(recomendacion_id: Optional[int] = None) -> List[Dict]:
    db = _db()
    try:
        q = db.query(AudSeguimiento)
        if recomendacion_id:
            q = q.filter(AudSeguimiento.recomendacion_id == recomendacion_id)
        return [_seguimiento_dict(o) for o in q.order_by(AudSeguimiento.id.desc()).all()]
    finally:
        db.close()


def create_seguimiento(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        obj = AudSeguimiento(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        # After adding a seguimiento, update recomendacion.porcentaje_avance
        avance = data.get("porcentaje_avance", 0)
        rec = db.query(AudRecomendacion).filter(
            AudRecomendacion.id == data["recomendacion_id"]
        ).first()
        if rec and avance > rec.porcentaje_avance:
            rec.porcentaje_avance = avance
            if avance == 100:
                rec.estado = "implementada"
            db.commit()
        return _seguimiento_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_seguimiento(seg_id: int) -> bool:
    db = _db()
    try:
        obj = db.query(AudSeguimiento).filter(AudSeguimiento.id == seg_id).first()
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


# ── Resumen / KPIs ────────────────────────────────────────────────────────────

def get_aud_resumen() -> Dict[str, Any]:
    db = _db()
    try:
        total_auditorias   = db.query(AudAuditoria).count()
        en_proceso         = db.query(AudAuditoria).filter(AudAuditoria.estado == "en_proceso").count()
        total_hallazgos    = db.query(AudHallazgo).count()
        hallazgos_abiertos = db.query(AudHallazgo).filter(
            AudHallazgo.estado.in_(["abierto", "en_atencion"])
        ).count()
        hallazgos_criticos = db.query(AudHallazgo).filter(
            AudHallazgo.nivel_riesgo == "critico",
            AudHallazgo.estado != "cerrado",
        ).count()
        total_recs         = db.query(AudRecomendacion).count()
        recs_pendientes    = db.query(AudRecomendacion).filter(
            AudRecomendacion.estado.in_(["pendiente", "en_proceso"])
        ).count()
        recs_implementadas = db.query(AudRecomendacion).filter(
            AudRecomendacion.estado == "implementada"
        ).count()
        return {
            "total_auditorias": total_auditorias,
            "auditorias_en_proceso": en_proceso,
            "total_hallazgos": total_hallazgos,
            "hallazgos_abiertos": hallazgos_abiertos,
            "hallazgos_criticos": hallazgos_criticos,
            "total_recomendaciones": total_recs,
            "recomendaciones_pendientes": recs_pendientes,
            "recomendaciones_implementadas": recs_implementadas,
        }
    finally:
        db.close()

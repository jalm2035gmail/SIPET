from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError

from fastapi_modulo.db import MAIN, SessionLocal, engine
from fastapi_modulo.modulos.auditoria.modelos.aud_db_models import (
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
    MAIN.metadata.create_all(bind=engine, tables=_AUD_TABLES, checkfirst=True)


def _db():
    return SessionLocal()


ensure_aud_schema()


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
        avance = data.get("porcentaje_avance", 0)
        rec = db.query(AudRecomendacion).filter(
            AudRecomendacion.id == data["recomendacion_id"]
        ).first()
        if rec:
            changed = False
            # Actualizar porcentaje de avance si es mayor
            if avance > rec.porcentaje_avance:
                rec.porcentaje_avance = avance
                changed = True
            # Si avance llega a 100, cambiar estado a implementada
            if avance == 100 and rec.estado != "implementada":
                rec.estado = "implementada"
                changed = True
            # Si avance > 0 y estado es pendiente, cambiar a en_proceso
            if avance > 0 and rec.estado == "pendiente":
                rec.estado = "en_proceso"
                changed = True
            # Registrar fecha de última actualización
            rec.actualizado_en = obj.creado_en
            if changed:
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
        total_auditorias = db.query(AudAuditoria).count()
        auditorias_planificadas = db.query(AudAuditoria).filter(AudAuditoria.estado == "planificada").count()
        auditorias_en_proceso = db.query(AudAuditoria).filter(AudAuditoria.estado == "en_proceso").count()
        auditorias_informe = db.query(AudAuditoria).filter(AudAuditoria.estado == "informe").count()
        auditorias_cerradas = db.query(AudAuditoria).filter(AudAuditoria.estado == "cerrada").count()
        porcentaje_cerradas = (auditorias_cerradas / (auditorias_planificadas + auditorias_en_proceso + auditorias_informe + auditorias_cerradas) * 100) if (auditorias_planificadas + auditorias_en_proceso + auditorias_informe + auditorias_cerradas) > 0 else 0

        total_hallazgos = db.query(AudHallazgo).count()
        hallazgos_por_riesgo = {r: db.query(AudHallazgo).filter(AudHallazgo.nivel_riesgo == r).count() for r in ["bajo", "medio", "alto", "critico"]}
        hallazgos_abiertos = db.query(AudHallazgo).filter(AudHallazgo.estado.in_(["abierto", "en_atencion"])).count()
        hallazgos_vencidos = db.query(AudHallazgo).filter(AudHallazgo.fecha_limite != None, AudHallazgo.estado.in_(["abierto", "en_atencion"]), AudHallazgo.fecha_limite < date.today()).count()
        hallazgos_por_area = {}
        for area in db.query(AudAuditoria.area_auditada).distinct():
            area_val = area[0]
            if area_val:
                hallazgos_por_area[area_val] = db.query(AudHallazgo).join(AudAuditoria, AudHallazgo.auditoria_id == AudAuditoria.id).filter(AudAuditoria.area_auditada == area_val, AudHallazgo.estado.in_(["abierto", "en_atencion"])).count()

        total_recs = db.query(AudRecomendacion).count()
        recs_pendientes = db.query(AudRecomendacion).filter(AudRecomendacion.estado.in_(["pendiente", "en_proceso"])).count()
        recs_implementadas = db.query(AudRecomendacion).filter(AudRecomendacion.estado == "implementada").count()
        recs_vencidas = db.query(AudRecomendacion).filter(AudRecomendacion.fecha_compromiso != None, AudRecomendacion.estado.in_(["pendiente", "en_proceso"]), AudRecomendacion.fecha_compromiso < date.today()).count()
        recs_por_prioridad = {p: db.query(AudRecomendacion).filter(AudRecomendacion.prioridad == p).count() for p in ["alta", "media", "baja"]}
        recs_por_responsable = {}
        for responsable in db.query(AudRecomendacion.responsable).distinct():
            resp_val = responsable[0]
            if resp_val:
                recs_por_responsable[resp_val] = db.query(AudRecomendacion).filter(AudRecomendacion.responsable == resp_val).count()

        promedio_avance = db.query(AudRecomendacion.porcentaje_avance).all()
        porcentaje_promedio_avance = round(sum([r[0] for r in promedio_avance]) / len(promedio_avance), 2) if promedio_avance else 0

        tiempos_cierre = []
        for aud in db.query(AudAuditoria).filter(AudAuditoria.fecha_inicio != None, AudAuditoria.fecha_fin_real != None, AudAuditoria.estado == "cerrada").all():
            tiempos_cierre.append((aud.fecha_fin_real - aud.fecha_inicio).days)
        tiempo_promedio_cierre = round(sum(tiempos_cierre) / len(tiempos_cierre), 2) if tiempos_cierre else 0

        tiempos_impl = []
        for rec in db.query(AudRecomendacion).filter(AudRecomendacion.fecha_compromiso != None, AudRecomendacion.estado == "implementada").all():
            hallazgo = db.query(AudHallazgo).filter(AudHallazgo.id == rec.hallazgo_id).first()
            if hallazgo and hallazgo.fecha_limite:
                tiempos_impl.append((rec.fecha_compromiso - hallazgo.fecha_limite).days)
        tiempo_promedio_impl = round(sum(tiempos_impl) / len(tiempos_impl), 2) if tiempos_impl else 0

        return {
            "total_auditorias": total_auditorias,
            "auditorias_planificadas": auditorias_planificadas,
            "auditorias_en_proceso": auditorias_en_proceso,
            "auditorias_informe": auditorias_informe,
            "auditorias_cerradas": auditorias_cerradas,
            "porcentaje_cerradas": porcentaje_cerradas,
            "total_hallazgos": total_hallazgos,
            "hallazgos_por_riesgo": hallazgos_por_riesgo,
            "hallazgos_abiertos": hallazgos_abiertos,
            "hallazgos_vencidos": hallazgos_vencidos,
            "hallazgos_por_area": hallazgos_por_area,
            "total_recomendaciones": total_recs,
            "recomendaciones_pendientes": recs_pendientes,
            "recomendaciones_implementadas": recs_implementadas,
            "recomendaciones_vencidas": recs_vencidas,
            "recomendaciones_por_prioridad": recs_por_prioridad,
            "recomendaciones_por_responsable": recs_por_responsable,
            "porcentaje_promedio_avance": porcentaje_promedio_avance,
            "tiempo_promedio_cierre_auditoria": tiempo_promedio_cierre,
            "tiempo_promedio_implementacion_recomendacion": tiempo_promedio_impl,
        }
    finally:
        db.close()

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from fastapi_modulo.db import Base, SessionLocal, engine
from fastapi_modulo.modulos.crm.crm_db_models import (
    CrmActividad,
    CrmCampania,
    CrmContacto,
    CrmContactoCampania,
    CrmNota,
    CrmOportunidad,
)


# ── Inicialización de esquema ──────────────────────────────────────────────────

def ensure_crm_schema() -> None:
    Base.metadata.create_all(
        bind=engine,
        tables=[
            CrmContacto.__table__,
            CrmOportunidad.__table__,
            CrmActividad.__table__,
            CrmNota.__table__,
            CrmCampania.__table__,
            CrmContactoCampania.__table__,
        ],
        checkfirst=True,
    )


def _db() -> Session:
    ensure_crm_schema()
    return SessionLocal()


# ── Serializadores ─────────────────────────────────────────────────────────────

def _contacto_dict(obj: CrmContacto) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "nombre": obj.nombre,
        "email": obj.email or "",
        "telefono": obj.telefono,
        "empresa": obj.empresa,
        "puesto": obj.puesto,
        "tipo": obj.tipo,
        "fuente": obj.fuente,
        "notas": obj.notas or "",
        "creado_en": obj.creado_en.isoformat() if obj.creado_en else "",
        "actualizado_en": obj.actualizado_en.isoformat() if obj.actualizado_en else "",
    }


def _oportunidad_dict(obj: CrmOportunidad, contacto_nombre: str = "") -> Dict[str, Any]:
    return {
        "id": obj.id,
        "contacto_id": obj.contacto_id,
        "contacto_nombre": contacto_nombre,
        "nombre": obj.nombre,
        "etapa": obj.etapa,
        "valor_estimado": round(float(obj.valor_estimado or 0), 2),
        "probabilidad": obj.probabilidad,
        "fecha_cierre_est": obj.fecha_cierre_est.isoformat() if obj.fecha_cierre_est else "",
        "responsable": obj.responsable,
        "descripcion": obj.descripcion or "",
        "creado_en": obj.creado_en.isoformat() if obj.creado_en else "",
        "actualizado_en": obj.actualizado_en.isoformat() if obj.actualizado_en else "",
    }


def _actividad_dict(obj: CrmActividad) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "contacto_id": obj.contacto_id,
        "oportunidad_id": obj.oportunidad_id,
        "tipo": obj.tipo,
        "titulo": obj.titulo,
        "descripcion": obj.descripcion or "",
        "fecha": obj.fecha.isoformat() if obj.fecha else "",
        "completada": obj.completada,
        "responsable": obj.responsable,
        "creado_en": obj.creado_en.isoformat() if obj.creado_en else "",
    }


def _nota_dict(obj: CrmNota) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "contacto_id": obj.contacto_id,
        "oportunidad_id": obj.oportunidad_id,
        "contenido": obj.contenido,
        "autor": obj.autor,
        "creado_en": obj.creado_en.isoformat() if obj.creado_en else "",
    }


def _campania_dict(obj: CrmCampania) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "nombre": obj.nombre,
        "tipo": obj.tipo,
        "estado": obj.estado,
        "fecha_inicio": obj.fecha_inicio.isoformat() if obj.fecha_inicio else "",
        "fecha_fin": obj.fecha_fin.isoformat() if obj.fecha_fin else "",
        "descripcion": obj.descripcion or "",
        "creado_en": obj.creado_en.isoformat() if obj.creado_en else "",
    }


def _contacto_campania_dict(obj: CrmContactoCampania) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "contacto_id": obj.contacto_id,
        "campania_id": obj.campania_id,
        "estado": obj.estado,
    }


# ── Contactos ──────────────────────────────────────────────────────────────────

def list_contactos(tipo: Optional[str] = None) -> List[Dict[str, Any]]:
    db = _db()
    try:
        q = db.query(CrmContacto)
        if tipo:
            q = q.filter(CrmContacto.tipo == tipo)
        return [_contacto_dict(r) for r in q.order_by(CrmContacto.nombre).all()]
    finally:
        db.close()


def get_contacto(contacto_id: int) -> Optional[Dict[str, Any]]:
    db = _db()
    try:
        obj = db.query(CrmContacto).filter(CrmContacto.id == contacto_id).first()
        return _contacto_dict(obj) if obj else None
    finally:
        db.close()


def create_contacto(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        obj = CrmContacto(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return _contacto_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_contacto(contacto_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db = _db()
    try:
        obj = db.query(CrmContacto).filter(CrmContacto.id == contacto_id).first()
        if not obj:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        db.commit()
        db.refresh(obj)
        return _contacto_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_contacto(contacto_id: int) -> bool:
    db = _db()
    try:
        obj = db.query(CrmContacto).filter(CrmContacto.id == contacto_id).first()
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


# ── Oportunidades ─────────────────────────────────────────────────────────────

def list_oportunidades(contacto_id: Optional[int] = None, etapa: Optional[str] = None) -> List[Dict[str, Any]]:
    db = _db()
    try:
        q = db.query(CrmOportunidad, CrmContacto.nombre).outerjoin(
            CrmContacto, CrmOportunidad.contacto_id == CrmContacto.id
        )
        if contacto_id:
            q = q.filter(CrmOportunidad.contacto_id == contacto_id)
        if etapa:
            q = q.filter(CrmOportunidad.etapa == etapa)
        return [_oportunidad_dict(op, nombre or "") for op, nombre in q.order_by(CrmOportunidad.creado_en.desc()).all()]
    finally:
        db.close()


def create_oportunidad(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        obj = CrmOportunidad(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        contacto = db.query(CrmContacto).filter(CrmContacto.id == obj.contacto_id).first()
        return _oportunidad_dict(obj, contacto.nombre if contacto else "")
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_oportunidad(oportunidad_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db = _db()
    try:
        obj = db.query(CrmOportunidad).filter(CrmOportunidad.id == oportunidad_id).first()
        if not obj:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        db.commit()
        db.refresh(obj)
        contacto = db.query(CrmContacto).filter(CrmContacto.id == obj.contacto_id).first()
        return _oportunidad_dict(obj, contacto.nombre if contacto else "")
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_oportunidad(oportunidad_id: int) -> bool:
    db = _db()
    try:
        obj = db.query(CrmOportunidad).filter(CrmOportunidad.id == oportunidad_id).first()
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


# ── Actividades ───────────────────────────────────────────────────────────────

def list_actividades(
    contacto_id: Optional[int] = None,
    oportunidad_id: Optional[int] = None,
    completada: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    db = _db()
    try:
        q = db.query(CrmActividad)
        if contacto_id is not None:
            q = q.filter(CrmActividad.contacto_id == contacto_id)
        if oportunidad_id is not None:
            q = q.filter(CrmActividad.oportunidad_id == oportunidad_id)
        if completada is not None:
            q = q.filter(CrmActividad.completada == completada)
        return [_actividad_dict(r) for r in q.order_by(CrmActividad.fecha.desc()).all()]
    finally:
        db.close()


def create_actividad(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        obj = CrmActividad(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return _actividad_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_actividad(actividad_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db = _db()
    try:
        obj = db.query(CrmActividad).filter(CrmActividad.id == actividad_id).first()
        if not obj:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        db.commit()
        db.refresh(obj)
        return _actividad_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_actividad(actividad_id: int) -> bool:
    db = _db()
    try:
        obj = db.query(CrmActividad).filter(CrmActividad.id == actividad_id).first()
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


# ── Notas ─────────────────────────────────────────────────────────────────────

def list_notas(
    contacto_id: Optional[int] = None,
    oportunidad_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    db = _db()
    try:
        q = db.query(CrmNota)
        if contacto_id is not None:
            q = q.filter(CrmNota.contacto_id == contacto_id)
        if oportunidad_id is not None:
            q = q.filter(CrmNota.oportunidad_id == oportunidad_id)
        return [_nota_dict(r) for r in q.order_by(CrmNota.creado_en.desc()).all()]
    finally:
        db.close()


def create_nota(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        obj = CrmNota(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return _nota_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_nota(nota_id: int) -> bool:
    db = _db()
    try:
        obj = db.query(CrmNota).filter(CrmNota.id == nota_id).first()
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


# ── Campañas ──────────────────────────────────────────────────────────────────

def list_campanias(estado: Optional[str] = None) -> List[Dict[str, Any]]:
    db = _db()
    try:
        q = db.query(CrmCampania)
        if estado:
            q = q.filter(CrmCampania.estado == estado)
        return [_campania_dict(r) for r in q.order_by(CrmCampania.creado_en.desc()).all()]
    finally:
        db.close()


def create_campania(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        obj = CrmCampania(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return _campania_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_campania(campania_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db = _db()
    try:
        obj = db.query(CrmCampania).filter(CrmCampania.id == campania_id).first()
        if not obj:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        db.commit()
        db.refresh(obj)
        return _campania_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


# ── Contacto–Campaña ──────────────────────────────────────────────────────────

def list_contactos_campania(campania_id: int) -> List[Dict[str, Any]]:
    db = _db()
    try:
        rows = db.query(CrmContactoCampania).filter(
            CrmContactoCampania.campania_id == campania_id
        ).all()
        return [_contacto_campania_dict(r) for r in rows]
    finally:
        db.close()


def add_contacto_campania(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        obj = CrmContactoCampania(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return _contacto_campania_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


# ── Dashboard resumen ─────────────────────────────────────────────────────────

def get_crm_resumen() -> Dict[str, Any]:
    db = _db()
    try:
        total_contactos = db.query(CrmContacto).count()
        total_oportunidades = db.query(CrmOportunidad).count()
        oportunidades_abiertas = db.query(CrmOportunidad).filter(
            CrmOportunidad.etapa.notin_(["cerrado_ganado", "cerrado_perdido"])
        ).count()
        actividades_pendientes = db.query(CrmActividad).filter(
            CrmActividad.completada == False  # noqa: E712
        ).count()
        campanias_activas = db.query(CrmCampania).filter(
            CrmCampania.estado == "activa"
        ).count()
        return {
            "total_contactos": total_contactos,
            "total_oportunidades": total_oportunidades,
            "oportunidades_abiertas": oportunidades_abiertas,
            "actividades_pendientes": actividades_pendientes,
            "campanias_activas": campanias_activas,
        }
    finally:
        db.close()

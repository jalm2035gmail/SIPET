from __future__ import annotations

from typing import Optional

from fastapi_modulo.modulos.cartera_prestamos.modelos.db_models import (
    CpCastigoCredito,
    CpCredito,
    CpGestionCobranza,
    CpPromesaPago,
    CpReestructuraCredito,
)


def create_promesa_pago(db, data: dict) -> CpPromesaPago:
    obj = CpPromesaPago(**data)
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return obj


def get_promesa_pago(db, promesa_id: int) -> Optional[CpPromesaPago]:
    return db.query(CpPromesaPago).filter(CpPromesaPago.id == promesa_id).first()


def update_promesa_pago(db, obj: CpPromesaPago, data: dict) -> CpPromesaPago:
    for key, value in data.items():
        setattr(obj, key, value)
    db.flush()
    db.refresh(obj)
    return obj


def list_promesas_pago(db, *, credito_id: Optional[int] = None, estado: Optional[str] = None) -> list[CpPromesaPago]:
    query = db.query(CpPromesaPago)
    if credito_id:
        query = query.filter(CpPromesaPago.credito_id == credito_id)
    if estado:
        query = query.filter(CpPromesaPago.estado == estado)
    return query.order_by(CpPromesaPago.fecha_compromiso.asc(), CpPromesaPago.id.desc()).all()


def create_gestion(db, data: dict) -> CpGestionCobranza:
    obj = CpGestionCobranza(**data)
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return obj


def list_gestiones(db, *, credito_id: Optional[int] = None, responsable: Optional[str] = None) -> list[CpGestionCobranza]:
    query = db.query(CpGestionCobranza)
    if credito_id:
        query = query.filter(CpGestionCobranza.credito_id == credito_id)
    if responsable:
        query = query.filter(CpGestionCobranza.responsable == responsable)
    return query.order_by(CpGestionCobranza.fecha_gestion.desc()).all()


def create_castigo(db, data: dict) -> CpCastigoCredito:
    obj = CpCastigoCredito(**data)
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return obj


def create_reestructura(db, data: dict) -> CpReestructuraCredito:
    obj = CpReestructuraCredito(**data)
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return obj


def list_castigos(db, *, credito_id: Optional[int] = None) -> list[CpCastigoCredito]:
    query = db.query(CpCastigoCredito)
    if credito_id:
        query = query.filter(CpCastigoCredito.credito_id == credito_id)
    return query.order_by(CpCastigoCredito.fecha_castigo.desc(), CpCastigoCredito.id.desc()).all()


def list_reestructuras(db, *, credito_id: Optional[int] = None) -> list[CpReestructuraCredito]:
    query = db.query(CpReestructuraCredito)
    if credito_id:
        query = query.filter(CpReestructuraCredito.credito_id == credito_id)
    return query.order_by(CpReestructuraCredito.fecha_reestructura.desc(), CpReestructuraCredito.id.desc()).all()


def update_credito_estado(db, credito: CpCredito, *, estado: str, bucket_mora: Optional[str] = None, dias_mora: Optional[int] = None) -> CpCredito:
    credito.estado = estado
    if bucket_mora is not None:
        credito.bucket_mora = bucket_mora
    if dias_mora is not None:
        credito.dias_mora = dias_mora
    db.flush()
    db.refresh(credito)
    return credito

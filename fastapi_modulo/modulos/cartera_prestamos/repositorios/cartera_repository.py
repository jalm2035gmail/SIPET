from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import func

from fastapi_modulo.db import MAIN, SessionLocal, engine
from fastapi_modulo.modulos.cartera_prestamos.modelos.db_models import (
    CpCliente,
    CpCredito,
    CpIndicadorCartera,
    CpMoraCredito,
    CpSaldoCredito,
)


CARTERA_TABLES = [
    CpCliente.__table__,
    CpCredito.__table__,
    CpSaldoCredito.__table__,
    CpMoraCredito.__table__,
    CpIndicadorCartera.__table__,
]


def ensure_schema() -> None:
    MAIN.metadata.create_all(bind=engine, tables=CARTERA_TABLES, checkfirst=True)


def get_db():
    return SessionLocal()


def create_cliente(db, data: dict) -> CpCliente:
    obj = CpCliente(**data)
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return obj


def get_cliente(db, cliente_id: int) -> Optional[CpCliente]:
    return db.query(CpCliente).filter(CpCliente.id == cliente_id).first()


def count_clientes(db) -> int:
    return db.query(CpCliente).count()


def create_credito(db, data: dict) -> CpCredito:
    obj = CpCredito(**data)
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return obj


def get_credito(db, credito_id: int) -> Optional[CpCredito]:
    return db.query(CpCredito).filter(CpCredito.id == credito_id).first()


def get_credito_by_numero(db, numero_credito: str) -> Optional[CpCredito]:
    return db.query(CpCredito).filter(CpCredito.numero_credito == numero_credito).first()


def list_creditos(
    db,
    *,
    estado: Optional[str] = None,
    bucket_mora: Optional[str] = None,
    oficial: Optional[str] = None,
) -> list[CpCredito]:
    query = db.query(CpCredito)
    if estado:
        query = query.filter(CpCredito.estado == estado)
    if bucket_mora:
        query = query.filter(CpCredito.bucket_mora == bucket_mora)
    if oficial:
        query = query.filter(CpCredito.oficial == oficial)
    return query.order_by(CpCredito.id.desc()).all()


def upsert_saldo_credito(db, credito_id: int, data: dict) -> CpSaldoCredito:
    obj = db.query(CpSaldoCredito).filter(CpSaldoCredito.credito_id == credito_id).first()
    if obj is None:
        obj = CpSaldoCredito(credito_id=credito_id, **data)
        db.add(obj)
    else:
        for key, value in data.items():
            setattr(obj, key, value)
    db.flush()
    db.refresh(obj)
    return obj


def upsert_mora_credito(db, credito_id: int, data: dict) -> CpMoraCredito:
    obj = db.query(CpMoraCredito).filter(CpMoraCredito.credito_id == credito_id).first()
    if obj is None:
        obj = CpMoraCredito(credito_id=credito_id, **data)
        db.add(obj)
    else:
        for key, value in data.items():
            setattr(obj, key, value)
    db.flush()
    db.refresh(obj)
    return obj


def list_moras(db) -> list[CpMoraCredito]:
    return db.query(CpMoraCredito).order_by(CpMoraCredito.dias_mora.desc()).all()


def save_indicador(db, data: dict) -> CpIndicadorCartera:
    obj = CpIndicadorCartera(**data)
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return obj


def list_indicadores(db, fecha_corte: Optional[date] = None) -> list[CpIndicadorCartera]:
    query = db.query(CpIndicadorCartera)
    if fecha_corte:
        query = query.filter(CpIndicadorCartera.fecha_corte == fecha_corte)
    return query.order_by(CpIndicadorCartera.fecha_corte.desc(), CpIndicadorCartera.id.desc()).all()


def sum_saldo_total(db) -> Decimal:
    return db.query(func.sum(CpSaldoCredito.saldo_total)).scalar() or Decimal("0")


def sum_monto_vencido(db) -> Decimal:
    return db.query(func.sum(CpMoraCredito.monto_vencido)).scalar() or Decimal("0")

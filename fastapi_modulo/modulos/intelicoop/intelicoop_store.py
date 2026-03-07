from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from fastapi_modulo.db import Base, SessionLocal, engine
from fastapi_modulo.modulos.intelicoop.intelicoop_db_models import (
    IntelicoopCampania,
    IntelicoopContactoCampania,
    IntelicoopCredito,
    IntelicoopCuenta,
    IntelicoopHistorialPago,
    IntelicoopProspecto,
    IntelicoopScoringResult,
    IntelicoopSeguimientoCampania,
    IntelicoopSocio,
    IntelicoopTransaccion,
)


def ensure_intelicoop_schema() -> None:
    Base.metadata.create_all(
        bind=engine,
        tables=[
            IntelicoopSocio.__table__,
            IntelicoopCredito.__table__,
            IntelicoopHistorialPago.__table__,
            IntelicoopCuenta.__table__,
            IntelicoopTransaccion.__table__,
            IntelicoopCampania.__table__,
            IntelicoopProspecto.__table__,
            IntelicoopContactoCampania.__table__,
            IntelicoopSeguimientoCampania.__table__,
            IntelicoopScoringResult.__table__,
        ],
        checkfirst=True,
    )


def _db() -> Session:
    ensure_intelicoop_schema()
    return SessionLocal()


def _socio_dict(obj: IntelicoopSocio) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "nombre": obj.nombre,
        "email": obj.email,
        "telefono": obj.telefono,
        "direccion": obj.direccion,
        "segmento": obj.segmento,
        "fecha_registro": obj.fecha_registro.isoformat() if obj.fecha_registro else "",
    }


def _credito_dict(obj: IntelicoopCredito, socio_nombre: str = "") -> Dict[str, Any]:
    return {
        "id": obj.id,
        "socio_id": obj.socio_id,
        "socio_nombre": socio_nombre,
        "monto": round(float(obj.monto or 0), 2),
        "plazo": obj.plazo,
        "ingreso_mensual": round(float(obj.ingreso_mensual or 0), 2),
        "deuda_actual": round(float(obj.deuda_actual or 0), 2),
        "antiguedad_meses": obj.antiguedad_meses,
        "estado": obj.estado,
        "fecha_creacion": obj.fecha_creacion.isoformat() if obj.fecha_creacion else "",
    }


def _historial_pago_dict(obj: IntelicoopHistorialPago) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "credito_id": obj.credito_id,
        "monto": round(float(obj.monto or 0), 2),
        "fecha": obj.fecha.isoformat() if obj.fecha else "",
    }


def _campania_dict(obj: IntelicoopCampania) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "nombre": obj.nombre,
        "tipo": obj.tipo,
        "fecha_inicio": obj.fecha_inicio,
        "fecha_fin": obj.fecha_fin,
        "estado": obj.estado,
        "fecha_creacion": obj.fecha_creacion.isoformat() if obj.fecha_creacion else "",
    }


def _prospecto_dict(obj: IntelicoopProspecto) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "nombre": obj.nombre,
        "telefono": obj.telefono,
        "direccion": obj.direccion,
        "fuente": obj.fuente,
        "score_propension": round(float(obj.score_propension or 0), 4),
        "fecha_creacion": obj.fecha_creacion.isoformat() if obj.fecha_creacion else "",
    }


def _contacto_campania_dict(obj: IntelicoopContactoCampania, campania_nombre: str = "", socio_nombre: str = "") -> Dict[str, Any]:
    return {
        "id": obj.id,
        "campania_id": obj.campania_id,
        "campania_nombre": campania_nombre,
        "socio_id": obj.socio_id,
        "socio_nombre": socio_nombre,
        "ejecutivo_id": obj.ejecutivo_id,
        "canal": obj.canal,
        "estado_contacto": obj.estado_contacto,
        "fecha_contacto": obj.fecha_contacto.isoformat() if obj.fecha_contacto else "",
    }


def _seguimiento_campania_dict(obj: IntelicoopSeguimientoCampania, campania_nombre: str = "", socio_nombre: str = "") -> Dict[str, Any]:
    return {
        "id": obj.id,
        "campania_id": obj.campania_id,
        "campania_nombre": campania_nombre,
        "socio_id": obj.socio_id,
        "socio_nombre": socio_nombre,
        "lista": obj.lista,
        "etapa": obj.etapa,
        "conversion": bool(obj.conversion),
        "monto_colocado": round(float(obj.monto_colocado or 0), 2),
        "fecha_evento": obj.fecha_evento.isoformat() if obj.fecha_evento else "",
    }


def _scoring_result_dict(obj: IntelicoopScoringResult) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "solicitud_id": obj.solicitud_id,
        "socio_id": obj.socio_id,
        "credito_id": obj.credito_id,
        "ingreso_mensual": round(float(obj.ingreso_mensual or 0), 2),
        "deuda_actual": round(float(obj.deuda_actual or 0), 2),
        "antiguedad_meses": obj.antiguedad_meses,
        "score": round(float(obj.score or 0), 4),
        "recomendacion": obj.recomendacion,
        "riesgo": obj.riesgo,
        "model_version": obj.model_version,
        "fecha_creacion": obj.fecha_creacion.isoformat() if obj.fecha_creacion else "",
    }


def _cuenta_dict(obj: IntelicoopCuenta, socio_nombre: str = "") -> Dict[str, Any]:
    return {
        "id": obj.id,
        "socio_id": obj.socio_id,
        "socio_nombre": socio_nombre,
        "tipo": obj.tipo,
        "saldo": round(float(obj.saldo or 0), 2),
        "fecha_creacion": obj.fecha_creacion.isoformat() if obj.fecha_creacion else "",
    }


def _transaccion_dict(obj: IntelicoopTransaccion, socio_nombre: str = "") -> Dict[str, Any]:
    return {
        "id": obj.id,
        "cuenta_id": obj.cuenta_id,
        "socio_nombre": socio_nombre,
        "monto": round(float(obj.monto or 0), 2),
        "tipo": obj.tipo,
        "fecha": obj.fecha.isoformat() if obj.fecha else "",
    }


def list_socios() -> List[Dict[str, Any]]:
    db = _db()
    try:
        rows = db.query(IntelicoopSocio).order_by(IntelicoopSocio.id.desc()).all()
        return [_socio_dict(row) for row in rows]
    finally:
        db.close()


def get_socio(socio_id: int) -> Dict[str, Any] | None:
    db = _db()
    try:
        row = db.query(IntelicoopSocio).filter(IntelicoopSocio.id == socio_id).first()
        return _socio_dict(row) if row else None
    finally:
        db.close()


def create_socio(payload: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        email = payload["email"].strip().lower()
        existing = db.query(IntelicoopSocio).filter(func.lower(IntelicoopSocio.email) == email).first()
        if existing:
            raise ValueError("Ya existe un socio con ese correo.")
        row = IntelicoopSocio(
            nombre=payload["nombre"].strip(),
            email=email,
            telefono=payload.get("telefono", "").strip(),
            direccion=payload.get("direccion", "").strip(),
            segmento=payload.get("segmento", "inactivo").strip() or "inactivo",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _socio_dict(row)
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def list_creditos() -> List[Dict[str, Any]]:
    db = _db()
    try:
        rows = (
            db.query(IntelicoopCredito, IntelicoopSocio.nombre)
            .join(IntelicoopSocio, IntelicoopSocio.id == IntelicoopCredito.socio_id)
            .order_by(IntelicoopCredito.id.desc())
            .all()
        )
        return [_credito_dict(credito, socio_nombre or "") for credito, socio_nombre in rows]
    finally:
        db.close()


def get_credito(credito_id: int) -> Dict[str, Any] | None:
    db = _db()
    try:
        row = (
            db.query(IntelicoopCredito, IntelicoopSocio.nombre)
            .join(IntelicoopSocio, IntelicoopSocio.id == IntelicoopCredito.socio_id)
            .filter(IntelicoopCredito.id == credito_id)
            .first()
        )
        if not row:
            return None
        credito, socio_nombre = row
        return _credito_dict(credito, socio_nombre or "")
    finally:
        db.close()


def get_credito_detail(credito_id: int) -> Dict[str, Any] | None:
    db = _db()
    try:
        row = (
            db.query(IntelicoopCredito, IntelicoopSocio.nombre)
            .join(IntelicoopSocio, IntelicoopSocio.id == IntelicoopCredito.socio_id)
            .filter(IntelicoopCredito.id == credito_id)
            .first()
        )
        if not row:
            return None
        credito, socio_nombre = row
        pagos = (
            db.query(IntelicoopHistorialPago)
            .filter(IntelicoopHistorialPago.credito_id == credito_id)
            .order_by(IntelicoopHistorialPago.fecha.desc(), IntelicoopHistorialPago.id.desc())
            .all()
        )
        total_pagado = sum(float(item.monto or 0) for item in pagos)
        return {
            **_credito_dict(credito, socio_nombre or ""),
            "historial_pagos": [_historial_pago_dict(item) for item in pagos],
            "resumen_pagos": {
                "total_pagos": len(pagos),
                "monto_pagado": round(total_pagado, 2),
                "saldo_estimado": round(max(0.0, float(credito.monto or 0) - total_pagado), 2),
            },
        }
    finally:
        db.close()


def create_credito(payload: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        socio = db.query(IntelicoopSocio).filter(IntelicoopSocio.id == int(payload["socio_id"])).first()
        if not socio:
            raise ValueError("El socio indicado no existe en intelicoop.")
        row = IntelicoopCredito(
            socio_id=int(payload["socio_id"]),
            monto=float(payload["monto"]),
            plazo=int(payload["plazo"]),
            ingreso_mensual=float(payload.get("ingreso_mensual", 0)),
            deuda_actual=float(payload.get("deuda_actual", 0)),
            antiguedad_meses=int(payload.get("antiguedad_meses", 0)),
            estado=payload.get("estado", "solicitado"),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _credito_dict(row, socio.nombre)
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def list_historial_pagos(credito_id: int | None = None) -> List[Dict[str, Any]]:
    db = _db()
    try:
        query = db.query(IntelicoopHistorialPago)
        if credito_id is not None:
            query = query.filter(IntelicoopHistorialPago.credito_id == credito_id)
        rows = query.order_by(IntelicoopHistorialPago.fecha.desc(), IntelicoopHistorialPago.id.desc()).all()
        return [_historial_pago_dict(row) for row in rows]
    finally:
        db.close()


def create_historial_pago(payload: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        credito = db.query(IntelicoopCredito).filter(IntelicoopCredito.id == int(payload["credito_id"])).first()
        if not credito:
            raise ValueError("El credito indicado no existe en intelicoop.")
        row = IntelicoopHistorialPago(
            credito_id=int(payload["credito_id"]),
            monto=float(payload["monto"]),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _historial_pago_dict(row)
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def get_ahorros_resumen() -> Dict[str, Any]:
    db = _db()
    try:
        cuentas = db.query(func.count(IntelicoopCuenta.id)).scalar() or 0
        movimientos = db.query(func.count(IntelicoopTransaccion.id)).scalar() or 0
        captacion = db.query(func.coalesce(func.sum(IntelicoopCuenta.saldo), 0)).scalar() or 0
        return {
            "cuentas": int(cuentas),
            "movimientos": int(movimientos),
            "captacion": round(float(captacion), 2),
        }
    finally:
        db.close()


def list_cuentas() -> List[Dict[str, Any]]:
    db = _db()
    try:
        rows = (
            db.query(IntelicoopCuenta, IntelicoopSocio.nombre)
            .join(IntelicoopSocio, IntelicoopSocio.id == IntelicoopCuenta.socio_id)
            .order_by(IntelicoopCuenta.id.desc())
            .all()
        )
        return [_cuenta_dict(cuenta, socio_nombre or "") for cuenta, socio_nombre in rows]
    finally:
        db.close()


def create_cuenta(payload: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        socio = db.query(IntelicoopSocio).filter(IntelicoopSocio.id == int(payload["socio_id"])).first()
        if not socio:
            raise ValueError("El socio indicado no existe en intelicoop.")
        row = IntelicoopCuenta(
            socio_id=int(payload["socio_id"]),
            tipo=str(payload.get("tipo", "ahorro")).strip() or "ahorro",
            saldo=float(payload.get("saldo", 0)),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _cuenta_dict(row, socio.nombre)
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def list_transacciones() -> List[Dict[str, Any]]:
    db = _db()
    try:
        rows = (
            db.query(IntelicoopTransaccion, IntelicoopSocio.nombre)
            .join(IntelicoopCuenta, IntelicoopCuenta.id == IntelicoopTransaccion.cuenta_id)
            .join(IntelicoopSocio, IntelicoopSocio.id == IntelicoopCuenta.socio_id)
            .order_by(IntelicoopTransaccion.id.desc())
            .all()
        )
        return [_transaccion_dict(tx, socio_nombre or "") for tx, socio_nombre in rows]
    finally:
        db.close()


def create_transaccion(payload: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        cuenta = db.query(IntelicoopCuenta).filter(IntelicoopCuenta.id == int(payload["cuenta_id"])).first()
        if not cuenta:
            raise ValueError("La cuenta indicada no existe en intelicoop.")
        tipo = str(payload.get("tipo", "deposito")).strip() or "deposito"
        monto = float(payload.get("monto", 0))
        if monto <= 0:
            raise ValueError("El monto debe ser mayor a cero.")
        saldo_actual = float(cuenta.saldo or 0)
        if tipo == "retiro" and monto > saldo_actual:
            raise ValueError("Saldo insuficiente para registrar el retiro.")
        cuenta.saldo = saldo_actual + monto if tipo == "deposito" else saldo_actual - monto
        tx = IntelicoopTransaccion(
            cuenta_id=cuenta.id,
            monto=monto,
            tipo=tipo,
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        socio = db.query(IntelicoopSocio).filter(IntelicoopSocio.id == cuenta.socio_id).first()
        return _transaccion_dict(tx, socio.nombre if socio else "")
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def list_campanas() -> List[Dict[str, Any]]:
    db = _db()
    try:
        rows = db.query(IntelicoopCampania).order_by(IntelicoopCampania.id.desc()).all()
        return [_campania_dict(row) for row in rows]
    finally:
        db.close()


def create_campana(payload: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        row = IntelicoopCampania(
            nombre=payload["nombre"].strip(),
            tipo=payload["tipo"].strip(),
            fecha_inicio=payload.get("fecha_inicio", "").strip(),
            fecha_fin=payload.get("fecha_fin", "").strip(),
            estado=payload.get("estado", "borrador").strip() or "borrador",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _campania_dict(row)
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def list_prospectos() -> List[Dict[str, Any]]:
    db = _db()
    try:
        rows = db.query(IntelicoopProspecto).order_by(IntelicoopProspecto.id.desc()).all()
        return [_prospecto_dict(row) for row in rows]
    finally:
        db.close()


def create_prospecto(payload: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        row = IntelicoopProspecto(
            nombre=payload["nombre"].strip(),
            telefono=payload.get("telefono", "").strip(),
            direccion=payload.get("direccion", "").strip(),
            fuente=payload.get("fuente", "").strip(),
            score_propension=float(payload.get("score_propension", 0)),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _prospecto_dict(row)
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def list_contactos_campania(campania_id: int | None = None) -> List[Dict[str, Any]]:
    db = _db()
    try:
        query = (
            db.query(IntelicoopContactoCampania, IntelicoopCampania.nombre, IntelicoopSocio.nombre)
            .join(IntelicoopCampania, IntelicoopCampania.id == IntelicoopContactoCampania.campania_id)
            .join(IntelicoopSocio, IntelicoopSocio.id == IntelicoopContactoCampania.socio_id)
        )
        if campania_id is not None:
            query = query.filter(IntelicoopContactoCampania.campania_id == campania_id)
        rows = query.order_by(IntelicoopContactoCampania.id.desc()).all()
        return [
            _contacto_campania_dict(contacto, campania_nombre or "", socio_nombre or "")
            for contacto, campania_nombre, socio_nombre in rows
        ]
    finally:
        db.close()


def create_contacto_campania(payload: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        campania = db.query(IntelicoopCampania).filter(IntelicoopCampania.id == int(payload["campania_id"])).first()
        socio = db.query(IntelicoopSocio).filter(IntelicoopSocio.id == int(payload["socio_id"])).first()
        if not campania:
            raise ValueError("La campana indicada no existe en intelicoop.")
        if not socio:
            raise ValueError("El socio indicado no existe en intelicoop.")
        row = IntelicoopContactoCampania(
            campania_id=int(payload["campania_id"]),
            socio_id=int(payload["socio_id"]),
            ejecutivo_id=str(payload.get("ejecutivo_id", "ejecutivo_general")).strip() or "ejecutivo_general",
            canal=str(payload.get("canal", "telefono")).strip() or "telefono",
            estado_contacto=str(payload.get("estado_contacto", "pendiente")).strip() or "pendiente",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _contacto_campania_dict(row, campania.nombre, socio.nombre)
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def list_seguimientos_campania(campania_id: int | None = None) -> List[Dict[str, Any]]:
    db = _db()
    try:
        query = (
            db.query(IntelicoopSeguimientoCampania, IntelicoopCampania.nombre, IntelicoopSocio.nombre)
            .join(IntelicoopCampania, IntelicoopCampania.id == IntelicoopSeguimientoCampania.campania_id)
            .join(IntelicoopSocio, IntelicoopSocio.id == IntelicoopSeguimientoCampania.socio_id)
        )
        if campania_id is not None:
            query = query.filter(IntelicoopSeguimientoCampania.campania_id == campania_id)
        rows = query.order_by(IntelicoopSeguimientoCampania.id.desc()).all()
        return [
            _seguimiento_campania_dict(item, campania_nombre or "", socio_nombre or "")
            for item, campania_nombre, socio_nombre in rows
        ]
    finally:
        db.close()


def create_seguimiento_campania(payload: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        campania = db.query(IntelicoopCampania).filter(IntelicoopCampania.id == int(payload["campania_id"])).first()
        socio = db.query(IntelicoopSocio).filter(IntelicoopSocio.id == int(payload["socio_id"])).first()
        if not campania:
            raise ValueError("La campana indicada no existe en intelicoop.")
        if not socio:
            raise ValueError("El socio indicado no existe en intelicoop.")
        row = IntelicoopSeguimientoCampania(
            campania_id=int(payload["campania_id"]),
            socio_id=int(payload["socio_id"]),
            lista=str(payload.get("lista", "general")).strip() or "general",
            etapa=str(payload.get("etapa", "contactado")).strip() or "contactado",
            conversion=1 if payload.get("conversion") else 0,
            monto_colocado=float(payload.get("monto_colocado", 0)),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _seguimiento_campania_dict(row, campania.nombre, socio.nombre)
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def list_scoring_results() -> List[Dict[str, Any]]:
    db = _db()
    try:
        rows = db.query(IntelicoopScoringResult).order_by(IntelicoopScoringResult.id.desc()).all()
        return [_scoring_result_dict(row) for row in rows]
    finally:
        db.close()


def create_scoring_result(payload: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        row = IntelicoopScoringResult(
            solicitud_id=str(payload["solicitud_id"]).strip(),
            socio_id=payload.get("socio_id"),
            credito_id=payload.get("credito_id"),
            ingreso_mensual=float(payload.get("ingreso_mensual", 0)),
            deuda_actual=float(payload.get("deuda_actual", 0)),
            antiguedad_meses=int(payload.get("antiguedad_meses", 0)),
            score=float(payload.get("score", 0)),
            recomendacion=str(payload.get("recomendacion", "evaluar")),
            riesgo=str(payload.get("riesgo", "medio")),
            model_version=str(payload.get("model_version", "intelicoop_scoring_v1")),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _scoring_result_dict(row)
    except SQLAlchemyError as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def get_basic_catalogs() -> Dict[str, Any]:
    db = _db()
    try:
        socios = db.query(IntelicoopSocio).order_by(IntelicoopSocio.nombre.asc()).all()
        return {
            "socios": [
                {
                    "id": row.id,
                    "nombre": row.nombre,
                    "segmento": row.segmento,
                }
                for row in socios
            ],
            "segmentos": [
                {"value": "hormiga", "label": "Ahorrador Hormiga"},
                {"value": "gran_ahorrador", "label": "Gran Ahorrador"},
                {"value": "inactivo", "label": "Inactivo"},
            ],
            "estados_credito": [
                {"value": "solicitado", "label": "Solicitado"},
                {"value": "aprobado", "label": "Aprobado"},
                {"value": "rechazado", "label": "Rechazado"},
            ],
            "estados_campana": [
                {"value": "borrador", "label": "Borrador"},
                {"value": "activa", "label": "Activa"},
                {"value": "finalizada", "label": "Finalizada"},
            ],
            "tipos_cuenta": [
                {"value": "ahorro", "label": "Ahorro"},
                {"value": "aportacion", "label": "Aportacion"},
            ],
            "tipos_transaccion": [
                {"value": "deposito", "label": "Deposito"},
                {"value": "retiro", "label": "Retiro"},
            ],
            "cuentas": [
                {
                    "id": row.id,
                    "socio_id": row.socio_id,
                    "tipo": row.tipo,
                    "saldo": round(float(row.saldo or 0), 2),
                }
                for row in db.query(IntelicoopCuenta).order_by(IntelicoopCuenta.id.asc()).all()
            ],
        }
    finally:
        db.close()


def get_dashboard_resumen() -> Dict[str, Any]:
    db = _db()
    try:
        socios = db.query(func.count(IntelicoopSocio.id)).scalar() or 0
        creditos = db.query(func.count(IntelicoopCredito.id)).scalar() or 0
        campanas = db.query(func.count(IntelicoopCampania.id)).scalar() or 0
        prospectos = db.query(func.count(IntelicoopProspecto.id)).scalar() or 0
        scoring_total = db.query(func.count(IntelicoopScoringResult.id)).scalar() or 0
        riesgo_rows = (
            db.query(IntelicoopScoringResult.riesgo, func.count(IntelicoopScoringResult.id))
            .group_by(IntelicoopScoringResult.riesgo)
            .all()
        )
        riesgo = {"bajo": 0, "medio": 0, "alto": 0}
        for key, count in riesgo_rows:
            if key in riesgo:
                riesgo[key] = int(count)
        cartera_total = float(db.query(func.coalesce(func.sum(IntelicoopCredito.monto), 0)).scalar() or 0)
        pagos_total = float(db.query(func.coalesce(func.sum(IntelicoopHistorialPago.monto), 0)).scalar() or 0)
        cartera_vigente = max(0.0, cartera_total - pagos_total)
        cartera_vencida_estimada = 0.0
        if scoring_total:
            cartera_vencida_estimada = cartera_total * (riesgo["alto"] / max(1, int(scoring_total))) * 0.35
        imor_pct = (cartera_vencida_estimada / cartera_total * 100.0) if cartera_total else 0.0
        depositos_total = float(
            db.query(func.coalesce(func.sum(IntelicoopTransaccion.monto), 0))
            .filter(IntelicoopTransaccion.tipo == "deposito")
            .scalar()
            or 0
        )
        retiros_total = float(
            db.query(func.coalesce(func.sum(IntelicoopTransaccion.monto), 0))
            .filter(IntelicoopTransaccion.tipo == "retiro")
            .scalar()
            or 0
        )
        captacion_neta = depositos_total - retiros_total
        campanas_activas = int(
            db.query(func.count(IntelicoopCampania.id))
            .filter(IntelicoopCampania.estado == "activa")
            .scalar()
            or 0
        )
        prospectos_score_prom = float(
            db.query(func.coalesce(func.avg(IntelicoopProspecto.score_propension), 0)).scalar() or 0
        )
        contactos_total = int(db.query(func.count(IntelicoopContactoCampania.id)).scalar() or 0)
        conversiones_total = int(
            db.query(func.count(IntelicoopSeguimientoCampania.id))
            .filter(IntelicoopSeguimientoCampania.conversion == 1)
            .scalar()
            or 0
        )
        conversion_pct = (conversiones_total / contactos_total * 100.0) if contactos_total else 0.0
        aprobados = int(
            db.query(func.count(IntelicoopCredito.id))
            .filter(IntelicoopCredito.estado == "aprobado")
            .scalar()
            or 0
        )
        rechazados = int(
            db.query(func.count(IntelicoopCredito.id))
            .filter(IntelicoopCredito.estado == "rechazado")
            .scalar()
            or 0
        )
        solicitados = int(
            db.query(func.count(IntelicoopCredito.id))
            .filter(IntelicoopCredito.estado == "solicitado")
            .scalar()
            or 0
        )
        semaforos = [
            {
                "ambito": "salud_cartera",
                "label": "Salud de cartera",
                "valor": round(imor_pct, 2),
                "meta": 8.0,
                "semaforo": "verde" if imor_pct <= 8 else ("amarillo" if imor_pct <= 14 else "rojo"),
            },
            {
                "ambito": "captacion",
                "label": "Captacion neta",
                "valor": round(captacion_neta, 2),
                "meta": 0.0,
                "semaforo": "verde" if captacion_neta >= 0 else ("amarillo" if captacion_neta >= -1000 else "rojo"),
            },
            {
                "ambito": "riesgo",
                "label": "Scoring alto riesgo",
                "valor": riesgo["alto"],
                "meta": max(1, int(scoring_total * 0.2)) if scoring_total else 0,
                "semaforo": "verde" if riesgo["alto"] <= max(1, int(scoring_total * 0.2)) else ("amarillo" if riesgo["alto"] <= max(1, int(scoring_total * 0.35)) else "rojo"),
            },
            {
                "ambito": "comercial",
                "label": "Campanas activas",
                "valor": campanas_activas,
                "meta": 1,
                "semaforo": "verde" if campanas_activas >= 1 else "amarillo",
            },
        ]
        return {
            "socios": int(socios),
            "creditos": int(creditos),
            "campanas": int(campanas),
            "prospectos": int(prospectos),
            "scoring_total": int(scoring_total),
            "riesgo": riesgo,
            "salud_cartera": {
                "cartera_total": round(cartera_total, 2),
                "cartera_vigente": round(cartera_vigente, 2),
                "cartera_vencida_estimada": round(cartera_vencida_estimada, 2),
                "imor_pct": round(imor_pct, 2),
            },
            "colocacion": {
                "solicitados": solicitados,
                "aprobados": aprobados,
                "rechazados": rechazados,
                "monto_total": round(cartera_total, 2),
                "ticket_promedio": round((cartera_total / creditos), 2) if creditos else 0.0,
            },
            "captacion": {
                "depositos_total": round(depositos_total, 2),
                "retiros_total": round(retiros_total, 2),
                "captacion_neta": round(captacion_neta, 2),
            },
            "comercial": {
                "campanas_activas": campanas_activas,
                "prospectos_total": int(prospectos),
                "score_propension_promedio": round(prospectos_score_prom, 4),
                "contactos_total": contactos_total,
                "conversiones_total": conversiones_total,
                "conversion_pct": round(conversion_pct, 2),
            },
            "semaforos": semaforos,
        }
    finally:
        db.close()

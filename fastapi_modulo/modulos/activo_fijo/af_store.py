from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError

from fastapi_modulo.db import Base, SessionLocal, engine
from fastapi_modulo.modulos.activo_fijo.af_db_models import (
    AfActivo,
    AfAsignacion,
    AfBaja,
    AfDepreciacion,
    AfMantenimiento,
)

_AF_TABLES = [
    AfActivo.__table__,
    AfDepreciacion.__table__,
    AfAsignacion.__table__,
    AfMantenimiento.__table__,
    AfBaja.__table__,
]


def ensure_af_schema() -> None:
    Base.metadata.create_all(bind=engine, tables=_AF_TABLES, checkfirst=True)


def _db():
    ensure_af_schema()
    return SessionLocal()


def _dec(v) -> Optional[str]:
    if v is None:
        return None
    return str(Decimal(str(v)).quantize(Decimal("0.01")))


def _date_str(v) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return str(v)


# ── Serializers ───────────────────────────────────────────────────────────────

def _activo_dict(obj: AfActivo) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "codigo": obj.codigo,
        "nombre": obj.nombre,
        "categoria": obj.categoria,
        "marca": obj.marca,
        "modelo": obj.modelo,
        "numero_serie": obj.numero_serie,
        "proveedor": obj.proveedor,
        "fecha_adquisicion": _date_str(obj.fecha_adquisicion),
        "valor_adquisicion": _dec(obj.valor_adquisicion),
        "valor_residual": _dec(obj.valor_residual),
        "vida_util_meses": obj.vida_util_meses,
        "metodo_depreciacion": obj.metodo_depreciacion,
        "valor_libro": _dec(obj.valor_libro if obj.valor_libro is not None else obj.valor_adquisicion),
        "ubicacion": obj.ubicacion,
        "responsable": obj.responsable,
        "estado": obj.estado,
        "descripcion": obj.descripcion,
        "creado_en": _date_str(obj.creado_en),
        "actualizado_en": _date_str(obj.actualizado_en),
    }


def _depreciacion_dict(obj: AfDepreciacion) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "activo_id": obj.activo_id,
        "activo_nombre": obj.activo.nombre if obj.activo else None,
        "activo_codigo": obj.activo.codigo if obj.activo else None,
        "periodo": obj.periodo,
        "metodo": obj.metodo,
        "valor_depreciacion": _dec(obj.valor_depreciacion),
        "valor_libro_anterior": _dec(obj.valor_libro_anterior),
        "valor_libro_nuevo": _dec(obj.valor_libro_nuevo),
        "creado_en": _date_str(obj.creado_en),
    }


def _asignacion_dict(obj: AfAsignacion) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "activo_id": obj.activo_id,
        "activo_nombre": obj.activo.nombre if obj.activo else None,
        "activo_codigo": obj.activo.codigo if obj.activo else None,
        "empleado": obj.empleado,
        "area": obj.area,
        "fecha_asignacion": _date_str(obj.fecha_asignacion),
        "fecha_devolucion": _date_str(obj.fecha_devolucion),
        "estado": obj.estado,
        "observaciones": obj.observaciones,
        "creado_en": _date_str(obj.creado_en),
        "actualizado_en": _date_str(obj.actualizado_en),
    }


def _mantenimiento_dict(obj: AfMantenimiento) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "activo_id": obj.activo_id,
        "activo_nombre": obj.activo.nombre if obj.activo else None,
        "activo_codigo": obj.activo.codigo if obj.activo else None,
        "tipo": obj.tipo,
        "descripcion": obj.descripcion,
        "proveedor": obj.proveedor,
        "fecha_inicio": _date_str(obj.fecha_inicio),
        "fecha_fin": _date_str(obj.fecha_fin),
        "costo": _dec(obj.costo),
        "estado": obj.estado,
        "observaciones": obj.observaciones,
        "creado_en": _date_str(obj.creado_en),
        "actualizado_en": _date_str(obj.actualizado_en),
    }


def _baja_dict(obj: AfBaja) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "activo_id": obj.activo_id,
        "activo_nombre": obj.activo.nombre if obj.activo else None,
        "activo_codigo": obj.activo.codigo if obj.activo else None,
        "motivo": obj.motivo,
        "fecha_baja": _date_str(obj.fecha_baja),
        "valor_residual_real": _dec(obj.valor_residual_real),
        "observaciones": obj.observaciones,
        "creado_en": _date_str(obj.creado_en),
    }


# ── Activos CRUD ──────────────────────────────────────────────────────────────

def list_activos(estado: Optional[str] = None,
                 categoria: Optional[str] = None) -> List[Dict]:
    db = _db()
    try:
        q = db.query(AfActivo)
        if estado:
            q = q.filter(AfActivo.estado == estado)
        if categoria:
            q = q.filter(AfActivo.categoria == categoria)
        return [_activo_dict(o) for o in q.order_by(AfActivo.id.desc()).all()]
    finally:
        db.close()


def get_activo(activo_id: int) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(AfActivo).filter(AfActivo.id == activo_id).first()
        return _activo_dict(obj) if obj else None
    finally:
        db.close()


def create_activo(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        # Initialize valor_libro = valor_adquisicion
        if "valor_libro" not in data or data["valor_libro"] is None:
            data["valor_libro"] = data.get("valor_adquisicion", 0)
        obj = AfActivo(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return _activo_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_activo(activo_id: int, data: Dict[str, Any]) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(AfActivo).filter(AfActivo.id == activo_id).first()
        if not obj:
            return None
        for k, v in data.items():
            setattr(obj, k, v)
        db.commit()
        db.refresh(obj)
        return _activo_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_activo(activo_id: int) -> bool:
    db = _db()
    try:
        obj = db.query(AfActivo).filter(AfActivo.id == activo_id).first()
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


# ── Depreciación ──────────────────────────────────────────────────────────────

def _calc_linea_recta(valor_libro: Decimal, valor_residual: Decimal,
                      vida_util_meses: int) -> Decimal:
    """Cuota mensual fija."""
    depreciable = valor_libro - valor_residual
    if depreciable <= 0 or vida_util_meses <= 0:
        return Decimal("0")
    cuota = (Decimal(str(valor_libro)) - Decimal(str(valor_residual))) / vida_util_meses
    # cuota cannot make valor_libro go below valor_residual
    cuota = min(cuota, depreciable)
    return cuota.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _calc_saldo_decreciente(valor_libro: Decimal, valor_residual: Decimal,
                             tasa: Decimal) -> Decimal:
    """Depreciación mensual = valor_libro × tasa/12."""
    monto = Decimal(str(valor_libro)) * tasa / 12
    max_dep = Decimal(str(valor_libro)) - Decimal(str(valor_residual))
    if max_dep <= 0:
        return Decimal("0")
    monto = min(monto, max_dep)
    return monto.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def depreciar_activo(activo_id: int, periodo: Optional[str] = None,
                     tasa_sd: Optional[Decimal] = None) -> Dict[str, Any]:
    """Calcula y registra la depreciación del activo para el periodo dado."""
    if periodo is None:
        hoy = date.today()
        periodo = f"{hoy.year:04d}-{hoy.month:02d}"

    db = _db()
    try:
        obj = db.query(AfActivo).filter(AfActivo.id == activo_id).first()
        if not obj:
            raise ValueError("Activo no encontrado")
        if obj.estado == "dado_de_baja":
            raise ValueError("El activo está dado de baja y no puede depreciarse")

        # Check duplicate period
        dup = db.query(AfDepreciacion).filter(
            AfDepreciacion.activo_id == activo_id,
            AfDepreciacion.periodo == periodo,
        ).first()
        if dup:
            raise ValueError(f"El activo ya tiene depreciación registrada para {periodo}")

        valor_libro_ant = Decimal(str(obj.valor_libro or obj.valor_adquisicion))
        valor_residual  = Decimal(str(obj.valor_residual or 0))

        if obj.metodo_depreciacion == "saldo_decreciente":
            tasa = tasa_sd if tasa_sd else Decimal("0.20")  # default 20% anual
            dep_monto = _calc_saldo_decreciente(valor_libro_ant, valor_residual, tasa)
        else:
            dep_monto = _calc_linea_recta(valor_libro_ant, valor_residual, obj.vida_util_meses)

        valor_libro_nuevo = (valor_libro_ant - dep_monto).quantize(Decimal("0.01"))

        # Save record
        dep = AfDepreciacion(
            activo_id=activo_id,
            periodo=periodo,
            metodo=obj.metodo_depreciacion,
            valor_depreciacion=dep_monto,
            valor_libro_anterior=valor_libro_ant,
            valor_libro_nuevo=valor_libro_nuevo,
        )
        db.add(dep)
        obj.valor_libro = valor_libro_nuevo
        db.commit()
        db.refresh(dep)
        dep = db.query(AfDepreciacion).filter(AfDepreciacion.id == dep.id).first()
        return _depreciacion_dict(dep)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def list_depreciaciones(activo_id: Optional[int] = None,
                        periodo: Optional[str] = None) -> List[Dict]:
    db = _db()
    try:
        q = db.query(AfDepreciacion)
        if activo_id:
            q = q.filter(AfDepreciacion.activo_id == activo_id)
        if periodo:
            q = q.filter(AfDepreciacion.periodo == periodo)
        return [_depreciacion_dict(o) for o in q.order_by(AfDepreciacion.id.desc()).all()]
    finally:
        db.close()


def delete_depreciacion(dep_id: int) -> bool:
    """Revertir una depreciación: restaura el valor_libro anterior."""
    db = _db()
    try:
        dep = db.query(AfDepreciacion).filter(AfDepreciacion.id == dep_id).first()
        if not dep:
            return False
        # Restore valor_libro on activo
        activo = db.query(AfActivo).filter(AfActivo.id == dep.activo_id).first()
        if activo:
            activo.valor_libro = dep.valor_libro_anterior
        db.delete(dep)
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


# ── Asignaciones CRUD ─────────────────────────────────────────────────────────

def list_asignaciones(activo_id: Optional[int] = None,
                      estado: Optional[str] = None) -> List[Dict]:
    db = _db()
    try:
        q = db.query(AfAsignacion)
        if activo_id:
            q = q.filter(AfAsignacion.activo_id == activo_id)
        if estado:
            q = q.filter(AfAsignacion.estado == estado)
        return [_asignacion_dict(o) for o in q.order_by(AfAsignacion.id.desc()).all()]
    finally:
        db.close()


def create_asignacion(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        if data.get("fecha_asignacion") is None:
            data["fecha_asignacion"] = date.today()
        obj = AfAsignacion(**data)
        db.add(obj)
        # Update activo state to "asignado"
        activo = db.query(AfActivo).filter(AfActivo.id == data["activo_id"]).first()
        if activo and activo.estado == "activo":
            activo.estado = "asignado"
        db.commit()
        obj = db.query(AfAsignacion).filter(AfAsignacion.id == obj.id).first()
        return _asignacion_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_asignacion(asig_id: int, data: Dict[str, Any]) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(AfAsignacion).filter(AfAsignacion.id == asig_id).first()
        if not obj:
            return None
        for k, v in data.items():
            setattr(obj, k, v)
        # If devuelto, free the activo
        if data.get("estado") == "devuelto":
            activo = db.query(AfActivo).filter(AfActivo.id == obj.activo_id).first()
            if activo and activo.estado == "asignado":
                activo.estado = "activo"
        db.commit()
        obj = db.query(AfAsignacion).filter(AfAsignacion.id == asig_id).first()
        return _asignacion_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_asignacion(asig_id: int) -> bool:
    db = _db()
    try:
        obj = db.query(AfAsignacion).filter(AfAsignacion.id == asig_id).first()
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


# ── Mantenimientos CRUD ───────────────────────────────────────────────────────

def list_mantenimientos(activo_id: Optional[int] = None,
                        estado: Optional[str] = None) -> List[Dict]:
    db = _db()
    try:
        q = db.query(AfMantenimiento)
        if activo_id:
            q = q.filter(AfMantenimiento.activo_id == activo_id)
        if estado:
            q = q.filter(AfMantenimiento.estado == estado)
        return [_mantenimiento_dict(o) for o in q.order_by(AfMantenimiento.id.desc()).all()]
    finally:
        db.close()


def create_mantenimiento(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        obj = AfMantenimiento(**data)
        db.add(obj)
        # If started, mark activo as en_mantenimiento
        activo = db.query(AfActivo).filter(AfActivo.id == data["activo_id"]).first()
        if activo and data.get("estado") in ("en_proceso",) and activo.estado == "activo":
            activo.estado = "en_mantenimiento"
        db.commit()
        obj = db.query(AfMantenimiento).filter(AfMantenimiento.id == obj.id).first()
        return _mantenimiento_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_mantenimiento(mant_id: int, data: Dict[str, Any]) -> Optional[Dict]:
    db = _db()
    try:
        obj = db.query(AfMantenimiento).filter(AfMantenimiento.id == mant_id).first()
        if not obj:
            return None
        for k, v in data.items():
            setattr(obj, k, v)
        # If completed, restore activo status
        if data.get("estado") == "completado":
            activo = db.query(AfActivo).filter(AfActivo.id == obj.activo_id).first()
            if activo and activo.estado == "en_mantenimiento":
                activo.estado = "activo"
        db.commit()
        obj = db.query(AfMantenimiento).filter(AfMantenimiento.id == mant_id).first()
        return _mantenimiento_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_mantenimiento(mant_id: int) -> bool:
    db = _db()
    try:
        obj = db.query(AfMantenimiento).filter(AfMantenimiento.id == mant_id).first()
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


# ── Bajas CRUD ────────────────────────────────────────────────────────────────

def list_bajas() -> List[Dict]:
    db = _db()
    try:
        return [_baja_dict(o) for o in
                db.query(AfBaja).order_by(AfBaja.id.desc()).all()]
    finally:
        db.close()


def create_baja(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        if data.get("fecha_baja") is None:
            data["fecha_baja"] = date.today()
        obj = AfBaja(**data)
        db.add(obj)
        # Mark activo as dado_de_baja
        activo = db.query(AfActivo).filter(AfActivo.id == data["activo_id"]).first()
        if activo:
            activo.estado = "dado_de_baja"
        db.commit()
        obj = db.query(AfBaja).filter(AfBaja.id == obj.id).first()
        return _baja_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_baja(baja_id: int) -> bool:
    db = _db()
    try:
        obj = db.query(AfBaja).filter(AfBaja.id == baja_id).first()
        if not obj:
            return False
        # Restore activo status
        activo = db.query(AfActivo).filter(AfActivo.id == obj.activo_id).first()
        if activo and activo.estado == "dado_de_baja":
            activo.estado = "activo"
        db.delete(obj)
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


# ── Resumen / KPIs ────────────────────────────────────────────────────────────

def get_af_resumen() -> Dict[str, Any]:
    db = _db()
    try:
        from sqlalchemy import func
        total         = db.query(AfActivo).count()
        activos       = db.query(AfActivo).filter(AfActivo.estado == "activo").count()
        asignados     = db.query(AfActivo).filter(AfActivo.estado == "asignado").count()
        en_mant       = db.query(AfActivo).filter(AfActivo.estado == "en_mantenimiento").count()
        dados_baja    = db.query(AfActivo).filter(AfActivo.estado == "dado_de_baja").count()

        valor_libro_total = db.query(
            func.sum(AfActivo.valor_libro)
        ).filter(AfActivo.estado != "dado_de_baja").scalar() or 0

        valor_adq_total = db.query(
            func.sum(AfActivo.valor_adquisicion)
        ).filter(AfActivo.estado != "dado_de_baja").scalar() or 0

        dep_acumulada = float(valor_adq_total) - float(valor_libro_total)

        return {
            "total_activos": total,
            "activos_activos": activos,
            "activos_asignados": asignados,
            "activos_en_mantenimiento": en_mant,
            "activos_dados_baja": dados_baja,
            "valor_libro_total": str(Decimal(str(valor_libro_total)).quantize(Decimal("0.01"))),
            "valor_adquisicion_total": str(Decimal(str(valor_adq_total)).quantize(Decimal("0.01"))),
            "depreciacion_acumulada": str(Decimal(str(max(dep_acumulada, 0))).quantize(Decimal("0.01"))),
        }
    finally:
        db.close()

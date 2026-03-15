from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional

from sqlalchemy.exc import SQLAlchemyError

from fastapi_modulo.modulos.activo_fijo.enums import EstadoActivo, EstadoAsignacion, EstadoMantenimiento, MetodoDepreciacion
import fastapi_modulo.modulos.activo_fijo.repository as repository
from fastapi_modulo.modulos.activo_fijo.serializers import (
    activo_to_dict,
    asignacion_to_dict,
    baja_to_dict,
    dec_str,
    depreciacion_to_dict,
    mantenimiento_to_dict,
)


def list_activos(estado: Optional[str] = None, categoria: Optional[str] = None):
    db = repository.get_db()
    try:
        return [
            activo_to_dict(obj)
            for obj in repository.list_activos(db, estado=estado, categoria=categoria)
        ]
    finally:
        db.close()


def get_activo(activo_id: int):
    db = repository.get_db()
    try:
        obj = repository.get_activo(db, activo_id)
        return activo_to_dict(obj) if obj else None
    finally:
        db.close()


def create_activo(data: Dict[str, Any]):
    db = repository.get_db()
    try:
        payload = dict(data)
        if "valor_libro" not in payload or payload["valor_libro"] is None:
            payload["valor_libro"] = payload.get("valor_adquisicion", 0)
        obj = repository.create_activo(db, payload)
        db.commit()
        db.refresh(obj)
        return activo_to_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_activo(activo_id: int, data: Dict[str, Any]):
    db = repository.get_db()
    try:
        obj = repository.get_activo(db, activo_id)
        if not obj:
            return None
        repository.update_activo(db, obj, data)
        db.commit()
        db.refresh(obj)
        return activo_to_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_activo(activo_id: int) -> bool:
    db = repository.get_db()
    try:
        obj = repository.get_activo(db, activo_id)
        if not obj:
            return False
        repository.delete_record(db, obj)
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def _calc_linea_recta(valor_libro: Decimal, valor_residual: Decimal, vida_util_meses: int) -> Decimal:
    depreciable = valor_libro - valor_residual
    if depreciable <= 0 or vida_util_meses <= 0:
        return Decimal("0")
    cuota = (Decimal(str(valor_libro)) - Decimal(str(valor_residual))) / vida_util_meses
    cuota = min(cuota, depreciable)
    return cuota.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _calc_saldo_decreciente(valor_libro: Decimal, valor_residual: Decimal, tasa: Decimal) -> Decimal:
    monto = Decimal(str(valor_libro)) * tasa / 12
    max_dep = Decimal(str(valor_libro)) - Decimal(str(valor_residual))
    if max_dep <= 0:
        return Decimal("0")
    monto = min(monto, max_dep)
    return monto.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def depreciar_activo(activo_id: int, periodo: Optional[str] = None, tasa_sd: Optional[Decimal] = None):
    if periodo is None:
        hoy = date.today()
        periodo = f"{hoy.year:04d}-{hoy.month:02d}"

    db = repository.get_db()
    try:
        obj = repository.get_activo(db, activo_id)
        if not obj:
            raise ValueError("Activo no encontrado")
        if obj.estado == EstadoActivo.DADO_DE_BAJA.value:
            raise ValueError("El activo está dado de baja y no puede depreciarse")
        if repository.get_depreciacion_by_periodo(db, activo_id, periodo):
            raise ValueError(f"El activo ya tiene depreciación registrada para {periodo}")

        valor_libro_anterior = Decimal(str(obj.valor_libro or obj.valor_adquisicion))
        valor_residual = Decimal(str(obj.valor_residual or 0))

        if obj.metodo_depreciacion == MetodoDepreciacion.SALDO_DECRECIENTE.value:
            tasa = tasa_sd if tasa_sd else Decimal("0.20")
            valor_depreciacion = _calc_saldo_decreciente(valor_libro_anterior, valor_residual, tasa)
        else:
            valor_depreciacion = _calc_linea_recta(
                valor_libro_anterior,
                valor_residual,
                obj.vida_util_meses,
            )

        valor_libro_nuevo = (valor_libro_anterior - valor_depreciacion).quantize(Decimal("0.01"))
        dep = repository.create_depreciacion(
            db,
            {
                "activo_id": activo_id,
                "periodo": periodo,
                "metodo": obj.metodo_depreciacion,
                "valor_depreciacion": valor_depreciacion,
                "valor_libro_anterior": valor_libro_anterior,
                "valor_libro_nuevo": valor_libro_nuevo,
            },
        )
        obj.valor_libro = valor_libro_nuevo
        db.commit()
        db.refresh(dep)
        return depreciacion_to_dict(dep)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def list_depreciaciones(activo_id: Optional[int] = None, periodo: Optional[str] = None):
    db = repository.get_db()
    try:
        return [
            depreciacion_to_dict(obj)
            for obj in repository.list_depreciaciones(db, activo_id=activo_id, periodo=periodo)
        ]
    finally:
        db.close()


def delete_depreciacion(dep_id: int) -> bool:
    db = repository.get_db()
    try:
        dep = repository.get_depreciacion(db, dep_id)
        if not dep:
            return False
        activo = repository.get_activo(db, dep.activo_id)
        if activo:
            activo.valor_libro = dep.valor_libro_anterior
        repository.delete_record(db, dep)
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def list_asignaciones(activo_id: Optional[int] = None, estado: Optional[str] = None):
    db = repository.get_db()
    try:
        return [
            asignacion_to_dict(obj)
            for obj in repository.list_asignaciones(db, activo_id=activo_id, estado=estado)
        ]
    finally:
        db.close()


def create_asignacion(data: Dict[str, Any]):
    db = repository.get_db()
    try:
        payload = dict(data)
        if payload.get("fecha_asignacion") is None:
            payload["fecha_asignacion"] = date.today()
        obj = repository.create_asignacion(db, payload)
        activo = repository.get_activo(db, payload["activo_id"])
        if activo and activo.estado == EstadoActivo.ACTIVO.value:
            activo.estado = EstadoActivo.ASIGNADO.value
        db.commit()
        db.refresh(obj)
        return asignacion_to_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_asignacion(asig_id: int, data: Dict[str, Any]):
    db = repository.get_db()
    try:
        obj = repository.get_asignacion(db, asig_id)
        if not obj:
            return None
        repository.update_asignacion(db, obj, data)
        if data.get("estado") == EstadoAsignacion.DEVUELTO.value:
            activo = repository.get_activo(db, obj.activo_id)
            if activo and activo.estado == EstadoActivo.ASIGNADO.value:
                activo.estado = EstadoActivo.ACTIVO.value
        db.commit()
        db.refresh(obj)
        return asignacion_to_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_asignacion(asig_id: int) -> bool:
    db = repository.get_db()
    try:
        obj = repository.get_asignacion(db, asig_id)
        if not obj:
            return False
        repository.delete_record(db, obj)
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def list_mantenimientos(activo_id: Optional[int] = None, estado: Optional[str] = None):
    db = repository.get_db()
    try:
        return [
            mantenimiento_to_dict(obj)
            for obj in repository.list_mantenimientos(db, activo_id=activo_id, estado=estado)
        ]
    finally:
        db.close()


def create_mantenimiento(data: Dict[str, Any]):
    db = repository.get_db()
    try:
        obj = repository.create_mantenimiento(db, data)
        activo = repository.get_activo(db, data["activo_id"])
        if (
            activo
            and data.get("estado") == EstadoMantenimiento.EN_PROCESO.value
            and activo.estado == EstadoActivo.ACTIVO.value
        ):
            activo.estado = EstadoActivo.EN_MANTENIMIENTO.value
        db.commit()
        db.refresh(obj)
        return mantenimiento_to_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_mantenimiento(mant_id: int, data: Dict[str, Any]):
    db = repository.get_db()
    try:
        obj = repository.get_mantenimiento(db, mant_id)
        if not obj:
            return None
        repository.update_mantenimiento(db, obj, data)
        if data.get("estado") == EstadoMantenimiento.COMPLETADO.value:
            activo = repository.get_activo(db, obj.activo_id)
            if activo and activo.estado == EstadoActivo.EN_MANTENIMIENTO.value:
                activo.estado = EstadoActivo.ACTIVO.value
        db.commit()
        db.refresh(obj)
        return mantenimiento_to_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_mantenimiento(mant_id: int) -> bool:
    db = repository.get_db()
    try:
        obj = repository.get_mantenimiento(db, mant_id)
        if not obj:
            return False
        repository.delete_record(db, obj)
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def list_bajas():
    db = repository.get_db()
    try:
        return [baja_to_dict(obj) for obj in repository.list_bajas(db)]
    finally:
        db.close()


def create_baja(data: Dict[str, Any]):
    db = repository.get_db()
    try:
        payload = dict(data)
        if payload.get("fecha_baja") is None:
            payload["fecha_baja"] = date.today()
        obj = repository.create_baja(db, payload)
        activo = repository.get_activo(db, payload["activo_id"])
        if activo:
            activo.estado = EstadoActivo.DADO_DE_BAJA.value
        db.commit()
        db.refresh(obj)
        return baja_to_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_baja(baja_id: int) -> bool:
    db = repository.get_db()
    try:
        obj = repository.get_baja(db, baja_id)
        if not obj:
            return False
        activo = repository.get_activo(db, obj.activo_id)
        if activo and activo.estado == EstadoActivo.DADO_DE_BAJA.value:
            activo.estado = EstadoActivo.ACTIVO.value
        repository.delete_record(db, obj)
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def get_af_resumen():
    db = repository.get_db()
    try:
        total = repository.count_activos(db)
        activos = repository.count_activos_by_estado(db, EstadoActivo.ACTIVO.value)
        asignados = repository.count_activos_by_estado(db, EstadoActivo.ASIGNADO.value)
        en_mantenimiento = repository.count_activos_by_estado(db, EstadoActivo.EN_MANTENIMIENTO.value)
        dados_baja = repository.count_activos_by_estado(db, EstadoActivo.DADO_DE_BAJA.value)
        valor_libro_total = repository.sum_valor_libro_activos(db)
        valor_adquisicion_total = repository.sum_valor_adquisicion_activos(db)
        depreciacion_acumulada = float(valor_adquisicion_total) - float(valor_libro_total)
        return {
            "total_activos": total,
            "activos_activos": activos,
            "activos_asignados": asignados,
            "activos_en_mantenimiento": en_mantenimiento,
            "activos_dados_baja": dados_baja,
            "valor_libro_total": dec_str(valor_libro_total),
            "valor_adquisicion_total": dec_str(valor_adquisicion_total),
            "depreciacion_acumulada": dec_str(max(depreciacion_acumulada, 0)),
        }
    finally:
        db.close()

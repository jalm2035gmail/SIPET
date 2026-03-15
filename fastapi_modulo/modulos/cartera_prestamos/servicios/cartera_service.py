from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError

from fastapi_modulo.modulos.cartera_prestamos.modelos.enums import BucketMora, EstadoCredito, NivelRiesgo
from fastapi_modulo.modulos.cartera_prestamos.modelos.schemas import (
    ClienteCreateSchema,
    ClienteResponseSchema,
    CreditoCreateSchema,
    CreditoResponseSchema,
    ResumenCarteraSchema,
)
from fastapi_modulo.modulos.cartera_prestamos.repositorios import cartera_repository


def clasificar_bucket_mora(dias_mora: int) -> BucketMora:
    if dias_mora <= 0:
        return BucketMora.CORRIENTE
    if dias_mora <= 8:
        return BucketMora.MORA_1_8
    if dias_mora <= 30:
        return BucketMora.MORA_9_30
    if dias_mora <= 60:
        return BucketMora.MORA_31_60
    if dias_mora <= 90:
        return BucketMora.MORA_61_90
    return BucketMora.MORA_MAS_90


def _estado_credito_por_mora(dias_mora: int) -> EstadoCredito:
    return EstadoCredito.EN_MORA if dias_mora > 0 else EstadoCredito.VIGENTE


def _porcentaje_cobertura(monto_vencido: Decimal, saldo_total: Decimal) -> Decimal:
    if saldo_total <= 0:
        return Decimal("0")
    return (monto_vencido / saldo_total).quantize(Decimal("0.0001"))


def crear_cliente(data: dict) -> ClienteResponseSchema:
    payload = ClienteCreateSchema(**data)
    db = cartera_repository.get_db()
    try:
        cartera_repository.ensure_schema()
        obj = cartera_repository.create_cliente(db, payload.model_dump(mode="python"))
        db.commit()
        db.refresh(obj)
        return ClienteResponseSchema.model_validate(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def crear_credito(data: dict) -> CreditoResponseSchema:
    payload = CreditoCreateSchema(**data)
    db = cartera_repository.get_db()
    try:
        cartera_repository.ensure_schema()
        obj = cartera_repository.create_credito(
            db,
            {
                **payload.model_dump(mode="python"),
                "estado": EstadoCredito.VIGENTE.value,
                "bucket_mora": BucketMora.CORRIENTE.value,
                "dias_mora": 0,
            },
        )
        cartera_repository.upsert_saldo_credito(
            db,
            obj.id,
            {
                "saldo_capital": payload.saldo_capital,
                "saldo_interes": Decimal("0"),
                "saldo_mora": Decimal("0"),
                "saldo_total": payload.saldo_capital,
                "fecha_corte": payload.fecha_desembolso,
            },
        )
        cartera_repository.upsert_mora_credito(
            db,
            obj.id,
            {
                "fecha_exigible": payload.fecha_vencimiento,
                "dias_mora": 0,
                "bucket": BucketMora.CORRIENTE.value,
                "monto_vencido": Decimal("0"),
                "porcentaje_cobertura": Decimal("0"),
            },
        )
        db.commit()
        db.refresh(obj)
        return CreditoResponseSchema.model_validate(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def actualizar_mora_credito(
    credito_id: int,
    *,
    fecha_exigible: date | None,
    saldo_capital: Decimal,
    saldo_interes: Decimal = Decimal("0"),
    saldo_mora: Decimal = Decimal("0"),
) -> CreditoResponseSchema | None:
    db = cartera_repository.get_db()
    try:
        credito = cartera_repository.get_credito(db, credito_id)
        if not credito:
            return None
        dias_mora = max((date.today() - fecha_exigible).days, 0) if fecha_exigible else 0
        bucket = clasificar_bucket_mora(dias_mora)
        saldo_total = saldo_capital + saldo_interes + saldo_mora
        monto_vencido = saldo_capital if dias_mora > 0 else Decimal("0")

        credito.estado = _estado_credito_por_mora(dias_mora).value
        credito.bucket_mora = bucket.value
        credito.dias_mora = dias_mora
        credito.saldo_capital = saldo_capital

        cartera_repository.upsert_saldo_credito(
            db,
            credito.id,
            {
                "saldo_capital": saldo_capital,
                "saldo_interes": saldo_interes,
                "saldo_mora": saldo_mora,
                "saldo_total": saldo_total,
                "fecha_corte": date.today(),
            },
        )
        cartera_repository.upsert_mora_credito(
            db,
            credito.id,
            {
                "fecha_exigible": fecha_exigible,
                "dias_mora": dias_mora,
                "bucket": bucket.value,
                "monto_vencido": monto_vencido,
                "porcentaje_cobertura": _porcentaje_cobertura(monto_vencido, saldo_total),
            },
        )
        db.commit()
        db.refresh(credito)
        return CreditoResponseSchema.model_validate(credito)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def obtener_resumen_cartera() -> ResumenCarteraSchema:
    db = cartera_repository.get_db()
    try:
        creditos = cartera_repository.list_creditos(db)
        moras = cartera_repository.list_moras(db)
        saldo_total = cartera_repository.sum_saldo_total(db)
        saldo_vencido = cartera_repository.sum_monto_vencido(db)
        distribucion = {bucket.value: 0 for bucket in BucketMora}
        for mora in moras:
            distribucion[mora.bucket] = distribucion.get(mora.bucket, 0) + 1
        indice_mora = Decimal("0")
        if saldo_total > 0:
            indice_mora = (saldo_vencido / saldo_total).quantize(Decimal("0.0001"))
        return ResumenCarteraSchema(
            total_creditos=len(creditos),
            total_clientes=cartera_repository.count_clientes(db),
            saldo_total=saldo_total,
            saldo_vencido=saldo_vencido,
            indice_mora=indice_mora,
            distribucion_buckets=distribucion,
        )
    finally:
        db.close()


def resolver_nivel_riesgo(dias_mora: int) -> NivelRiesgo:
    if dias_mora <= 8:
        return NivelRiesgo.BAJO
    if dias_mora <= 30:
        return NivelRiesgo.MEDIO
    if dias_mora <= 90:
        return NivelRiesgo.ALTO
    return NivelRiesgo.CRITICO

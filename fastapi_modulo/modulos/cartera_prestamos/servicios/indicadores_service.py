from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError

from fastapi_modulo.modulos.cartera_prestamos.modelos.enums import NivelRiesgo, TipoIndicador
from fastapi_modulo.modulos.cartera_prestamos.modelos.schemas import IndicadorSnapshotSchema
from fastapi_modulo.modulos.cartera_prestamos.repositorios import cartera_repository, cobranza_repository


def resolver_semaforo(valor: Decimal, meta: Decimal | None, *, invertido: bool = False) -> NivelRiesgo:
    if meta is None:
        return NivelRiesgo.BAJO
    if invertido:
        if valor <= meta:
            return NivelRiesgo.BAJO
        if valor <= meta * Decimal("1.15"):
            return NivelRiesgo.MEDIO
        if valor <= meta * Decimal("1.35"):
            return NivelRiesgo.ALTO
        return NivelRiesgo.CRITICO
    if valor >= meta:
        return NivelRiesgo.BAJO
    if valor >= meta * Decimal("0.85"):
        return NivelRiesgo.MEDIO
    if valor >= meta * Decimal("0.70"):
        return NivelRiesgo.ALTO
    return NivelRiesgo.CRITICO


def calcular_indice_mora() -> Decimal:
    db = cartera_repository.get_db()
    try:
        saldo_total = cartera_repository.sum_saldo_total(db)
        saldo_vencido = cartera_repository.sum_monto_vencido(db)
        if saldo_total <= 0:
            return Decimal("0")
        return (saldo_vencido / saldo_total).quantize(Decimal("0.0001"))
    finally:
        db.close()


def calcular_efectividad_cobranza() -> Decimal:
    db = cartera_repository.get_db()
    try:
        gestiones = cobranza_repository.list_gestiones(db)
        if not gestiones:
            return Decimal("0")
        exitosas = sum(1 for gestion in gestiones if gestion.resultado in {"promesa_pago", "pago_parcial", "pago_total"})
        return (Decimal(exitosas) / Decimal(len(gestiones))).quantize(Decimal("0.0001"))
    finally:
        db.close()


def construir_indicadores() -> list[IndicadorSnapshotSchema]:
    db = cartera_repository.get_db()
    try:
        saldo_total = cartera_repository.sum_saldo_total(db)
        saldo_vencido = cartera_repository.sum_monto_vencido(db)
        promesas = cobranza_repository.list_promesas_pago(db)
        promesas_cumplidas = sum(1 for promesa in promesas if promesa.estado == "cumplida")
        cumplimiento = Decimal("0")
        if promesas:
            cumplimiento = (Decimal(promesas_cumplidas) / Decimal(len(promesas))).quantize(Decimal("0.0001"))
        indice_mora = Decimal("0")
        if saldo_total > 0:
            indice_mora = (saldo_vencido / saldo_total).quantize(Decimal("0.0001"))
        efectividad = calcular_efectividad_cobranza()
        return [
            IndicadorSnapshotSchema(
                tipo_indicador=TipoIndicador.MORA,
                nombre="Indice de mora",
                valor=indice_mora,
                meta=Decimal("0.0500"),
                semaforo=resolver_semaforo(indice_mora, Decimal("0.0500"), invertido=True),
                detalle="Porción de cartera vencida sobre saldo total.",
            ),
            IndicadorSnapshotSchema(
                tipo_indicador=TipoIndicador.PROMESAS,
                nombre="Cumplimiento de promesas",
                valor=cumplimiento,
                meta=Decimal("0.8500"),
                semaforo=resolver_semaforo(cumplimiento, Decimal("0.8500")),
                detalle="Promesas cumplidas sobre promesas registradas.",
            ),
            IndicadorSnapshotSchema(
                tipo_indicador=TipoIndicador.EFECTIVIDAD,
                nombre="Efectividad de cobranza",
                valor=efectividad,
                meta=Decimal("0.6500"),
                semaforo=resolver_semaforo(efectividad, Decimal("0.6500")),
                detalle="Gestiones con resultado útil sobre total de gestiones.",
            ),
        ]
    finally:
        db.close()


def guardar_indicadores(fecha_corte: date | None = None) -> list[IndicadorSnapshotSchema]:
    fecha_objetivo = fecha_corte or date.today()
    snapshots = construir_indicadores()
    db = cartera_repository.get_db()
    try:
        for indicador in snapshots:
            cartera_repository.save_indicador(
                db,
                {
                    "fecha_corte": fecha_objetivo,
                    "tipo_indicador": indicador.tipo_indicador.value,
                    "nombre": indicador.nombre,
                    "valor": indicador.valor,
                    "meta": indicador.meta,
                    "semaforo": indicador.semaforo.value,
                    "detalle": indicador.detalle,
                },
            )
        db.commit()
        return snapshots
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()

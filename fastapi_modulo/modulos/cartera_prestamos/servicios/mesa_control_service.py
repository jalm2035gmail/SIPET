from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from fastapi_modulo.modulos.cartera_prestamos.modelos.schemas import MesaControlResumenSchema
from fastapi_modulo.modulos.cartera_prestamos.repositorios import cartera_repository, cobranza_repository
from fastapi_modulo.modulos.cartera_prestamos.servicios.cartera_service import obtener_resumen_cartera
from fastapi_modulo.modulos.cartera_prestamos.servicios.indicadores_service import calcular_efectividad_cobranza
from fastapi_modulo.modulos.cartera_prestamos.servicios.recuperacion_service import calcular_cumplimiento_promesas, listar_casos_criticos


def construir_resumen_mesa_control(fecha_corte: date | None = None) -> MesaControlResumenSchema:
    resumen = obtener_resumen_cartera()
    cumplimiento_promesas = calcular_cumplimiento_promesas()
    efectividad = calcular_efectividad_cobranza()
    recuperacion_mes = (resumen.saldo_vencido * cumplimiento_promesas).quantize(Decimal("0.01"))
    return MesaControlResumenSchema(
        fecha_corte=fecha_corte or date.today(),
        cartera=resumen,
        recuperacion_mes=recuperacion_mes,
        efectividad_cobranza=efectividad,
        promesas_pendientes=summary_promesas_pendientes(),
        casos_criticos=len(listar_casos_criticos()),
    )


def obtener_snapshot_mesa_control() -> dict:
    db = cartera_repository.get_db()
    try:
        hoy = date.today()
        resumen = obtener_resumen_cartera()
        creditos = cartera_repository.list_creditos(db)
        castigos = cobranza_repository.list_castigos(db)
        buckets = defaultdict(lambda: {"casos": 0, "saldo": Decimal("0")})
        saldos_sucursal = defaultdict(Decimal)
        saldos_asesor = defaultdict(Decimal)
        saldos_producto = defaultdict(Decimal)
        evolucion = defaultdict(lambda: Decimal("0"))
        cartera_vigente = Decimal("0")
        cobertura = Decimal("0")
        saldo_total_mora = Decimal("0")
        saldo_total_vencido = Decimal("0")

        for credito in creditos:
            saldo_total = Decimal(str(credito.saldo.saldo_total if credito.saldo else credito.saldo_capital or 0))
            bucket = credito.bucket_mora
            buckets[bucket]["casos"] += 1
            buckets[bucket]["saldo"] += saldo_total
            saldos_sucursal[credito.sucursal or "Sin sucursal"] += saldo_total
            saldos_asesor[credito.oficial or "Sin asesor"] += saldo_total
            saldos_producto[credito.producto or "Sin producto"] += saldo_total
            evolucion[credito.fecha_desembolso.strftime("%Y-%m")] += saldo_total
            if credito.dias_mora <= 0:
                cartera_vigente += saldo_total
            if credito.saldo:
                saldo_total_mora += Decimal(str(credito.saldo.saldo_mora or 0))
            if credito.mora:
                saldo_total_vencido += Decimal(str(credito.mora.monto_vencido or 0))

        if saldo_total_vencido > 0:
            cobertura = (saldo_total_mora / saldo_total_vencido).quantize(Decimal("0.0001"))

        castigos_periodo = sum(
            Decimal(str(item.monto_castigado or 0))
            for item in castigos
            if item.fecha_castigo.year == hoy.year and item.fecha_castigo.month == hoy.month
        )
        recuperacion_periodo = (resumen.saldo_vencido * calcular_cumplimiento_promesas()).quantize(Decimal("0.01"))

        return {
            "fecha_corte": hoy.isoformat(),
            "cartera_total": float(resumen.saldo_total),
            "cartera_vigente": float(cartera_vigente),
            "cartera_vencida": float(resumen.saldo_vencido),
            "indice_morosidad": float(resumen.indice_mora),
            "cobertura": float(cobertura),
            "castigos_periodo": float(castigos_periodo),
            "recuperacion_periodo": float(recuperacion_periodo),
            "saldo_por_sucursal": _ranking(saldos_sucursal),
            "saldo_por_asesor": _ranking(saldos_asesor),
            "saldo_por_producto": _ranking(saldos_producto),
            "evolucion_mensual": _serie_mensual(evolucion),
            "buckets_mora": [
                {"bucket": bucket, "casos": valores["casos"], "saldo": float(valores["saldo"])}
                for bucket, valores in sorted(buckets.items())
            ],
        }
    finally:
        db.close()


def summary_promesas_pendientes() -> int:
    from fastapi_modulo.modulos.cartera_prestamos.repositorios import cartera_repository, cobranza_repository

    db = cartera_repository.get_db()
    try:
        return len(cobranza_repository.list_promesas_pago(db, estado="pendiente"))
    finally:
        db.close()


def _ranking(grouped: dict[str, Decimal], limit: int = 10) -> list[dict]:
    items = [{"nombre": key, "saldo": float(value)} for key, value in grouped.items()]
    items.sort(key=lambda item: item["saldo"], reverse=True)
    return items[:limit]


def _serie_mensual(grouped: dict[str, Decimal]) -> list[dict]:
    return [
        {"periodo": periodo, "saldo": float(saldo)}
        for periodo, saldo in sorted(grouped.items())
    ]

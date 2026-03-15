from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from fastapi_modulo.modulos.cartera_prestamos.modelos.enums import NivelRiesgo
from fastapi_modulo.modulos.cartera_prestamos.repositorios import cartera_repository, cobranza_repository
from fastapi_modulo.modulos.cartera_prestamos.servicios.cartera_service import resolver_nivel_riesgo


def obtener_snapshot_gestion() -> dict:
    db = cartera_repository.get_db()
    try:
        creditos = cartera_repository.list_creditos(db)
        reestructuras = cobranza_repository.list_reestructuras(db)
        hoy = date.today()

        pipeline = defaultdict(int)
        saldo_por_producto = defaultdict(Decimal)
        saldo_por_asesor = defaultdict(Decimal)
        expedientes = []
        renovaciones = 0
        casos_documentacion_incompleta = 0
        desembolsos_cantidad = 0
        desembolsos_monto = Decimal("0")
        score_total = Decimal("0")
        score_count = 0

        for credito in creditos:
            pipeline[credito.etapa_colocacion] += 1
            saldo = Decimal(str(credito.saldo.saldo_total if credito.saldo else credito.saldo_capital or 0))
            saldo_por_producto[credito.producto or "Sin producto"] += saldo
            saldo_por_asesor[credito.oficial or "Sin asesor"] += saldo
            nivel = resolver_nivel_riesgo(credito.dias_mora)
            if credito.es_renovacion:
                renovaciones += 1
            if not credito.documentacion_completa:
                casos_documentacion_incompleta += 1
            if credito.fecha_desembolso and credito.fecha_desembolso.year == hoy.year and credito.fecha_desembolso.month == hoy.month:
                desembolsos_cantidad += 1
                desembolsos_monto += Decimal(str(credito.monto_original or 0))
            score_total += Decimal(str(credito.score_riesgo or 0))
            score_count += 1
            expedientes.append(
                {
                    "credito_id": credito.id,
                    "numero_credito": credito.numero_credito,
                    "cliente": credito.cliente.nombre_completo if credito.cliente else f"Cliente {credito.cliente_id}",
                    "score_riesgo": float(credito.score_riesgo or 0),
                    "nivel_riesgo": nivel.value,
                    "semaforo": nivel.value,
                    "documentacion_completa": credito.documentacion_completa,
                }
            )

        expedientes.sort(key=lambda item: (item["documentacion_completa"], item["score_riesgo"]), reverse=False)
        reestructuras_periodo = [
            item for item in reestructuras if item.fecha_reestructura.year == hoy.year and item.fecha_reestructura.month == hoy.month
        ]
        score_promedio = (score_total / Decimal(score_count)).quantize(Decimal("0.01")) if score_count else Decimal("0")

        return {
            "fecha_corte": hoy.isoformat(),
            "pipeline_colocacion": dict(sorted(pipeline.items())),
            "renovaciones": renovaciones,
            "reestructuras_periodo": len(reestructuras_periodo),
            "desembolsos_periodo": {
                "cantidad": desembolsos_cantidad,
                "monto": float(desembolsos_monto),
            },
            "score_riesgo": {
                "promedio": float(score_promedio),
                "distribucion": _distribucion_riesgo(expedientes),
            },
            "saldo_por_producto": _ranking_montos(saldo_por_producto),
            "saldo_por_asesor": _ranking_montos(saldo_por_asesor),
            "casos_documentacion_incompleta": casos_documentacion_incompleta,
            "expedientes": expedientes[:25],
        }
    finally:
        db.close()


def _distribucion_riesgo(expedientes: list[dict]) -> dict[str, int]:
    distribucion = {nivel.value: 0 for nivel in NivelRiesgo}
    for expediente in expedientes:
        distribucion[expediente["nivel_riesgo"]] += 1
    return distribucion


def _ranking_montos(grouped: dict[str, Decimal], limit: int = 10) -> list[dict]:
    items = [
        {"nombre": nombre, "saldo": float(saldo)}
        for nombre, saldo in grouped.items()
    ]
    items.sort(key=lambda item: item["saldo"], reverse=True)
    return items[:limit]

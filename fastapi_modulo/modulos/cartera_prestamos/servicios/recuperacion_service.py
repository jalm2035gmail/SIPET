from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError

from fastapi_modulo.modulos.cartera_prestamos.modelos.enums import BucketMora, EstadoCredito, EstadoPromesaPago
from fastapi_modulo.modulos.cartera_prestamos.modelos.schemas import (
    GestionCobranzaCreateSchema,
    GestionCobranzaResponseSchema,
    PromesaPagoCreateSchema,
    PromesaPagoResponseSchema,
    PromesaPagoUpdateSchema,
)
from fastapi_modulo.modulos.cartera_prestamos.repositorios import cartera_repository, cobranza_repository
from fastapi_modulo.modulos.cartera_prestamos.servicios.cartera_service import clasificar_bucket_mora


def registrar_promesa_pago(data: dict) -> PromesaPagoResponseSchema:
    payload = PromesaPagoCreateSchema(**data)
    db = cartera_repository.get_db()
    try:
        obj = cobranza_repository.create_promesa_pago(
            db,
            {
                **payload.model_dump(mode="python"),
                "fecha_promesa": date.today(),
                "estado": EstadoPromesaPago.PENDIENTE.value,
                "monto_cumplido": Decimal("0"),
            },
        )
        db.commit()
        db.refresh(obj)
        return PromesaPagoResponseSchema.model_validate(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def actualizar_promesa_pago(promesa_id: int, data: dict) -> PromesaPagoResponseSchema | None:
    payload = PromesaPagoUpdateSchema(**data)
    db = cartera_repository.get_db()
    try:
        obj = cobranza_repository.get_promesa_pago(db, promesa_id)
        if not obj:
            return None
        cobranza_repository.update_promesa_pago(db, obj, payload.model_dump(mode="python"))
        db.commit()
        db.refresh(obj)
        return PromesaPagoResponseSchema.model_validate(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def registrar_gestion_cobranza(data: dict) -> GestionCobranzaResponseSchema:
    payload = GestionCobranzaCreateSchema(**data)
    db = cartera_repository.get_db()
    try:
        obj = cobranza_repository.create_gestion(db, payload.model_dump(mode="python"))
        db.commit()
        db.refresh(obj)
        return GestionCobranzaResponseSchema.model_validate(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def calcular_cumplimiento_promesas() -> Decimal:
    db = cartera_repository.get_db()
    try:
        promesas = cobranza_repository.list_promesas_pago(db)
        if not promesas:
            return Decimal("0")
        cumplidas = sum(1 for promesa in promesas if promesa.estado == EstadoPromesaPago.CUMPLIDA.value)
        return (Decimal(cumplidas) / Decimal(len(promesas))).quantize(Decimal("0.0001"))
    finally:
        db.close()


def listar_casos_criticos(limit: int = 10) -> list[dict]:
    db = cartera_repository.get_db()
    try:
        creditos = cartera_repository.list_creditos(db)
        criticos = []
        for credito in creditos:
            if credito.dias_mora < 31:
                continue
            cliente = credito.cliente.nombre_completo if credito.cliente else f"Cliente {credito.cliente_id}"
            criticos.append(
                {
                    "credito_id": credito.id,
                    "numero_credito": credito.numero_credito,
                    "cliente": cliente,
                    "saldo": float(credito.saldo.saldo_total if credito.saldo else credito.saldo_capital or 0),
                    "dias_mora": credito.dias_mora,
                    "bucket_mora": credito.bucket_mora,
                    "estado": credito.estado,
                }
            )
        criticos.sort(key=lambda item: item["dias_mora"], reverse=True)
        return criticos[:limit]
    finally:
        db.close()


def aplicar_recuperacion_credito(credito_id: int, monto_recuperado: Decimal) -> bool:
    db = cartera_repository.get_db()
    try:
        credito = cartera_repository.get_credito(db, credito_id)
        if not credito or not credito.saldo:
            return False
        nuevo_saldo_total = max(Decimal(credito.saldo.saldo_total) - monto_recuperado, Decimal("0"))
        nuevo_saldo_capital = max(Decimal(credito.saldo.saldo_capital) - monto_recuperado, Decimal("0"))
        dias_mora = 0 if nuevo_saldo_total == 0 else credito.dias_mora
        bucket = clasificar_bucket_mora(dias_mora)
        credito.estado = EstadoCredito.VIGENTE.value if nuevo_saldo_total == 0 else credito.estado
        credito.bucket_mora = bucket.value
        credito.dias_mora = dias_mora
        credito.saldo_capital = nuevo_saldo_capital
        cartera_repository.upsert_saldo_credito(
            db,
            credito.id,
            {
                "saldo_capital": nuevo_saldo_capital,
                "saldo_interes": credito.saldo.saldo_interes,
                "saldo_mora": credito.saldo.saldo_mora,
                "saldo_total": nuevo_saldo_total,
                "fecha_corte": date.today(),
            },
        )
        cartera_repository.upsert_mora_credito(
            db,
            credito.id,
            {
                "fecha_exigible": credito.mora.fecha_exigible if credito.mora else None,
                "dias_mora": dias_mora,
                "bucket": bucket.value,
                "monto_vencido": Decimal("0") if nuevo_saldo_total == 0 else (credito.mora.monto_vencido if credito.mora else Decimal("0")),
                "porcentaje_cobertura": Decimal("0") if nuevo_saldo_total == 0 else (credito.mora.porcentaje_cobertura if credito.mora else Decimal("0")),
            },
        )
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def obtener_snapshot_recuperacion(meta_periodo: Decimal = Decimal("0")) -> dict:
    db = cartera_repository.get_db()
    try:
        hoy = date.today()
        promesas = cobranza_repository.list_promesas_pago(db)
        gestiones = cobranza_repository.list_gestiones(db)
        creditos = cartera_repository.list_creditos(db)

        promesas_activas = [item for item in promesas if item.estado == EstadoPromesaPago.PENDIENTE.value]
        gestiones_hoy = [item for item in gestiones if item.fecha_gestion.date() == hoy]
        visitas_programadas = [
            item for item in gestiones
            if item.tipo_gestion == "visita" and item.fecha_proxima_accion and item.fecha_proxima_accion >= hoy
        ]
        recuperado_periodo = sum(
            Decimal(str(item.monto_cumplido or 0))
            for item in promesas
            if item.fecha_promesa.year == hoy.year and item.fecha_promesa.month == hoy.month
        )
        efectividad_por_gestor = _efectividad_por_gestor(gestiones)
        cartera_por_tramo = defaultdict(lambda: {"casos": 0, "saldo": Decimal("0")})
        for credito in creditos:
            if credito.dias_mora <= 0:
                continue
            saldo = Decimal(str(credito.saldo.saldo_total if credito.saldo else credito.saldo_capital or 0))
            cartera_por_tramo[credito.bucket_mora]["casos"] += 1
            cartera_por_tramo[credito.bucket_mora]["saldo"] += saldo

        return {
            "fecha_corte": hoy.isoformat(),
            "promesas_pago_activas": len(promesas_activas),
            "gestiones_dia": len(gestiones_hoy),
            "visitas_programadas": len(visitas_programadas),
            "cartera_vencida_por_tramo": [
                {"tramo": tramo, "casos": valores["casos"], "saldo": float(valores["saldo"])}
                for tramo, valores in sorted(cartera_por_tramo.items())
            ],
            "efectividad_cobranza": float(calcular_cumplimiento_promesas()),
            "efectividad_por_gestor": efectividad_por_gestor,
            "recuperado_vs_meta": {
                "recuperado": float(recuperado_periodo),
                "meta": float(meta_periodo),
                "avance": float((recuperado_periodo / meta_periodo).quantize(Decimal("0.0001")) if meta_periodo > 0 else Decimal("0")),
            },
            "casos_criticos": listar_casos_criticos(),
        }
    finally:
        db.close()


def _efectividad_por_gestor(gestiones: list) -> list[dict]:
    agrupado: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "efectivas": 0})
    for gestion in gestiones:
        gestor = gestion.responsable or "Sin gestor"
        agrupado[gestor]["total"] += 1
        if gestion.resultado in {"promesa_pago", "pago_parcial", "pago_total"}:
            agrupado[gestor]["efectivas"] += 1
    respuesta = []
    for gestor, valores in agrupado.items():
        total = valores["total"]
        efectividad = Decimal("0")
        if total:
            efectividad = (Decimal(valores["efectivas"]) / Decimal(total)).quantize(Decimal("0.0001"))
        respuesta.append({"gestor": gestor, "efectividad": float(efectividad), "gestiones": total})
    respuesta.sort(key=lambda item: item["efectividad"], reverse=True)
    return respuesta

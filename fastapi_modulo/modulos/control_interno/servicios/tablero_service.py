from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from fastapi_modulo.modulos.control_interno.modelos.enums import (
    EstadoAccionCorrectiva,
    EstadoActividad,
    EstadoControl,
    EstadoHallazgo,
    NivelRiesgoHallazgo,
    ResultadoEvaluacion,
)
from fastapi_modulo.modulos.control_interno.servicios.controles_service import listar as listar_controles
from fastapi_modulo.modulos.control_interno.servicios.evidencia_service import all_evidencias
from fastapi_modulo.modulos.control_interno.servicios.hallazgo_service import all_acciones, all_hallazgos
from fastapi_modulo.modulos.control_interno.servicios.programa_service import all_actividades, listar_programas_service

RECENT_EVIDENCE_DAYS = 90


def _conteo(items: list[Any], campo: str) -> dict[str, int]:
    conteo: dict[str, int] = {}
    for item in items:
        value = getattr(item, campo, None) or "—"
        conteo[value] = conteo.get(value, 0) + 1
    return conteo


def _pct(parte: int, total: int) -> float:
    return round(parte / total * 100, 1) if total else 0.0


def _avg(values: list[int]) -> float:
    return round(sum(values) / len(values), 1) if values else 0.0


def _to_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _month_key(value) -> str:
    current = _to_date(value)
    return current.strftime("%Y-%m") if current else "Sin fecha"


def _entity_from_dict(item: dict[str, Any]):
    return type("Entity", (), item)


def kpi_controles_service() -> dict[str, Any]:
    controles = listar_controles()
    evidencias = all_evidencias()
    total = len(controles)
    activos = sum(1 for item in controles if item["estado"] == EstadoControl.ACTIVO.value)
    cutoff = date.today() - timedelta(days=RECENT_EVIDENCE_DAYS)
    ultima_evidencia_por_control: dict[int, date] = {}
    for evidencia in evidencias:
        if not evidencia.control_id:
            continue
        fecha = _to_date(evidencia.fecha_evidencia) or _to_date(evidencia.creado_en)
        if not fecha:
            continue
        ultima = ultima_evidencia_por_control.get(evidencia.control_id)
        if not ultima or fecha > ultima:
            ultima_evidencia_por_control[evidencia.control_id] = fecha

    controles_sin_evidencia_reciente = 0
    cumplimiento_por_componente: dict[str, dict[str, Any]] = {}
    for control in controles:
        control_id = control["id"]
        ultima = ultima_evidencia_por_control.get(control_id)
        if not ultima or ultima < cutoff:
            controles_sin_evidencia_reciente += 1
        componente = control["componente"] or "—"
        bucket = cumplimiento_por_componente.setdefault(componente, {"total": 0, "con_evidencia_reciente": 0, "sin_evidencia_reciente": 0})
        bucket["total"] += 1
        if ultima and ultima >= cutoff:
            bucket["con_evidencia_reciente"] += 1
        else:
            bucket["sin_evidencia_reciente"] += 1
    for bucket in cumplimiento_por_componente.values():
        bucket["porcentaje"] = _pct(bucket["con_evidencia_reciente"], bucket["total"])

    return {
        "total": total,
        "activos": activos,
        "inactivos": total - activos,
        "pct_activos": _pct(activos, total),
        "controles_sin_evidencia_reciente": controles_sin_evidencia_reciente,
        "por_componente": _conteo([_entity_from_dict(item) for item in controles], "componente"),
        "por_periodicidad": _conteo([_entity_from_dict(item) for item in controles], "periodicidad"),
        "cumplimiento_por_componente": cumplimiento_por_componente,
    }


def kpi_programa_service() -> dict[str, Any]:
    programas = listar_programas_service()
    actividades = all_actividades()
    total = len(actividades)
    today = date.today()
    completadas = sum(1 for item in actividades if item.estado == EstadoActividad.COMPLETADO.value)
    actividades_vencidas = sum(
        1
        for item in actividades
        if item.estado not in {EstadoActividad.COMPLETADO.value, EstadoActividad.CANCELADO.value}
        and _to_date(item.fecha_fin_programada)
        and _to_date(item.fecha_fin_programada) < today
    )
    cumplimiento_por_mes: dict[str, dict[str, Any]] = defaultdict(lambda: {"total": 0, "completadas": 0})
    cumplimiento_por_area: dict[str, dict[str, Any]] = defaultdict(lambda: {"total": 0, "completadas": 0})
    cumplimiento_por_componente: dict[str, dict[str, Any]] = defaultdict(lambda: {"total": 0, "completadas": 0})
    tendencia_mensual: dict[str, dict[str, int]] = defaultdict(lambda: {"programadas": 0, "completadas": 0})

    for item in actividades:
        mes = _month_key(item.fecha_fin_programada or item.fecha_inicio_programada or item.creado_en)
        area = (item.control.area if item.control else "") or "Sin area"
        componente = (item.control.componente if item.control else "") or "Sin componente"
        cumplimiento_por_mes[mes]["total"] += 1
        cumplimiento_por_area[area]["total"] += 1
        cumplimiento_por_componente[componente]["total"] += 1
        tendencia_mensual[mes]["programadas"] += 1
        if item.estado == EstadoActividad.COMPLETADO.value:
            cumplimiento_por_mes[mes]["completadas"] += 1
            cumplimiento_por_area[area]["completadas"] += 1
            cumplimiento_por_componente[componente]["completadas"] += 1
            tendencia_mensual[mes]["completadas"] += 1

    for dataset in (cumplimiento_por_mes, cumplimiento_por_area, cumplimiento_por_componente):
        for bucket in dataset.values():
            bucket["porcentaje"] = _pct(bucket["completadas"], bucket["total"])

    return {
        "total_programas": len(programas),
        "total_actividades": total,
        "completadas": completadas,
        "en_proceso": sum(1 for item in actividades if item.estado == EstadoActividad.EN_PROCESO.value),
        "programadas": sum(1 for item in actividades if item.estado == EstadoActividad.PROGRAMADO.value),
        "diferidas": sum(1 for item in actividades if item.estado == EstadoActividad.DIFERIDO.value),
        "canceladas": sum(1 for item in actividades if item.estado == EstadoActividad.CANCELADO.value),
        "actividades_vencidas": actividades_vencidas,
        "pct_completadas": _pct(completadas, total),
        "por_estado_programa": {item["estado"]: sum(1 for row in programas if row["estado"] == item["estado"]) for item in programas},
        "cumplimiento_por_mes": dict(sorted(cumplimiento_por_mes.items())),
        "cumplimiento_por_area": dict(sorted(cumplimiento_por_area.items())),
        "cumplimiento_por_componente": dict(sorted(cumplimiento_por_componente.items())),
        "tendencia_mensual": dict(sorted(tendencia_mensual.items())),
    }


def kpi_evidencias_service() -> dict[str, Any]:
    evidencias = all_evidencias()
    total = len(evidencias)
    cumple = sum(1 for item in evidencias if item.resultado_evaluacion == ResultadoEvaluacion.CUMPLE.value)
    parcial = sum(1 for item in evidencias if item.resultado_evaluacion == ResultadoEvaluacion.CUMPLE_PARCIALMENTE.value)
    no_cumple = sum(1 for item in evidencias if item.resultado_evaluacion == ResultadoEvaluacion.NO_CUMPLE.value)
    por_evaluar = sum(1 for item in evidencias if item.resultado_evaluacion == ResultadoEvaluacion.POR_EVALUAR.value)
    evaluadas = cumple + parcial + no_cumple
    tendencia_mensual: dict[str, dict[str, int]] = defaultdict(lambda: {"registradas": 0, "evaluadas": 0, "por_evaluar": 0})
    for item in evidencias:
        mes = _month_key(item.fecha_evidencia or item.creado_en)
        tendencia_mensual[mes]["registradas"] += 1
        if item.resultado_evaluacion == ResultadoEvaluacion.POR_EVALUAR.value:
            tendencia_mensual[mes]["por_evaluar"] += 1
        else:
            tendencia_mensual[mes]["evaluadas"] += 1

    return {
        "total": total,
        "cumple": cumple,
        "parcial": parcial,
        "no_cumple": no_cumple,
        "por_evaluar": por_evaluar,
        "evidencias_no_evaluadas": por_evaluar,
        "pct_cumple": _pct(cumple, evaluadas),
        "pct_parcial": _pct(parcial, evaluadas),
        "pct_no_cumple": _pct(no_cumple, evaluadas),
        "por_tipo": _conteo(evidencias, "tipo"),
        "tendencia_mensual": dict(sorted(tendencia_mensual.items())),
    }


def kpi_hallazgos_service() -> dict[str, Any]:
    hallazgos = all_hallazgos()
    acciones = all_acciones()
    total = len(hallazgos)
    today = date.today()
    ejecutadas = sum(1 for item in acciones if item.estado in (EstadoAccionCorrectiva.EJECUTADA.value, EstadoAccionCorrectiva.VERIFICADA.value))
    hallazgos_vencidos = sum(
        1
        for item in hallazgos
        if item.estado not in {EstadoHallazgo.SUBSANADO.value, EstadoHallazgo.CERRADO.value}
        and _to_date(item.fecha_limite)
        and _to_date(item.fecha_limite) < today
    )
    acciones_vencidas = sum(
        1
        for item in acciones
        if item.estado not in {EstadoAccionCorrectiva.EJECUTADA.value, EstadoAccionCorrectiva.VERIFICADA.value, EstadoAccionCorrectiva.CANCELADA.value}
        and _to_date(item.fecha_compromiso)
        and _to_date(item.fecha_compromiso) < today
    )
    tiempos_atencion: list[int] = []
    tiempos_cierre: list[int] = []
    tendencia_mensual: dict[str, dict[str, int]] = defaultdict(lambda: {"hallazgos": 0, "cerrados": 0})
    for item in hallazgos:
        fecha_deteccion = _to_date(item.fecha_deteccion) or _to_date(item.creado_en)
        mes = _month_key(fecha_deteccion)
        tendencia_mensual[mes]["hallazgos"] += 1
        acciones_hallazgo = list(item.acciones or [])
        if acciones_hallazgo and fecha_deteccion:
            primera_accion = min((_to_date(acc.fecha_ejecucion) or _to_date(acc.actualizado_en) for acc in acciones_hallazgo if _to_date(acc.fecha_ejecucion) or _to_date(acc.actualizado_en)), default=None)
            if primera_accion and primera_accion >= fecha_deteccion:
                tiempos_atencion.append((primera_accion - fecha_deteccion).days)
        if item.estado in {EstadoHallazgo.SUBSANADO.value, EstadoHallazgo.CERRADO.value} and fecha_deteccion:
            fecha_cierre = max((_to_date(acc.fecha_ejecucion) or _to_date(acc.actualizado_en) for acc in acciones_hallazgo if acc.estado in {EstadoAccionCorrectiva.EJECUTADA.value, EstadoAccionCorrectiva.VERIFICADA.value}), default=None)
            if fecha_cierre and fecha_cierre >= fecha_deteccion:
                tiempos_cierre.append((fecha_cierre - fecha_deteccion).days)
                tendencia_mensual[mes]["cerrados"] += 1

    return {
        "total": total,
        "abiertos": sum(1 for item in hallazgos if item.estado == EstadoHallazgo.ABIERTO.value),
        "en_atencion": sum(1 for item in hallazgos if item.estado == EstadoHallazgo.EN_ATENCION.value),
        "subsanados": sum(1 for item in hallazgos if item.estado == EstadoHallazgo.SUBSANADO.value),
        "cerrados": sum(1 for item in hallazgos if item.estado == EstadoHallazgo.CERRADO.value),
        "criticos": sum(1 for item in hallazgos if item.nivel_riesgo == NivelRiesgoHallazgo.CRITICO.value),
        "altos": sum(1 for item in hallazgos if item.nivel_riesgo == NivelRiesgoHallazgo.ALTO.value),
        "medios": sum(1 for item in hallazgos if item.nivel_riesgo == NivelRiesgoHallazgo.MEDIO.value),
        "bajos": sum(1 for item in hallazgos if item.nivel_riesgo == NivelRiesgoHallazgo.BAJO.value),
        "hallazgos_vencidos": hallazgos_vencidos,
        "acciones_correctivas_vencidas": acciones_vencidas,
        "pct_resueltos": _pct(sum(1 for item in hallazgos if item.estado in (EstadoHallazgo.SUBSANADO.value, EstadoHallazgo.CERRADO.value)), total),
        "pct_criticos": _pct(sum(1 for item in hallazgos if item.nivel_riesgo == NivelRiesgoHallazgo.CRITICO.value), total),
        "total_acciones": len(acciones),
        "acciones_ejecutadas": ejecutadas,
        "pct_acciones": _pct(ejecutadas, len(acciones)),
        "por_coso": _conteo(hallazgos, "componente_coso"),
        "tiempo_promedio_atencion_dias": _avg(tiempos_atencion),
        "tiempo_promedio_cierre_dias": _avg(tiempos_cierre),
        "tendencia_mensual": dict(sorted(tendencia_mensual.items())),
    }


def resumen_global_service() -> dict[str, Any]:
    return {
        "controles": kpi_controles_service(),
        "programa": kpi_programa_service(),
        "evidencias": kpi_evidencias_service(),
        "hallazgos": kpi_hallazgos_service(),
    }


__all__ = [
    "kpi_controles_service",
    "kpi_evidencias_service",
    "kpi_hallazgos_service",
    "kpi_programa_service",
    "resumen_global_service",
]

from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import Session

from fastapi_modulo.db import SessionLocal
from fastapi_modulo.modulos.control_interno.models import ControlInterno
from fastapi_modulo.modulos.control_interno.programa_models import (
    ProgramaAnual, ProgramaActividad,
)
from fastapi_modulo.modulos.control_interno.evidencia_models import Evidencia
from fastapi_modulo.modulos.control_interno.hallazgo_models import (
    Hallazgo, AccionCorrectiva,
)


def _db() -> Session:
    return SessionLocal()


def _conteo(items: List[Any], campo: str) -> Dict[str, int]:
    conteo: Dict[str, int] = {}
    for item in items:
        val = getattr(item, campo, None) or "—"
        conteo[val] = conteo.get(val, 0) + 1
    return conteo


def _pct(parte: int, total: int) -> float:
    return round(parte / total * 100, 1) if total else 0.0


# ── Controles ─────────────────────────────────────────────────────────────────

def kpi_controles() -> Dict[str, Any]:
    db = _db()
    try:
        controles = db.query(ControlInterno).all()
        total     = len(controles)
        activos   = sum(1 for c in controles if c.estado == "Activo")
        return {
            "total":           total,
            "activos":         activos,
            "inactivos":       total - activos,
            "pct_activos":     _pct(activos, total),
            "por_componente":  _conteo(controles, "componente"),
            "por_periodicidad": _conteo(controles, "periodicidad"),
        }
    finally:
        db.close()


# ── Programa anual ────────────────────────────────────────────────────────────

def kpi_programa() -> Dict[str, Any]:
    db = _db()
    try:
        programas    = db.query(ProgramaAnual).all()
        actividades  = db.query(ProgramaActividad).all()
        total_act    = len(actividades)
        completadas  = sum(1 for a in actividades if a.estado == "Completado")
        en_proceso   = sum(1 for a in actividades if a.estado == "En proceso")
        programadas  = sum(1 for a in actividades if a.estado == "Programado")
        diferidas    = sum(1 for a in actividades if a.estado == "Diferido")
        canceladas   = sum(1 for a in actividades if a.estado == "Cancelado")
        por_estado_prog = _conteo(programas, "estado")
        return {
            "total_programas":  len(programas),
            "total_actividades": total_act,
            "completadas":      completadas,
            "en_proceso":       en_proceso,
            "programadas":      programadas,
            "diferidas":        diferidas,
            "canceladas":       canceladas,
            "pct_completadas":  _pct(completadas, total_act),
            "por_estado_programa": por_estado_prog,
        }
    finally:
        db.close()


# ── Evidencias ────────────────────────────────────────────────────────────────

def kpi_evidencias() -> Dict[str, Any]:
    db = _db()
    try:
        evidencias   = db.query(Evidencia).all()
        total        = len(evidencias)
        cumple       = sum(1 for e in evidencias if e.resultado_evaluacion == "Cumple")
        parcial      = sum(1 for e in evidencias if e.resultado_evaluacion == "Cumple parcialmente")
        no_cumple    = sum(1 for e in evidencias if e.resultado_evaluacion == "No cumple")
        por_evaluar  = sum(1 for e in evidencias if e.resultado_evaluacion == "Por evaluar")
        evaluadas    = cumple + parcial + no_cumple
        return {
            "total":        total,
            "cumple":       cumple,
            "parcial":      parcial,
            "no_cumple":    no_cumple,
            "por_evaluar":  por_evaluar,
            "pct_cumple":   _pct(cumple,    evaluadas),
            "pct_parcial":  _pct(parcial,   evaluadas),
            "pct_no_cumple": _pct(no_cumple, evaluadas),
            "por_tipo":     _conteo(evidencias, "tipo"),
        }
    finally:
        db.close()


# ── Hallazgos ─────────────────────────────────────────────────────────────────

def kpi_hallazgos() -> Dict[str, Any]:
    db = _db()
    try:
        hallazgos = db.query(Hallazgo).all()
        acciones  = db.query(AccionCorrectiva).all()
        total_h   = len(hallazgos)
        abiertos  = sum(1 for h in hallazgos if h.estado == "Abierto")
        atencion  = sum(1 for h in hallazgos if h.estado == "En atención")
        subsanados = sum(1 for h in hallazgos if h.estado == "Subsanado")
        cerrados  = sum(1 for h in hallazgos if h.estado == "Cerrado")
        criticos  = sum(1 for h in hallazgos if h.nivel_riesgo == "Crítico")
        altos     = sum(1 for h in hallazgos if h.nivel_riesgo == "Alto")
        medios    = sum(1 for h in hallazgos if h.nivel_riesgo == "Medio")
        bajos     = sum(1 for h in hallazgos if h.nivel_riesgo == "Bajo")

        total_ac   = len(acciones)
        ac_ejecutadas = sum(1 for a in acciones
                            if a.estado in ("Ejecutada", "Verificada"))
        return {
            "total":           total_h,
            "abiertos":        abiertos,
            "en_atencion":     atencion,
            "subsanados":      subsanados,
            "cerrados":        cerrados,
            "criticos":        criticos,
            "altos":           altos,
            "medios":          medios,
            "bajos":           bajos,
            "pct_resueltos":   _pct(subsanados + cerrados, total_h),
            "pct_criticos":    _pct(criticos, total_h),
            "total_acciones":  total_ac,
            "acciones_ejecutadas": ac_ejecutadas,
            "pct_acciones":    _pct(ac_ejecutadas, total_ac),
            "por_coso":        _conteo(hallazgos, "componente_coso"),
        }
    finally:
        db.close()


# ── Resumen global ────────────────────────────────────────────────────────────

def resumen_global() -> Dict[str, Any]:
    return {
        "controles":  kpi_controles(),
        "programa":   kpi_programa(),
        "evidencias": kpi_evidencias(),
        "hallazgos":  kpi_hallazgos(),
    }

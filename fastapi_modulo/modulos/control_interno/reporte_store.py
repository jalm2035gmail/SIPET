from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, joinedload

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


def _fe(d: Any) -> str:
    """Format date/datetime as ISO string or empty."""
    if not d:
        return ""
    if isinstance(d, date):
        return d.isoformat()
    return str(d)[:10]


# ── Controles ─────────────────────────────────────────────────────────────────

def _filas_controles(
    componente: Optional[str] = None,
    estado:     Optional[str] = None,
    q:          Optional[str] = None,
) -> List[Dict[str, Any]]:
    db = _db()
    try:
        query = db.query(ControlInterno)
        if componente:
            query = query.filter(ControlInterno.componente == componente)
        if estado:
            query = query.filter(ControlInterno.estado == estado)
        rows = query.order_by(ControlInterno.componente, ControlInterno.codigo).all()
        result = []
        for c in rows:
            if q and q.lower() not in (
                (c.codigo or "") + (c.nombre or "") + (c.area or "")
            ).lower():
                continue
            result.append({
                "ID": c.id,
                "Código": c.codigo,
                "Nombre": c.nombre,
                "Componente COSO": c.componente,
                "Área": c.area,
                "Tipo de riesgo": c.tipo_riesgo or "",
                "Periodicidad": c.periodicidad,
                "Estado": c.estado,
                "Normativa": c.normativa or "",
                "Creado": _fe(c.creado_en),
            })
        return result
    finally:
        db.close()


# ── Programa anual ────────────────────────────────────────────────────────────

def _filas_actividades(
    anio:       Optional[int]  = None,
    estado:     Optional[str]  = None,
    control_id: Optional[int]  = None,
) -> List[Dict[str, Any]]:
    db = _db()
    try:
        query = (db.query(ProgramaActividad)
                   .options(joinedload(ProgramaActividad.programa),
                            joinedload(ProgramaActividad.control)))
        if estado:
            query = query.filter(ProgramaActividad.estado == estado)
        if control_id:
            query = query.filter(ProgramaActividad.control_id == control_id)
        actividades = query.all()
        result = []
        for a in actividades:
            prog_anio = a.programa.anio if a.programa else None
            if anio and prog_anio != anio:
                continue
            result.append({
                "ID": a.id,
                "Programa": a.programa.nombre if a.programa else "",
                "Año": prog_anio or "",
                "Control vinculado": a.control.codigo if a.control else "",
                "Descripción": a.descripcion or "",
                "Responsable": a.responsable or "",
                "F. inicio programada": _fe(a.fecha_inicio_programada),
                "F. fin programada": _fe(a.fecha_fin_programada),
                "F. inicio real": _fe(a.fecha_inicio_real),
                "F. fin real": _fe(a.fecha_fin_real),
                "Estado": a.estado,
                "Observaciones": a.observaciones or "",
            })
        return result
    finally:
        db.close()


# ── Evidencias ────────────────────────────────────────────────────────────────

def _filas_evidencias(
    resultado:  Optional[str] = None,
    control_id: Optional[int] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> List[Dict[str, Any]]:
    db = _db()
    try:
        query = (db.query(Evidencia)
                   .options(joinedload(Evidencia.control)))
        if resultado:
            query = query.filter(Evidencia.resultado_evaluacion == resultado)
        if control_id:
            query = query.filter(Evidencia.control_id == control_id)
        if fecha_desde:
            query = query.filter(Evidencia.fecha_evidencia >= date.fromisoformat(fecha_desde))
        if fecha_hasta:
            query = query.filter(Evidencia.fecha_evidencia <= date.fromisoformat(fecha_hasta))
        evidencias = query.order_by(Evidencia.fecha_evidencia.desc().nullslast()).all()
        return [
            {
                "ID": e.id,
                "Título": e.titulo,
                "Tipo": e.tipo,
                "Fecha": _fe(e.fecha_evidencia),
                "Control vinculado": e.control.codigo if e.control else "",
                "Resultado evaluación": e.resultado_evaluacion,
                "Observaciones": e.observaciones or "",
                "Archivo": e.archivo_nombre or "",
                "Creado": _fe(e.creado_en),
            }
            for e in evidencias
        ]
    finally:
        db.close()


# ── Hallazgos ─────────────────────────────────────────────────────────────────

def _filas_hallazgos(
    nivel_riesgo:    Optional[str] = None,
    estado:          Optional[str] = None,
    componente_coso: Optional[str] = None,
    control_id:      Optional[int] = None,
    fecha_desde:     Optional[str] = None,
    fecha_hasta:     Optional[str] = None,
) -> List[Dict[str, Any]]:
    db = _db()
    try:
        query = (db.query(Hallazgo)
                   .options(joinedload(Hallazgo.control),
                            joinedload(Hallazgo.acciones)))
        if nivel_riesgo:
            query = query.filter(Hallazgo.nivel_riesgo == nivel_riesgo)
        if estado:
            query = query.filter(Hallazgo.estado == estado)
        if componente_coso:
            query = query.filter(Hallazgo.componente_coso == componente_coso)
        if control_id:
            query = query.filter(Hallazgo.control_id == control_id)
        if fecha_desde:
            query = query.filter(Hallazgo.fecha_deteccion >= date.fromisoformat(fecha_desde))
        if fecha_hasta:
            query = query.filter(Hallazgo.fecha_deteccion <= date.fromisoformat(fecha_hasta))
        hallazgos = query.order_by(Hallazgo.fecha_deteccion.desc().nullslast()).all()
        return [
            {
                "ID": h.id,
                "Código": h.codigo or "",
                "Título": h.titulo,
                "Componente COSO": h.componente_coso or "",
                "Control vinculado": h.control.codigo if h.control else "",
                "Nivel de riesgo": h.nivel_riesgo,
                "Estado": h.estado,
                "Causa": h.causa or "",
                "Efecto": h.efecto or "",
                "Fecha detección": _fe(h.fecha_deteccion),
                "Fecha límite": _fe(h.fecha_limite),
                "Responsable": h.responsable or "",
                "# Acciones": len(h.acciones) if h.acciones else 0,
                "Creado": _fe(h.creado_en),
            }
            for h in hallazgos
        ]
    finally:
        db.close()


def _filas_acciones(
    estado:          Optional[str] = None,
    fecha_desde:     Optional[str] = None,
    fecha_hasta:     Optional[str] = None,
) -> List[Dict[str, Any]]:
    db = _db()
    try:
        query = db.query(AccionCorrectiva).options(joinedload(AccionCorrectiva.hallazgo))
        if estado:
            query = query.filter(AccionCorrectiva.estado == estado)
        if fecha_desde:
            query = query.filter(AccionCorrectiva.fecha_compromiso >= date.fromisoformat(fecha_desde))
        if fecha_hasta:
            query = query.filter(AccionCorrectiva.fecha_compromiso <= date.fromisoformat(fecha_hasta))
        acciones = query.order_by(AccionCorrectiva.fecha_compromiso).all()
        return [
            {
                "ID": a.id,
                "Hallazgo código": a.hallazgo.codigo if a.hallazgo else "",
                "Hallazgo título": a.hallazgo.titulo if a.hallazgo else "",
                "Descripción acción": a.descripcion,
                "Responsable": a.responsable or "",
                "Estado": a.estado,
                "F. compromiso": _fe(a.fecha_compromiso),
                "F. ejecución": _fe(a.fecha_ejecucion),
                "Evidencia seguimiento": a.evidencia_seguimiento or "",
            }
            for a in acciones
        ]
    finally:
        db.close()


# ── Entrada pública ───────────────────────────────────────────────────────────

def datos_reporte(
    tipo:            str            = "completo",
    anio:            Optional[int]  = None,
    componente_coso: Optional[str]  = None,
    nivel_riesgo:    Optional[str]  = None,
    estado_hallazgo: Optional[str]  = None,
    estado_actividad: Optional[str] = None,
    estado_control:  Optional[str]  = None,
    resultado_ev:    Optional[str]  = None,
    control_id:      Optional[int]  = None,
    fecha_desde:     Optional[str]  = None,
    fecha_hasta:     Optional[str]  = None,
    q:               Optional[str]  = None,
) -> Dict[str, Any]:
    """Devuelve todas las secciones del reporte según el tipo solicitado."""
    incluir = {
        "controles":  tipo in ("controles",  "completo"),
        "programa":   tipo in ("programa",   "completo"),
        "evidencias": tipo in ("evidencias", "completo"),
        "hallazgos":  tipo in ("hallazgos",  "completo"),
        "acciones":   tipo in ("hallazgos",  "completo"),
    }
    resultado: Dict[str, Any] = {"tipo": tipo}

    if incluir["controles"]:
        resultado["controles"] = _filas_controles(
            componente=componente_coso, estado=estado_control, q=q
        )
    if incluir["programa"]:
        resultado["actividades"] = _filas_actividades(
            anio=anio, estado=estado_actividad, control_id=control_id
        )
    if incluir["evidencias"]:
        resultado["evidencias"] = _filas_evidencias(
            resultado=resultado_ev, control_id=control_id,
            fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        )
    if incluir["hallazgos"]:
        resultado["hallazgos"] = _filas_hallazgos(
            nivel_riesgo=nivel_riesgo, estado=estado_hallazgo,
            componente_coso=componente_coso, control_id=control_id,
            fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        )
    if incluir["acciones"]:
        resultado["acciones"] = _filas_acciones(
            fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        )
    return resultado

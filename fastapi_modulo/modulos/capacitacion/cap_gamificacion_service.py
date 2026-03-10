"""Servicio — Gamificación (puntos, insignias, ranking, niveles)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from fastapi_modulo.db import SessionLocal
from fastapi_modulo.modulos.capacitacion.cap_db_models import (
    CapColaboradorInsignia,
    CapInsignia,
    CapInscripcion,
    CapProgresoLeccion,
    CapCertificado,
    CapIntentoEvaluacion,
    CapPuntosLog,
)


def _db():
    return SessionLocal()


# ── Niveles ─────────────────────────────────────────────────────────────────────

_NIVELES = [
    (0,    "🌱", "Aprendiz"),
    (100,  "📖", "Practicante"),
    (300,  "⚡", "Avanzado"),
    (700,  "🎓", "Experto"),
    (1500, "🏆", "Maestro"),
]


def _get_nivel(puntos: int) -> Dict[str, Any]:
    nivel_actual = _NIVELES[0]
    for umbral, emoji, nombre in _NIVELES:
        if puntos >= umbral:
            nivel_actual = (umbral, emoji, nombre)
    idx = next(i for i, n in enumerate(_NIVELES) if n[0] == nivel_actual[0])
    if idx < len(_NIVELES) - 1:
        siguiente = _NIVELES[idx + 1]
        pts_rango = siguiente[0] - nivel_actual[0]
        pts_en_rango = puntos - nivel_actual[0]
        pct = round(pts_en_rango / pts_rango * 100)
        pts_siguiente = siguiente[0]
        nombre_siguiente = siguiente[2]
    else:
        pct = 100
        pts_siguiente = None
        nombre_siguiente = None
    return {
        "nivel": nivel_actual[2],
        "emoji": nivel_actual[1],
        "pts_siguiente": pts_siguiente,
        "nombre_siguiente": nombre_siguiente,
        "pct_nivel": pct,
    }


# ── Insignias predeterminadas ───────────────────────────────────────────────────

_INSIGNIAS_DEFAULT = [
    {
        "nombre": "Primer paso",
        "descripcion": "Completa tu primera lección.",
        "icono_emoji": "🎯",
        "condicion_tipo": "lecciones_completadas",
        "condicion_valor": 1,
        "color": "#6366f1",
        "orden": 1,
    },
    {
        "nombre": "Estudioso",
        "descripcion": "Completa 10 lecciones.",
        "icono_emoji": "📚",
        "condicion_tipo": "lecciones_completadas",
        "condicion_valor": 10,
        "color": "#2563eb",
        "orden": 2,
    },
    {
        "nombre": "Voraz del conocimiento",
        "descripcion": "Completa 25 lecciones.",
        "icono_emoji": "🧠",
        "condicion_tipo": "lecciones_completadas",
        "condicion_valor": 25,
        "color": "#9333ea",
        "orden": 3,
    },
    {
        "nombre": "Primer curso",
        "descripcion": "Completa tu primer curso.",
        "icono_emoji": "✅",
        "condicion_tipo": "cursos_completados",
        "condicion_valor": 1,
        "color": "#16a34a",
        "orden": 4,
    },
    {
        "nombre": "Constante",
        "descripcion": "Completa 3 cursos.",
        "icono_emoji": "🔥",
        "condicion_tipo": "cursos_completados",
        "condicion_valor": 3,
        "color": "#ea580c",
        "orden": 5,
    },
    {
        "nombre": "Maestro del aprendizaje",
        "descripcion": "Completa 5 cursos.",
        "icono_emoji": "🏆",
        "condicion_tipo": "cursos_completados",
        "condicion_valor": 5,
        "color": "#b45309",
        "orden": 6,
    },
    {
        "nombre": "Graduado",
        "descripcion": "Obtén tu primer certificado.",
        "icono_emoji": "🎓",
        "condicion_tipo": "certificados_obtenidos",
        "condicion_valor": 1,
        "color": "#0891b2",
        "orden": 7,
    },
    {
        "nombre": "Coleccionista",
        "descripcion": "Obtén 3 certificados.",
        "icono_emoji": "💎",
        "condicion_tipo": "certificados_obtenidos",
        "condicion_valor": 3,
        "color": "#0e7490",
        "orden": 8,
    },
    {
        "nombre": "Perfeccionista",
        "descripcion": "Obtén 100% en una evaluación.",
        "icono_emoji": "⭐",
        "condicion_tipo": "puntaje_perfecto",
        "condicion_valor": 1,
        "color": "#ca8a04",
        "orden": 9,
    },
]


def _seed_insignias(db) -> None:
    """Inserta las insignias predeterminadas si la tabla está vacía."""
    if db.query(CapInsignia).count() > 0:
        return
    for data in _INSIGNIAS_DEFAULT:
        db.add(CapInsignia(**data))
    db.commit()


# ── Puntos ───────────────────────────────────────────────────────────────────────

def otorgar_puntos(
    colaborador_key: str,
    motivo: str,
    puntos: int,
    referencia_tipo: Optional[str] = None,
    referencia_id: Optional[int] = None,
) -> int:
    """
    Registra los puntos en el log (idempotente: ignora duplicados vía UNIQUE).
    Retorna el total actual de puntos del colaborador.
    """
    db = _db()
    try:
        entry = CapPuntosLog(
            colaborador_key=colaborador_key,
            puntos=puntos,
            motivo=motivo,
            referencia_tipo=referencia_tipo,
            referencia_id=referencia_id,
            fecha=datetime.utcnow(),
        )
        db.add(entry)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()  # duplicate — already awarded
        return get_puntos_totales(colaborador_key)
    finally:
        db.close()


def get_puntos_totales(colaborador_key: str) -> int:
    db = _db()
    try:
        from sqlalchemy import func
        total = db.query(func.sum(CapPuntosLog.puntos)).filter(
            CapPuntosLog.colaborador_key == colaborador_key
        ).scalar()
        return int(total or 0)
    finally:
        db.close()


# ── Insignias ────────────────────────────────────────────────────────────────────

def _contar_condicion(db, colaborador_key: str, condicion_tipo: str) -> int:
    """Cuenta cuántas veces se cumple un tipo de condición para el colaborador."""
    if condicion_tipo == "lecciones_completadas":
        return (
            db.query(CapProgresoLeccion)
            .join(CapInscripcion, CapProgresoLeccion.inscripcion_id == CapInscripcion.id)
            .filter(
                CapInscripcion.colaborador_key == colaborador_key,
                CapProgresoLeccion.completada == True,
            )
            .count()
        )
    elif condicion_tipo == "cursos_completados":
        return (
            db.query(CapInscripcion)
            .filter(
                CapInscripcion.colaborador_key == colaborador_key,
                CapInscripcion.estado == "completado",
            )
            .count()
        )
    elif condicion_tipo == "certificados_obtenidos":
        return (
            db.query(CapCertificado)
            .join(CapInscripcion, CapCertificado.inscripcion_id == CapInscripcion.id)
            .filter(CapInscripcion.colaborador_key == colaborador_key)
            .count()
        )
    elif condicion_tipo == "puntaje_perfecto":
        return (
            db.query(CapIntentoEvaluacion)
            .join(CapInscripcion, CapIntentoEvaluacion.inscripcion_id == CapInscripcion.id)
            .filter(
                CapInscripcion.colaborador_key == colaborador_key,
                CapIntentoEvaluacion.puntaje >= 100.0,
                CapIntentoEvaluacion.aprobado == True,
            )
            .count()
        )
    return 0


def check_y_otorgar_insignias(colaborador_key: str) -> List[Dict[str, Any]]:
    """Evalúa todas las insignias y otorga las que aún no tiene el colaborador.
    Retorna lista de insignias recién ganadas."""
    db = _db()
    try:
        _seed_insignias(db)

        todas = db.query(CapInsignia).order_by(CapInsignia.orden).all()
        ya_tiene_ids = {
            ci.insignia_id
            for ci in db.query(CapColaboradorInsignia)
            .filter(CapColaboradorInsignia.colaborador_key == colaborador_key)
            .all()
        }

        nuevas = []
        for insignia in todas:
            if insignia.id in ya_tiene_ids:
                continue
            valor_actual = _contar_condicion(db, colaborador_key, insignia.condicion_tipo)
            if valor_actual >= insignia.condicion_valor:
                ci = CapColaboradorInsignia(
                    colaborador_key=colaborador_key,
                    insignia_id=insignia.id,
                    fecha_obtencion=datetime.utcnow(),
                )
                db.add(ci)
                nuevas.append({
                    "id": insignia.id,
                    "nombre": insignia.nombre,
                    "descripcion": insignia.descripcion,
                    "icono_emoji": insignia.icono_emoji,
                    "color": insignia.color,
                })
        if nuevas:
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
        return nuevas
    finally:
        db.close()


def get_insignias_disponibles() -> List[Dict[str, Any]]:
    db = _db()
    try:
        _seed_insignias(db)
        objs = db.query(CapInsignia).order_by(CapInsignia.orden).all()
        return [
            {
                "id": o.id,
                "nombre": o.nombre,
                "descripcion": o.descripcion,
                "icono_emoji": o.icono_emoji,
                "condicion_tipo": o.condicion_tipo,
                "condicion_valor": o.condicion_valor,
                "color": o.color,
                "orden": o.orden,
            }
            for o in objs
        ]
    finally:
        db.close()


def get_mis_insignias(colaborador_key: str) -> List[Dict[str, Any]]:
    db = _db()
    try:
        _seed_insignias(db)
        objs = (
            db.query(CapColaboradorInsignia)
            .filter(CapColaboradorInsignia.colaborador_key == colaborador_key)
            .all()
        )
        result = []
        for ci in objs:
            ins = ci.insignia
            result.append({
                "id": ins.id,
                "nombre": ins.nombre,
                "descripcion": ins.descripcion,
                "icono_emoji": ins.icono_emoji,
                "color": ins.color,
                "orden": ins.orden,
                "fecha_obtencion": ci.fecha_obtencion.isoformat() if ci.fecha_obtencion else None,
            })
        return sorted(result, key=lambda x: x["orden"])
    finally:
        db.close()


# ── Perfil completo ──────────────────────────────────────────────────────────────

def get_perfil_gamificacion(colaborador_key: str) -> Dict[str, Any]:
    puntos = get_puntos_totales(colaborador_key)
    nivel_info = _get_nivel(puntos)
    insignias = get_mis_insignias(colaborador_key)

    db = _db()
    try:
        # Historial reciente (últimas 10 entradas)
        historial = (
            db.query(CapPuntosLog)
            .filter(CapPuntosLog.colaborador_key == colaborador_key, CapPuntosLog.puntos > 0)
            .order_by(CapPuntosLog.fecha.desc())
            .limit(10)
            .all()
        )
        actividad = [
            {
                "puntos": h.puntos,
                "motivo": h.motivo,
                "fecha": h.fecha.isoformat() if h.fecha else None,
            }
            for h in historial
        ]
    finally:
        db.close()

    return {
        "colaborador_key": colaborador_key,
        "puntos_totales": puntos,
        **nivel_info,
        "insignias": insignias,
        "actividad_reciente": actividad,
    }


# ── Ranking ──────────────────────────────────────────────────────────────────────

def get_ranking(limit: int = 10) -> List[Dict[str, Any]]:
    db = _db()
    try:
        from sqlalchemy import func
        rows = (
            db.query(
                CapPuntosLog.colaborador_key,
                func.sum(CapPuntosLog.puntos).label("total_puntos"),
            )
            .group_by(CapPuntosLog.colaborador_key)
            .order_by(func.sum(CapPuntosLog.puntos).desc())
            .limit(limit)
            .all()
        )
        result = []
        for i, row in enumerate(rows):
            ck = row[0]
            pts = int(row[1] or 0)
            nivel_info = _get_nivel(pts)
            num_insignias = db.query(CapColaboradorInsignia).filter(
                CapColaboradorInsignia.colaborador_key == ck
            ).count()
            # Nombre amigable: buscar en inscripciones
            nombre = (
                db.query(CapInscripcion.colaborador_nombre)
                .filter(
                    CapInscripcion.colaborador_key == ck,
                    CapInscripcion.colaborador_nombre != None,
                )
                .first()
            )
            result.append({
                "posicion": i + 1,
                "colaborador_key": ck,
                "colaborador_nombre": nombre[0] if nombre else ck,
                "puntos": pts,
                "nivel": nivel_info["nivel"],
                "emoji_nivel": nivel_info["emoji"],
                "num_insignias": num_insignias,
            })
        return result
    finally:
        db.close()

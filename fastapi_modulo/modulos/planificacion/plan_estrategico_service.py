from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime
from html import escape
from io import BytesIO, StringIO
from typing import Any, Dict, List

import pandas as pd
from fastapi import Body, File, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError

_CORE_BOUND = False


def _bind_core_symbols() -> None:
    global _CORE_BOUND
    if _CORE_BOUND:
        return
    from fastapi_modulo import main as core

    names = [
        "SessionLocal",
        "StrategicAxisConfig",
        "StrategicObjectiveConfig",
        "POAActivity",
        "POASubactivity",
        "Usuario",
        "_date_to_iso",
        "_activity_status",
        "_parse_date_field",
        "_validate_date_range",
        "_validate_child_date_range",
    ]
    for name in names:
        globals()[name] = getattr(core, name)
    _CORE_BOUND = True


MAX_SUBTASK_DEPTH = 4
VALID_ACTIVITY_PERIODICITIES = {
    "diaria",
    "semanal",
    "quincenal",
    "mensual",
    "bimensual",
    "cada_xx_dias",
}


def _serialize_strategic_objective(obj) -> Dict[str, Any]:
    _bind_core_symbols()
    return {
        "id": obj.id,
        "eje_id": obj.eje_id,
        "codigo": obj.codigo or "",
        "nombre": obj.nombre or "",
        "hito": obj.hito or "",
        "lider": obj.lider or "",
        "fecha_inicial": _date_to_iso(obj.fecha_inicial),
        "fecha_final": _date_to_iso(obj.fecha_final),
        "descripcion": obj.descripcion or "",
        "orden": obj.orden or 0,
    }


def _serialize_strategic_axis(axis) -> Dict[str, Any]:
    _bind_core_symbols()
    objetivos = sorted(axis.objetivos or [], key=lambda item: (item.orden or 0, item.id or 0))
    return {
        "id": axis.id,
        "nombre": axis.nombre or "",
        "codigo": axis.codigo or "",
        "lider_departamento": axis.lider_departamento or "",
        "responsabilidad_directa": axis.responsabilidad_directa or "",
        "fecha_inicial": _date_to_iso(axis.fecha_inicial),
        "fecha_final": _date_to_iso(axis.fecha_final),
        "descripcion": axis.descripcion or "",
        "orden": axis.orden or 0,
        "objetivos_count": len(objetivos),
        "objetivos": [_serialize_strategic_objective(obj) for obj in objetivos],
    }


def _compose_axis_code(base_code: str, order_value: int) -> str:
    raw_prefix = (base_code or "").strip().lower()
    safe_prefix = "".join(ch for ch in raw_prefix if ch.isalnum()) or "m1"
    safe_order = int(order_value or 0)
    if safe_order <= 0:
        safe_order = 1
    return f"{safe_prefix}-{safe_order:02d}"


def _compose_objective_code(axis_code: str, order_value: int) -> str:
    raw_axis = (axis_code or "").strip().lower()
    axis_parts = [part for part in raw_axis.split("-") if part]
    if len(axis_parts) >= 2:
        axis_prefix = f"{axis_parts[0]}-{axis_parts[1]}"
    elif axis_parts:
        axis_prefix = f"{axis_parts[0]}-01"
    else:
        axis_prefix = "m1-01"
    safe_order = int(order_value or 0)
    if safe_order <= 0:
        safe_order = 1
    return f"{axis_prefix}-{safe_order:02d}"


def _collaborator_belongs_to_department(db, collaborator_name: str, department: str) -> bool:
    _bind_core_symbols()
    name = (collaborator_name or "").strip()
    dep = (department or "").strip()
    if not name or not dep:
        return False
    exists = (
        db.query(Usuario.id)
        .filter(Usuario.nombre == name, Usuario.departamento == dep)
        .first()
    )
    return bool(exists)


def _ensure_strategic_identity_table(db) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS strategic_identity_config (
              bloque VARCHAR(20) PRIMARY KEY,
              payload TEXT NOT NULL DEFAULT '[]',
              updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )


def _normalize_identity_lines(raw: Any, prefix: str) -> List[Dict[str, str]]:
    rows = raw if isinstance(raw, list) else []
    clean: List[Dict[str, str]] = []
    for idx, item in enumerate(rows):
        if not isinstance(item, dict):
            continue
        code_raw = str(item.get("code") or "").strip().lower()
        text_raw = str(item.get("text") or "").strip()
        safe_code = "".join(ch for ch in code_raw if ch.isalnum()) or f"{prefix}{idx + 1}"
        clean.append({"code": safe_code, "text": text_raw})
    if not clean:
        clean = [{"code": f"{prefix}1", "text": ""}]
    return clean


def _normalize_foundation_text(raw: Any) -> str:
    return str(raw or "").strip()


def _ensure_axis_kpi_table(db) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS strategic_axis_kpis (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              axis_id INTEGER NOT NULL,
              nombre VARCHAR(255) NOT NULL DEFAULT '',
              descripcion TEXT NOT NULL DEFAULT '',
              objetivo TEXT NOT NULL DEFAULT '',
              formula TEXT NOT NULL DEFAULT '',
              responsable VARCHAR(255) NOT NULL DEFAULT '',
              fuente_datos TEXT NOT NULL DEFAULT '',
              unidad VARCHAR(120) NOT NULL DEFAULT '',
              frecuencia VARCHAR(120) NOT NULL DEFAULT '',
              linea_base TEXT NOT NULL DEFAULT '',
              estandar_meta TEXT NOT NULL DEFAULT '',
              semaforo_rojo TEXT NOT NULL DEFAULT '',
              semaforo_verde TEXT NOT NULL DEFAULT '',
              categoria VARCHAR(255) NOT NULL DEFAULT '',
              perspectiva VARCHAR(255) NOT NULL DEFAULT '',
              orden INTEGER NOT NULL DEFAULT 0
            )
            """
        )
    )
    try:
        cols = db.execute(text("PRAGMA table_info(strategic_axis_kpis)")).fetchall()
        col_names = {str(col[1]).strip().lower() for col in cols if len(col) > 1}
        if "perspectiva" not in col_names:
            db.execute(
                text(
                    "ALTER TABLE strategic_axis_kpis ADD COLUMN perspectiva VARCHAR(255) NOT NULL DEFAULT ''"
                )
            )
    except Exception:
        pass


def _normalize_axis_kpi_items(raw: Any) -> List[Dict[str, str]]:
    rows = raw if isinstance(raw, list) else []
    cleaned: List[Dict[str, str]] = []
    for idx, item in enumerate(rows, start=1):
        if not isinstance(item, dict):
            continue
        nombre = str(item.get("nombre") or "").strip()
        if not nombre:
            continue
        cleaned.append(
            {
                "nombre": nombre,
                "descripcion": str(item.get("descripcion") or "").strip(),
                "objetivo": str(item.get("objetivo") or "").strip(),
                "formula": str(item.get("formula") or "").strip(),
                "responsable": str(item.get("responsable") or "").strip(),
                "fuente_datos": str(item.get("fuente_datos") or "").strip(),
                "unidad": str(item.get("unidad") or "").strip(),
                "frecuencia": str(item.get("frecuencia") or "").strip(),
                "linea_base": str(item.get("linea_base") or "").strip(),
                "estandar_meta": str(item.get("estandar_meta") or "").strip(),
                "semaforo_rojo": str(item.get("semaforo_rojo") or "").strip(),
                "semaforo_verde": str(item.get("semaforo_verde") or "").strip(),
                "categoria": str(item.get("categoria") or "").strip(),
                "perspectiva": str(item.get("perspectiva") or "").strip(),
                "orden": idx,
            }
        )
    return cleaned


def _axis_kpis_by_axis_ids(db, axis_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    result: Dict[int, List[Dict[str, Any]]] = {}
    if not axis_ids:
        return result
    _ensure_axis_kpi_table(db)
    db.commit()
    placeholders = ", ".join([f":id_{idx}" for idx, _ in enumerate(axis_ids)])
    rows = db.execute(
        text(
            f"""
            SELECT id, axis_id, nombre, descripcion, objetivo, formula, responsable, fuente_datos,
                   unidad, frecuencia, linea_base, estandar_meta, semaforo_rojo, semaforo_verde,
                   categoria, perspectiva, orden
            FROM strategic_axis_kpis
            WHERE axis_id IN ({placeholders})
            ORDER BY axis_id ASC, orden ASC, id ASC
            """
        ),
        {f"id_{idx}": int(axis_id) for idx, axis_id in enumerate(axis_ids)},
    ).fetchall()
    for row in rows:
        axis_id = int(row[1] or 0)
        if axis_id <= 0:
            continue
        result.setdefault(axis_id, []).append(
            {
                "id": int(row[0] or 0),
                "nombre": str(row[2] or ""),
                "descripcion": str(row[3] or ""),
                "objetivo": str(row[4] or ""),
                "formula": str(row[5] or ""),
                "responsable": str(row[6] or ""),
                "fuente_datos": str(row[7] or ""),
                "unidad": str(row[8] or ""),
                "frecuencia": str(row[9] or ""),
                "linea_base": str(row[10] or ""),
                "estandar_meta": str(row[11] or ""),
                "semaforo_rojo": str(row[12] or ""),
                "semaforo_verde": str(row[13] or ""),
                "categoria": str(row[14] or ""),
                "perspectiva": str(row[15] or ""),
                "orden": int(row[16] or 0),
            }
        )
    return result


def _replace_axis_kpis(db, axis_id: int, items: Any) -> None:
    clean = _normalize_axis_kpi_items(items)
    _ensure_axis_kpi_table(db)
    db.execute(text("DELETE FROM strategic_axis_kpis WHERE axis_id = :aid"), {"aid": int(axis_id)})
    for item in clean:
        db.execute(
            text(
                """
                INSERT INTO strategic_axis_kpis (
                  axis_id, nombre, descripcion, objetivo, formula, responsable, fuente_datos,
                  unidad, frecuencia, linea_base, estandar_meta, semaforo_rojo, semaforo_verde,
                  categoria, perspectiva, orden
                ) VALUES (
                  :axis_id, :nombre, :descripcion, :objetivo, :formula, :responsable, :fuente_datos,
                  :unidad, :frecuencia, :linea_base, :estandar_meta, :semaforo_rojo, :semaforo_verde,
                  :categoria, :perspectiva, :orden
                )
                """
            ),
            {
                "axis_id": int(axis_id),
                "nombre": item["nombre"],
                "descripcion": item["descripcion"],
                "objetivo": item["objetivo"],
                "formula": item["formula"],
                "responsable": item["responsable"],
                "fuente_datos": item["fuente_datos"],
                "unidad": item["unidad"],
                "frecuencia": item["frecuencia"],
                "linea_base": item["linea_base"],
                "estandar_meta": item["estandar_meta"],
                "semaforo_rojo": item["semaforo_rojo"],
                "semaforo_verde": item["semaforo_verde"],
                "categoria": item["categoria"],
                "perspectiva": item["perspectiva"],
                "orden": int(item["orden"]),
            },
        )


def _delete_axis_kpis(db, axis_id: int) -> None:
    _ensure_axis_kpi_table(db)
    db.execute(text("DELETE FROM strategic_axis_kpis WHERE axis_id = :aid"), {"aid": int(axis_id)})


def _ensure_objective_kpi_table(db) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS strategic_objective_kpis (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              objective_id INTEGER NOT NULL,
              axis_kpi_id INTEGER NOT NULL DEFAULT 0,
              nombre VARCHAR(255) NOT NULL DEFAULT '',
              proposito TEXT NOT NULL DEFAULT '',
              formula TEXT NOT NULL DEFAULT '',
              periodicidad VARCHAR(100) NOT NULL DEFAULT '',
              estandar VARCHAR(20) NOT NULL DEFAULT '',
              referencia VARCHAR(120) NOT NULL DEFAULT '',
              orden INTEGER NOT NULL DEFAULT 0
            )
            """
        )
    )
    try:
        cols = db.execute(text("PRAGMA table_info(strategic_objective_kpis)")).fetchall()
        col_names = {str(col[1]).strip().lower() for col in cols if len(col) > 1}
        if "axis_kpi_id" not in col_names:
            db.execute(
                text(
                    "ALTER TABLE strategic_objective_kpis ADD COLUMN axis_kpi_id INTEGER NOT NULL DEFAULT 0"
                )
            )
        if "referencia" not in col_names:
            db.execute(
                text(
                    "ALTER TABLE strategic_objective_kpis ADD COLUMN referencia VARCHAR(120) NOT NULL DEFAULT ''"
                )
            )
    except Exception:
        pass


def _normalize_kpi_items(raw: Any) -> List[Dict[str, str]]:
    rows = raw if isinstance(raw, list) else []
    allowed = {"mayor", "menor", "entre", "igual"}
    cleaned: List[Dict[str, str]] = []
    seen_axis_ids = set()
    for idx, item in enumerate(rows, start=1):
        if not isinstance(item, dict):
            continue
        nombre = str(item.get("nombre") or "").strip()
        axis_kpi_id = int(item.get("axis_kpi_id") or 0)
        if not nombre:
            continue
        if axis_kpi_id > 0 and axis_kpi_id in seen_axis_ids:
            continue
        estandar = str(item.get("estandar") or "").strip().lower()
        if estandar not in allowed:
            estandar = ""
        if axis_kpi_id > 0:
            seen_axis_ids.add(axis_kpi_id)
        cleaned.append(
            {
                "axis_kpi_id": axis_kpi_id,
                "nombre": nombre,
                "proposito": str(item.get("proposito") or "").strip(),
                "formula": str(item.get("formula") or "").strip(),
                "periodicidad": str(item.get("periodicidad") or "").strip(),
                "estandar": estandar,
                "referencia": str(item.get("referencia") or "").strip(),
                "orden": idx,
            }
        )
    return cleaned


def _kpis_by_objective_ids(db, objective_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    result: Dict[int, List[Dict[str, Any]]] = {}
    if not objective_ids:
        return result
    _ensure_objective_kpi_table(db)
    db.commit()
    placeholders = ", ".join([f":id_{idx}" for idx, _ in enumerate(objective_ids)])
    rows = db.execute(
        text(
            f"""
            SELECT id, objective_id, axis_kpi_id, nombre, proposito, formula, periodicidad, estandar, referencia, orden
            FROM strategic_objective_kpis
            WHERE objective_id IN ({placeholders})
            ORDER BY objective_id ASC, orden ASC, id ASC
            """
        ),
        {f"id_{idx}": int(obj_id) for idx, obj_id in enumerate(objective_ids)},
    ).fetchall()
    for row in rows:
        objective_id = int(row[1] or 0)
        if objective_id <= 0:
            continue
        result.setdefault(objective_id, []).append(
            {
                "id": int(row[0] or 0),
                "axis_kpi_id": int(row[2] or 0),
                "nombre": str(row[3] or ""),
                "proposito": str(row[4] or ""),
                "formula": str(row[5] or ""),
                "periodicidad": str(row[6] or ""),
                "estandar": str(row[7] or ""),
                "referencia": str(row[8] or ""),
                "orden": int(row[9] or 0),
            }
        )
    return result


def _replace_objective_kpis(db, objective_id: int, items: Any) -> None:
    clean = _normalize_kpi_items(items)
    _ensure_objective_kpi_table(db)
    db.execute(text("DELETE FROM strategic_objective_kpis WHERE objective_id = :oid"), {"oid": int(objective_id)})
    for item in clean:
        db.execute(
            text(
                """
                INSERT INTO strategic_objective_kpis (
                  objective_id, axis_kpi_id, nombre, proposito, formula, periodicidad, estandar, referencia, orden
                ) VALUES (
                  :objective_id, :axis_kpi_id, :nombre, :proposito, :formula, :periodicidad, :estandar, :referencia, :orden
                )
                """
            ),
            {
                "objective_id": int(objective_id),
                "axis_kpi_id": int(item["axis_kpi_id"]),
                "nombre": item["nombre"],
                "proposito": item["proposito"],
                "formula": item["formula"],
                "periodicidad": item["periodicidad"],
                "estandar": item["estandar"],
                "referencia": item["referencia"],
                "orden": int(item["orden"]),
            },
        )


def _delete_objective_kpis(db, objective_id: int) -> None:
    _ensure_objective_kpi_table(db)
    db.execute(text("DELETE FROM strategic_objective_kpis WHERE objective_id = :oid"), {"oid": int(objective_id)})


def _ensure_objective_milestone_table(db) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS strategic_objective_milestones (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              objective_id INTEGER NOT NULL,
              nombre VARCHAR(255) NOT NULL DEFAULT '',
              logrado INTEGER NOT NULL DEFAULT 0,
              fecha_realizacion DATE,
              orden INTEGER NOT NULL DEFAULT 0
            )
            """
        )
    )
    try:
        cols = db.execute(text("PRAGMA table_info(strategic_objective_milestones)")).fetchall()
        col_names = {str(col[1]).strip().lower() for col in cols if len(col) > 1}
        if "logrado" not in col_names:
            db.execute(text("ALTER TABLE strategic_objective_milestones ADD COLUMN logrado INTEGER NOT NULL DEFAULT 0"))
        if "fecha_realizacion" not in col_names:
            db.execute(text("ALTER TABLE strategic_objective_milestones ADD COLUMN fecha_realizacion DATE"))
    except Exception:
        pass


def _normalize_milestone_items(raw: Any) -> List[Dict[str, Any]]:
    rows = raw if isinstance(raw, list) else []
    cleaned: List[Dict[str, Any]] = []
    for idx, item in enumerate(rows, start=1):
        if isinstance(item, dict):
            nombre = str(item.get("nombre") or item.get("text") or "").strip()
            logrado = bool(item.get("logrado"))
            fecha_realizacion = str(item.get("fecha_realizacion") or "").strip()
        else:
            nombre = str(item or "").strip()
            logrado = False
            fecha_realizacion = ""
        if not nombre:
            continue
        cleaned.append({"nombre": nombre, "logrado": logrado, "fecha_realizacion": fecha_realizacion, "orden": idx})
    return cleaned


def _milestones_by_objective_ids(db, objective_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    result: Dict[int, List[Dict[str, Any]]] = {}
    if not objective_ids:
        return result
    _ensure_objective_milestone_table(db)
    db.commit()
    placeholders = ", ".join([f":id_{idx}" for idx, _ in enumerate(objective_ids)])
    rows = db.execute(
        text(
            f"""
            SELECT id, objective_id, nombre, logrado, fecha_realizacion, orden
            FROM strategic_objective_milestones
            WHERE objective_id IN ({placeholders})
            ORDER BY objective_id ASC, orden ASC, id ASC
            """
        ),
        {f"id_{idx}": int(obj_id) for idx, obj_id in enumerate(objective_ids)},
    ).fetchall()
    for row in rows:
        objective_id = int(row[1] or 0)
        if objective_id <= 0:
            continue
        result.setdefault(objective_id, []).append(
            {
                "id": int(row[0] or 0),
                "nombre": str(row[2] or ""),
                "logrado": bool(row[3]),
                "fecha_realizacion": str(row[4] or ""),
                "orden": int(row[5] or 0),
            }
        )
    return result


def _replace_objective_milestones(db, objective_id: int, items: Any) -> List[Dict[str, Any]]:
    clean = _normalize_milestone_items(items)
    _ensure_objective_milestone_table(db)
    db.execute(text("DELETE FROM strategic_objective_milestones WHERE objective_id = :oid"), {"oid": int(objective_id)})
    for item in clean:
        db.execute(
            text(
                """
                INSERT INTO strategic_objective_milestones (objective_id, nombre, logrado, fecha_realizacion, orden)
                VALUES (:objective_id, :nombre, :logrado, :fecha_realizacion, :orden)
                """
            ),
            {
                "objective_id": int(objective_id),
                "nombre": item["nombre"],
                "logrado": 1 if item.get("logrado") else 0,
                "fecha_realizacion": item.get("fecha_realizacion") or None,
                "orden": int(item["orden"]),
            },
        )
    return clean


def _delete_objective_milestones(db, objective_id: int) -> None:
    _ensure_objective_milestone_table(db)
    db.execute(text("DELETE FROM strategic_objective_milestones WHERE objective_id = :oid"), {"oid": int(objective_id)})


def _ensure_poa_subactivity_recurrence_columns(db) -> None:
    try:
        cols = db.execute(text("PRAGMA table_info(poa_subactivities)")).fetchall()
        col_names = {str(col[1]).strip().lower() for col in cols if len(col) > 1}
        if "recurrente" not in col_names:
            db.execute(text("ALTER TABLE poa_subactivities ADD COLUMN recurrente INTEGER NOT NULL DEFAULT 0"))
        if "periodicidad" not in col_names:
            db.execute(text("ALTER TABLE poa_subactivities ADD COLUMN periodicidad VARCHAR(50) NOT NULL DEFAULT ''"))
        if "cada_xx_dias" not in col_names:
            db.execute(text("ALTER TABLE poa_subactivities ADD COLUMN cada_xx_dias INTEGER"))
        db.commit()
    except Exception:
        db.rollback()


STRATEGIC_POA_CSV_HEADERS = [
    "tipo_registro", "axis_codigo", "axis_nombre", "axis_lider_departamento", "axis_responsabilidad_directa",
    "axis_descripcion", "axis_orden", "objective_codigo", "objective_nombre", "objective_hito", "objective_lider",
    "objective_fecha_inicial", "objective_fecha_final", "objective_descripcion", "objective_orden", "activity_codigo",
    "activity_nombre", "activity_responsable", "activity_entregable", "activity_fecha_inicial", "activity_fecha_final",
    "activity_descripcion", "activity_recurrente", "activity_periodicidad", "activity_cada_xx_dias",
    "subactivity_codigo", "subactivity_parent_codigo", "subactivity_nivel", "subactivity_nombre",
    "subactivity_responsable", "subactivity_entregable", "subactivity_fecha_inicial", "subactivity_fecha_final",
    "subactivity_descripcion",
]


def _strategic_poa_template_rows() -> List[Dict[str, str]]:
    return [
        {
            "tipo_registro": "eje",
            "axis_codigo": "m1-01",
            "axis_nombre": "Gobernanza y cumplimiento",
            "axis_lider_departamento": "Dirección",
            "axis_responsabilidad_directa": "Nombre Colaborador",
            "axis_descripcion": "Eje estratégico institucional",
            "axis_orden": "1",
        },
        {
            "tipo_registro": "objetivo",
            "axis_codigo": "m1-01",
            "objective_codigo": "m1-01-01",
            "objective_nombre": "Fortalecer controles y gestión de riesgos",
            "objective_hito": "Modelo de control aprobado",
            "objective_lider": "Nombre Colaborador",
            "objective_fecha_inicial": "2026-01-01",
            "objective_fecha_final": "2026-12-31",
            "objective_descripcion": "Objetivo estratégico anual",
            "objective_orden": "1",
        },
        {
            "tipo_registro": "actividad",
            "objective_codigo": "m1-01-01",
            "activity_codigo": "m1-01-01-aa-bb-cc-dd-ee",
            "activity_nombre": "Implementar matriz de riesgos",
            "activity_responsable": "Nombre Colaborador",
            "activity_entregable": "Matriz de riesgos validada",
            "activity_fecha_inicial": "2026-02-01",
            "activity_fecha_final": "2026-05-30",
            "activity_descripcion": "Actividad POA",
            "activity_recurrente": "no",
            "activity_periodicidad": "",
            "activity_cada_xx_dias": "",
        },
        {
            "tipo_registro": "subactividad",
            "activity_codigo": "m1-01-01-aa-bb-cc-dd-ee",
            "subactivity_codigo": "m1-01-01-aa-bb-cc-dd-ee-01",
            "subactivity_parent_codigo": "",
            "subactivity_nivel": "1",
            "subactivity_nombre": "Levantar riesgos críticos",
            "subactivity_responsable": "Nombre Colaborador",
            "subactivity_entregable": "Inventario de riesgos",
            "subactivity_fecha_inicial": "2026-02-01",
            "subactivity_fecha_final": "2026-02-28",
            "subactivity_descripcion": "Subactividad POA",
        },
    ]


def _strategic_poa_export_rows(db) -> List[Dict[str, str]]:
    _bind_core_symbols()
    rows: List[Dict[str, str]] = []
    axes = (
        db.query(StrategicAxisConfig)
        .filter(StrategicAxisConfig.is_active == True)
        .order_by(StrategicAxisConfig.orden.asc(), StrategicAxisConfig.id.asc())
        .all()
    )
    for axis in axes:
        axis_code = str(axis.codigo or "").strip()
        rows.append(
            {
                "tipo_registro": "eje",
                "axis_codigo": axis_code,
                "axis_nombre": str(axis.nombre or "").strip(),
                "axis_lider_departamento": str(axis.lider_departamento or "").strip(),
                "axis_responsabilidad_directa": str(axis.responsabilidad_directa or "").strip(),
                "axis_descripcion": str(axis.descripcion or "").strip(),
                "axis_orden": str(int(axis.orden or 0)),
            }
        )
        objectives = (
            db.query(StrategicObjectiveConfig)
            .filter(StrategicObjectiveConfig.is_active == True, StrategicObjectiveConfig.eje_id == axis.id)
            .order_by(StrategicObjectiveConfig.orden.asc(), StrategicObjectiveConfig.id.asc())
            .all()
        )
        for objective in objectives:
            objective_code = str(objective.codigo or "").strip()
            rows.append(
                {
                    "tipo_registro": "objetivo",
                    "axis_codigo": axis_code,
                    "objective_codigo": objective_code,
                    "objective_nombre": str(objective.nombre or "").strip(),
                    "objective_hito": str(objective.hito or "").strip(),
                    "objective_lider": str(objective.lider or "").strip(),
                    "objective_fecha_inicial": str(_date_to_iso(objective.fecha_inicial) or ""),
                    "objective_fecha_final": str(_date_to_iso(objective.fecha_final) or ""),
                    "objective_descripcion": str(objective.descripcion or "").strip(),
                    "objective_orden": str(int(objective.orden or 0)),
                }
            )
            activities = (
                db.query(POAActivity)
                .filter(POAActivity.objective_id == objective.id)
                .order_by(POAActivity.id.asc())
                .all()
            )
            for activity in activities:
                activity_code = str(activity.codigo or "").strip()
                rows.append(
                    {
                        "tipo_registro": "actividad",
                        "objective_codigo": objective_code,
                        "activity_codigo": activity_code,
                        "activity_nombre": str(activity.nombre or "").strip(),
                        "activity_responsable": str(activity.responsable or "").strip(),
                        "activity_entregable": str(activity.entregable or "").strip(),
                        "activity_fecha_inicial": str(_date_to_iso(activity.fecha_inicial) or ""),
                        "activity_fecha_final": str(_date_to_iso(activity.fecha_final) or ""),
                        "activity_descripcion": str(activity.descripcion or "").strip(),
                        "activity_recurrente": "si" if bool(getattr(activity, "recurrente", False)) else "no",
                        "activity_periodicidad": str(getattr(activity, "periodicidad", "") or ""),
                        "activity_cada_xx_dias": str(int(getattr(activity, "cada_xx_dias", 0) or 0) or ""),
                    }
                )
                subs = (
                    db.query(POASubactivity)
                    .filter(POASubactivity.activity_id == activity.id)
                    .order_by(POASubactivity.nivel.asc(), POASubactivity.id.asc())
                    .all()
                )
                for sub in subs:
                    parent_code = ""
                    if getattr(sub, "parent_subactivity_id", None):
                        parent = next((item for item in subs if int(item.id or 0) == int(sub.parent_subactivity_id or 0)), None)
                        parent_code = str(getattr(parent, "codigo", "") or "").strip()
                    rows.append(
                        {
                            "tipo_registro": "subactividad",
                            "activity_codigo": activity_code,
                            "subactivity_codigo": str(sub.codigo or "").strip(),
                            "subactivity_parent_codigo": parent_code,
                            "subactivity_nivel": str(int(getattr(sub, "nivel", 1) or 1)),
                            "subactivity_nombre": str(sub.nombre or "").strip(),
                            "subactivity_responsable": str(sub.responsable or "").strip(),
                            "subactivity_entregable": str(sub.entregable or "").strip(),
                            "subactivity_fecha_inicial": str(_date_to_iso(sub.fecha_inicial) or ""),
                            "subactivity_fecha_final": str(_date_to_iso(sub.fecha_final) or ""),
                            "subactivity_descripcion": str(sub.descripcion or "").strip(),
                        }
                    )
    return rows


def _csv_value(row: Dict[str, Any], key: str) -> str:
    return str((row.get(key) or "")).strip()


def _normalize_import_kind(value: str) -> str:
    raw = str(value or "").strip().lower()
    aliases = {
        "axis": "eje",
        "eje": "eje",
        "objetivo": "objetivo",
        "objective": "objetivo",
        "actividad": "actividad",
        "activity": "actividad",
        "subactividad": "subactividad",
        "subactivity": "subactividad",
    }
    return aliases.get(raw, raw)


def _parse_import_date(value: str) -> Any:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"Fecha inválida '{raw}', use formato YYYY-MM-DD") from exc


def _parse_import_int(value: str, fallback: int = 0) -> int:
    raw = str(value or "").strip()
    if not raw:
        return fallback
    return int(raw)


def _parse_import_bool(value: str) -> bool:
    raw = str(value or "").strip().lower()
    return raw in {"1", "true", "yes", "si", "sí", "on"}


def download_strategic_poa_template():
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=STRATEGIC_POA_CSV_HEADERS)
    writer.writeheader()
    for row in _strategic_poa_template_rows():
        writer.writerow({key: row.get(key, "") for key in STRATEGIC_POA_CSV_HEADERS})
    headers = {"Content-Disposition": 'attachment; filename="plantilla_plan_estrategico_poa.csv"'}
    return Response(output.getvalue(), media_type="text/csv; charset=utf-8", headers=headers)


def export_strategic_poa_xlsx():
    _bind_core_symbols()
    db = SessionLocal()
    try:
        export_rows = _strategic_poa_export_rows(db)
    finally:
        db.close()
    records = [{key: _csv_value(row, key) for key in STRATEGIC_POA_CSV_HEADERS} for row in export_rows]
    df = pd.DataFrame(records, columns=STRATEGIC_POA_CSV_HEADERS)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Plan_POA")
    output.seek(0)
    filename = f'plan_estrategico_poa_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.xlsx'
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def import_strategic_poa_csv(file: UploadFile = File(...)):
    _bind_core_symbols()
    filename = (file.filename or "").strip().lower()
    if not filename.endswith(".csv"):
        return JSONResponse({"success": False, "error": "El archivo debe ser CSV (.csv)."}, status_code=400)
    raw_bytes = await file.read()
    if not raw_bytes:
        return JSONResponse({"success": False, "error": "El archivo CSV está vacío."}, status_code=400)
    try:
        raw_text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            raw_text = raw_bytes.decode("latin-1")
        except UnicodeDecodeError:
            return JSONResponse(
                {"success": False, "error": "No se pudo leer el archivo. Usa codificación UTF-8."},
                status_code=400,
            )
    reader = csv.DictReader(StringIO(raw_text))
    if not reader.fieldnames:
        return JSONResponse({"success": False, "error": "Encabezados CSV no válidos."}, status_code=400)
    missing_headers = [h for h in ["tipo_registro"] if h not in reader.fieldnames]
    if missing_headers:
        return JSONResponse(
            {"success": False, "error": f"Faltan columnas obligatorias: {', '.join(missing_headers)}"},
            status_code=400,
        )
    db = SessionLocal()
    summary = {"created": 0, "updated": 0, "skipped": 0, "errors": []}
    try:
        _ensure_poa_subactivity_recurrence_columns(db)
        axes = db.query(StrategicAxisConfig).all()
        axis_by_code = {str((item.codigo or "")).strip().lower(): item for item in axes if (item.codigo or "").strip()}
        objectives = db.query(StrategicObjectiveConfig).all()
        objective_by_code = {str((item.codigo or "")).strip().lower(): item for item in objectives if (item.codigo or "").strip()}
        activities = db.query(POAActivity).all()
        activity_by_key: Dict[str, Any] = {}
        activity_by_code_list: Dict[str, List[Any]] = {}
        for item in activities:
            code = str((item.codigo or "")).strip().lower()
            if not code:
                continue
            activity_by_key[f"{int(item.objective_id)}::{code}"] = item
            activity_by_code_list.setdefault(code, []).append(item)
        subactivities = db.query(POASubactivity).all()
        sub_by_activity_code: Dict[str, Dict[str, Any]] = {}
        activity_code_by_id = {int(item.id): str((item.codigo or "")).strip().lower() for item in activities}
        for sub in subactivities:
            activity_code = activity_code_by_id.get(int(sub.activity_id or 0), "")
            sub_code = str((sub.codigo or "")).strip().lower()
            if activity_code and sub_code:
                sub_by_activity_code.setdefault(activity_code, {})[sub_code] = sub
        max_axis_order = db.query(func.max(StrategicAxisConfig.orden)).scalar() or 0
        objective_order_by_axis: Dict[int, int] = {}
        for item in objectives:
            axis_id = int(item.eje_id or 0)
            objective_order_by_axis[axis_id] = max(objective_order_by_axis.get(axis_id, 0), int(item.orden or 0))
        for row_index, row in enumerate(reader, start=2):
            try:
                kind = _normalize_import_kind(_csv_value(row, "tipo_registro"))
                if kind not in {"eje", "objetivo", "actividad", "subactividad"}:
                    summary["skipped"] += 1
                    summary["errors"].append(f"Fila {row_index}: tipo_registro no reconocido.")
                    continue
                if kind == "eje":
                    axis_code = _csv_value(row, "axis_codigo").lower()
                    axis_name = _csv_value(row, "axis_nombre")
                    if not axis_code:
                        raise ValueError("axis_codigo es obligatorio para tipo_registro=eje.")
                    if not axis_name and axis_code not in axis_by_code:
                        raise ValueError("axis_nombre es obligatorio al crear un eje.")
                    axis_order = _parse_import_int(_csv_value(row, "axis_orden"), 0)
                    axis = axis_by_code.get(axis_code)
                    if axis:
                        if axis_name:
                            axis.nombre = axis_name
                        axis.lider_departamento = _csv_value(row, "axis_lider_departamento")
                        axis.responsabilidad_directa = _csv_value(row, "axis_responsabilidad_directa")
                        axis.descripcion = _csv_value(row, "axis_descripcion")
                        if axis_order > 0:
                            axis.orden = axis_order
                        db.add(axis)
                        summary["updated"] += 1
                    else:
                        max_axis_order += 1
                        axis = StrategicAxisConfig(
                            nombre=axis_name or "Nuevo eje",
                            codigo=axis_code,
                            lider_departamento=_csv_value(row, "axis_lider_departamento"),
                            responsabilidad_directa=_csv_value(row, "axis_responsabilidad_directa"),
                            descripcion=_csv_value(row, "axis_descripcion"),
                            orden=axis_order if axis_order > 0 else max_axis_order,
                            is_active=True,
                        )
                        db.add(axis)
                        db.flush()
                        axis_by_code[axis_code] = axis
                        summary["created"] += 1
                    continue
                if kind == "objetivo":
                    axis_code = _csv_value(row, "axis_codigo").lower()
                    axis = axis_by_code.get(axis_code)
                    if not axis:
                        raise ValueError("axis_codigo no existe. Carga primero el eje.")
                    objective_code = _csv_value(row, "objective_codigo").lower()
                    objective_name = _csv_value(row, "objective_nombre")
                    if not objective_code:
                        raise ValueError("objective_codigo es obligatorio para tipo_registro=objetivo.")
                    objective = objective_by_code.get(objective_code)
                    start_date = _parse_import_date(_csv_value(row, "objective_fecha_inicial"))
                    end_date = _parse_import_date(_csv_value(row, "objective_fecha_final"))
                    if (start_date and not end_date) or (end_date and not start_date):
                        raise ValueError("objective_fecha_inicial y objective_fecha_final deben definirse juntas.")
                    if start_date and end_date:
                        range_error = _validate_date_range(start_date, end_date, "Objetivo")
                        if range_error:
                            raise ValueError(range_error)
                    objective_order = _parse_import_int(_csv_value(row, "objective_orden"), 0)
                    if objective:
                        if objective_name:
                            objective.nombre = objective_name
                        objective.eje_id = int(axis.id)
                        objective.hito = _csv_value(row, "objective_hito")
                        objective.lider = _csv_value(row, "objective_lider")
                        objective.fecha_inicial = start_date
                        objective.fecha_final = end_date
                        objective.descripcion = _csv_value(row, "objective_descripcion")
                        if objective_order > 0:
                            objective.orden = objective_order
                        db.add(objective)
                        summary["updated"] += 1
                    else:
                        if not objective_name:
                            raise ValueError("objective_nombre es obligatorio al crear un objetivo.")
                        next_obj_order = objective_order if objective_order > 0 else (objective_order_by_axis.get(int(axis.id), 0) + 1)
                        objective = StrategicObjectiveConfig(
                            eje_id=int(axis.id),
                            codigo=objective_code,
                            nombre=objective_name,
                            hito=_csv_value(row, "objective_hito"),
                            lider=_csv_value(row, "objective_lider"),
                            fecha_inicial=start_date,
                            fecha_final=end_date,
                            descripcion=_csv_value(row, "objective_descripcion"),
                            orden=next_obj_order,
                            is_active=True,
                        )
                        db.add(objective)
                        db.flush()
                        objective_by_code[objective_code] = objective
                        objective_order_by_axis[int(axis.id)] = max(objective_order_by_axis.get(int(axis.id), 0), int(next_obj_order))
                        summary["created"] += 1
                    continue
                if kind == "actividad":
                    objective = objective_by_code.get(_csv_value(row, "objective_codigo").lower())
                    if not objective:
                        raise ValueError("objective_codigo no existe. Carga primero el objetivo.")
                    activity_code = _csv_value(row, "activity_codigo").lower()
                    activity_name = _csv_value(row, "activity_nombre")
                    if not activity_code:
                        raise ValueError("activity_codigo es obligatorio para tipo_registro=actividad.")
                    activity_key = f"{int(objective.id)}::{activity_code}"
                    activity = activity_by_key.get(activity_key)
                    start_date = _parse_import_date(_csv_value(row, "activity_fecha_inicial"))
                    end_date = _parse_import_date(_csv_value(row, "activity_fecha_final"))
                    if (start_date and not end_date) or (end_date and not start_date):
                        raise ValueError("activity_fecha_inicial y activity_fecha_final deben definirse juntas.")
                    if start_date and end_date:
                        range_error = _validate_date_range(start_date, end_date, "Actividad")
                        if range_error:
                            raise ValueError(range_error)
                        parent_range_error = _validate_child_date_range(
                            start_date, end_date, objective.fecha_inicial, objective.fecha_final, "Actividad", "Objetivo"
                        )
                        if parent_range_error:
                            raise ValueError(parent_range_error)
                    recurrente = _parse_import_bool(_csv_value(row, "activity_recurrente"))
                    periodicidad = _csv_value(row, "activity_periodicidad").lower()
                    cada_xx_dias = _parse_import_int(_csv_value(row, "activity_cada_xx_dias"), 0)
                    if recurrente:
                        if periodicidad not in VALID_ACTIVITY_PERIODICITIES:
                            raise ValueError("activity_periodicidad no es válida para actividad recurrente.")
                        if periodicidad == "cada_xx_dias" and cada_xx_dias <= 0:
                            raise ValueError("activity_cada_xx_dias debe ser mayor a 0 para periodicidad cada_xx_dias.")
                    else:
                        periodicidad = ""
                        cada_xx_dias = 0
                    if activity:
                        if activity_name:
                            activity.nombre = activity_name
                        activity.responsable = _csv_value(row, "activity_responsable")
                        activity.entregable = _csv_value(row, "activity_entregable")
                        activity.fecha_inicial = start_date
                        activity.fecha_final = end_date
                        activity.descripcion = _csv_value(row, "activity_descripcion")
                        activity.recurrente = recurrente
                        activity.periodicidad = periodicidad
                        activity.cada_xx_dias = cada_xx_dias if periodicidad == "cada_xx_dias" else None
                        db.add(activity)
                        summary["updated"] += 1
                    else:
                        if not activity_name:
                            raise ValueError("activity_nombre es obligatorio al crear una actividad.")
                        activity = POAActivity(
                            objective_id=int(objective.id),
                            codigo=activity_code,
                            nombre=activity_name,
                            responsable=_csv_value(row, "activity_responsable"),
                            entregable=_csv_value(row, "activity_entregable"),
                            fecha_inicial=start_date,
                            fecha_final=end_date,
                            descripcion=_csv_value(row, "activity_descripcion"),
                            recurrente=recurrente,
                            periodicidad=periodicidad,
                            cada_xx_dias=cada_xx_dias if periodicidad == "cada_xx_dias" else None,
                            entrega_estado="ninguna",
                            created_by="import_csv",
                        )
                        db.add(activity)
                        db.flush()
                        activity_by_key[activity_key] = activity
                        activity_by_code_list.setdefault(activity_code, []).append(activity)
                        summary["created"] += 1
                    continue
                if kind == "subactividad":
                    objective_code = _csv_value(row, "objective_codigo").lower()
                    activity_code = _csv_value(row, "activity_codigo").lower()
                    sub_code = _csv_value(row, "subactivity_codigo").lower()
                    if not activity_code or not sub_code:
                        raise ValueError("activity_codigo y subactivity_codigo son obligatorios para subactividad.")
                    activity = None
                    if objective_code:
                        objective = objective_by_code.get(objective_code)
                        if objective:
                            activity = activity_by_key.get(f"{int(objective.id)}::{activity_code}")
                    if activity is None:
                        candidates = activity_by_code_list.get(activity_code, [])
                        if len(candidates) == 1:
                            activity = candidates[0]
                    if activity is None:
                        raise ValueError("No se encontró la actividad destino para esta subactividad.")
                    sub_map = sub_by_activity_code.setdefault(activity_code, {})
                    sub = sub_map.get(sub_code)
                    parent_code = _csv_value(row, "subactivity_parent_codigo").lower()
                    parent_sub = sub_map.get(parent_code) if parent_code else None
                    level_raw = _parse_import_int(_csv_value(row, "subactivity_nivel"), 0)
                    level = level_raw if level_raw > 0 else ((int(parent_sub.nivel) + 1) if parent_sub else 1)
                    if level > MAX_SUBTASK_DEPTH:
                        raise ValueError(f"subactivity_nivel no puede ser mayor a {MAX_SUBTASK_DEPTH}.")
                    sub_name = _csv_value(row, "subactivity_nombre")
                    if not sub and not sub_name:
                        raise ValueError("subactivity_nombre es obligatorio al crear una subactividad.")
                    start_date = _parse_import_date(_csv_value(row, "subactivity_fecha_inicial"))
                    end_date = _parse_import_date(_csv_value(row, "subactivity_fecha_final"))
                    if (start_date and not end_date) or (end_date and not start_date):
                        raise ValueError("subactivity_fecha_inicial y subactivity_fecha_final deben definirse juntas.")
                    if start_date and end_date:
                        range_error = _validate_date_range(start_date, end_date, "Subactividad")
                        if range_error:
                            raise ValueError(range_error)
                        parent_range_error = _validate_child_date_range(
                            start_date, end_date, activity.fecha_inicial, activity.fecha_final, "Subactividad", "Actividad"
                        )
                        if parent_range_error:
                            raise ValueError(parent_range_error)
                    if sub:
                        if sub_name:
                            sub.nombre = sub_name
                        sub.parent_subactivity_id = int(parent_sub.id) if parent_sub else None
                        sub.nivel = level
                        sub.responsable = _csv_value(row, "subactivity_responsable")
                        sub.entregable = _csv_value(row, "subactivity_entregable")
                        sub.fecha_inicial = start_date
                        sub.fecha_final = end_date
                        sub.descripcion = _csv_value(row, "subactivity_descripcion")
                        db.add(sub)
                        summary["updated"] += 1
                    else:
                        sub = POASubactivity(
                            activity_id=int(activity.id),
                            parent_subactivity_id=int(parent_sub.id) if parent_sub else None,
                            nivel=level,
                            codigo=sub_code,
                            nombre=sub_name,
                            responsable=_csv_value(row, "subactivity_responsable"),
                            entregable=_csv_value(row, "subactivity_entregable"),
                            fecha_inicial=start_date,
                            fecha_final=end_date,
                            descripcion=_csv_value(row, "subactivity_descripcion"),
                            assigned_by="import_csv",
                        )
                        db.add(sub)
                        db.flush()
                        sub_map[sub_code] = sub
                        summary["created"] += 1
            except Exception as row_error:
                summary["skipped"] += 1
                summary["errors"].append(f"Fila {row_index}: {row_error}")
        db.commit()
        return JSONResponse({"success": True, "summary": summary})
    except (sqlite3.OperationalError, SQLAlchemyError):
        db.rollback()
        return JSONResponse(
            {"success": False, "error": "No se pudo escribir en la base de datos (modo solo lectura o bloqueo)."},
            status_code=500,
        )
    finally:
        db.close()


def get_strategic_identity():
    _bind_core_symbols()
    db = SessionLocal()
    try:
        _ensure_strategic_identity_table(db)
        db.commit()
        rows = db.execute(
            text("SELECT bloque, payload FROM strategic_identity_config WHERE bloque IN ('mision', 'vision', 'valores')")
        ).fetchall()
        payload_map = {str(row[0] or "").strip().lower(): str(row[1] or "[]") for row in rows}
        try:
            mission_json = json.loads(payload_map.get("mision", "[]"))
        except Exception:
            mission_json = []
        try:
            vision_json = json.loads(payload_map.get("vision", "[]"))
        except Exception:
            vision_json = []
        try:
            valores_json = json.loads(payload_map.get("valores", "[]"))
        except Exception:
            valores_json = []
        return JSONResponse(
            {
                "success": True,
                "data": {
                    "mision": _normalize_identity_lines(mission_json, "m"),
                    "vision": _normalize_identity_lines(vision_json, "v"),
                    "valores": _normalize_identity_lines(valores_json, "val"),
                },
            }
        )
    finally:
        db.close()


def get_strategic_foundation():
    _bind_core_symbols()
    db = SessionLocal()
    try:
        _ensure_strategic_identity_table(db)
        db.commit()
        row = db.execute(text("SELECT payload FROM strategic_identity_config WHERE bloque = 'fundamentacion' LIMIT 1")).fetchone()
        payload_raw = str(row[0] or "{}") if row else "{}"
        try:
            payload_json = json.loads(payload_raw)
        except Exception:
            payload_json = {}
        return JSONResponse({"success": True, "data": {"texto": _normalize_foundation_text(payload_json.get("texto"))}})
    finally:
        db.close()


def save_strategic_foundation(data: dict = Body(...)):
    _bind_core_symbols()
    texto = _normalize_foundation_text(data.get("texto"))
    encoded = json.dumps({"texto": texto}, ensure_ascii=False)
    db = SessionLocal()
    try:
        _ensure_strategic_identity_table(db)
        db.execute(
            text(
                """
                INSERT INTO strategic_identity_config (bloque, payload, updated_at)
                VALUES ('fundamentacion', :payload, CURRENT_TIMESTAMP)
                ON CONFLICT (bloque)
                DO UPDATE SET payload = EXCLUDED.payload, updated_at = CURRENT_TIMESTAMP
                """
            ),
            {"payload": encoded},
        )
        db.commit()
        return JSONResponse({"success": True, "data": {"texto": texto}})
    except (sqlite3.OperationalError, SQLAlchemyError):
        db.rollback()
        return JSONResponse({"success": False, "error": "No se pudo escribir en la base de datos (modo solo lectura o bloqueo)."}, status_code=500)
    finally:
        db.close()


def export_strategic_plan_doc():
    _bind_core_symbols()
    db = SessionLocal()
    try:
        _ensure_strategic_identity_table(db)
        db.commit()
        identity_rows = db.execute(
            text("SELECT bloque, payload FROM strategic_identity_config WHERE bloque IN ('mision','vision','valores','fundamentacion')")
        ).fetchall()
        payload_map = {str(row[0] or "").strip().lower(): str(row[1] or "") for row in identity_rows}

        def _parse_lines(block: str, prefix: str) -> List[Dict[str, str]]:
            raw = payload_map.get(block, "[]")
            try:
                data = json.loads(raw)
            except Exception:
                data = []
            return _normalize_identity_lines(data, prefix)

        mision = _parse_lines("mision", "m")
        vision = _parse_lines("vision", "v")
        valores = _parse_lines("valores", "val")
        try:
            foundation_payload = json.loads(payload_map.get("fundamentacion", "{}") or "{}")
        except Exception:
            foundation_payload = {}
        fundamentacion_html = _normalize_foundation_text(foundation_payload.get("texto"))
        axes = (
            db.query(StrategicAxisConfig)
            .filter(StrategicAxisConfig.is_active == True)
            .order_by(StrategicAxisConfig.orden.asc(), StrategicAxisConfig.id.asc())
            .all()
        )
        axis_data = [_serialize_strategic_axis(axis) for axis in axes]
        objective_ids = [
            int(obj.get("id") or 0)
            for axis in axis_data
            for obj in (axis.get("objetivos") or [])
            if int(obj.get("id") or 0) > 0
        ]
        kpis_by_objective = _kpis_by_objective_ids(db, sorted(set(objective_ids)))
        for axis in axis_data:
            for obj in axis.get("objetivos", []):
                obj["kpis"] = kpis_by_objective.get(int(obj.get("id") or 0), [])

        def _lines_html(rows: List[Dict[str, str]]) -> str:
            if not rows:
                return "<p>N/D</p>"
            return "<ul>" + "".join(
                f"<li><strong>{escape(str(item.get('code') or '').upper())}</strong>: {escape(str(item.get('text') or ''))}</li>"
                for item in rows
            ) + "</ul>"

        axes_html_parts: List[str] = []
        for axis in axis_data:
            objectives_html: List[str] = []
            for obj in axis.get("objetivos") or []:
                kpis = obj.get("kpis") or []
                if kpis:
                    kpis_html = "<ul>" + "".join(
                        f"<li>{escape(str(k.get('nombre') or ''))}</li>"
                        for k in kpis
                    ) + "</ul>"
                else:
                    kpis_html = "<p>Sin KPIs registrados.</p>"
                objectives_html.append(
                    "<section class='objective'>"
                    f"<h4>{escape(str(obj.get('nombre') or 'Sin nombre'))}</h4>"
                    f"<div class='rich'>{str(obj.get('descripcion') or '') or '<p>Sin descripción.</p>'}</div>"
                    "<h5>KPIs</h5>"
                    f"{kpis_html}"
                    "</section>"
                )
            axes_html_parts.append(
                "<section class='axis'>"
                f"<h2>{escape(str(axis.get('nombre') or 'Sin nombre'))}</h2>"
                "<h3>Descripción</h3>"
                f"<div class='rich'>{str(axis.get('descripcion') or '') or '<p>Sin descripción.</p>'}</div>"
                "<h3>Objetivos estratégicos</h3>"
                f"{''.join(objectives_html) if objectives_html else '<p>Sin objetivos registrados.</p>'}"
                "</section>"
            )
        now = datetime.utcnow().strftime("%Y-%m-%d")
        html_doc = f"""<!doctype html>
<html>
<head><meta charset="utf-8"><title>Plan Estratégico</title></head>
<body>
  <section class="cover"><h1>Plan estratégico</h1><p class="subtitle">Edición y administración del plan estratégico de la institución</p><p class="date">Fecha de exportación: {escape(now)}</p></section>
  <section class="page-break"><h2>Misión, Visión y Valores</h2><h3>Misión</h3>{_lines_html(mision)}<h3>Visión</h3>{_lines_html(vision)}<h3>Valores</h3>{_lines_html(valores)}</section>
  <section class="page-break"><h2>Fundamentación</h2><div class="rich">{fundamentacion_html or '<p>Sin fundamentación registrada.</p>'}</div></section>
  <section class="page-break"><h2>Ejes estratégicos</h2>{''.join(axes_html_parts) if axes_html_parts else '<p>Sin ejes estratégicos registrados.</p>'}</section>
</body>
</html>"""
        filename = f"plan_estrategico_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.doc"
        return Response(content=html_doc, media_type="application/msword; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
    finally:
        db.close()


def save_strategic_identity_block(bloque: str, data: dict = Body(...)):
    _bind_core_symbols()
    block = str(bloque or "").strip().lower()
    if block not in {"mision", "vision", "valores"}:
        return JSONResponse({"success": False, "error": "Bloque inválido"}, status_code=400)
    prefix = "m" if block == "mision" else ("v" if block == "vision" else "val")
    lines = _normalize_identity_lines(data.get("lineas"), prefix)
    encoded = json.dumps(lines, ensure_ascii=False)
    db = SessionLocal()
    try:
        _ensure_strategic_identity_table(db)
        db.execute(
            text(
                """
                INSERT INTO strategic_identity_config (bloque, payload, updated_at)
                VALUES (:bloque, :payload, CURRENT_TIMESTAMP)
                ON CONFLICT (bloque)
                DO UPDATE SET payload = EXCLUDED.payload, updated_at = CURRENT_TIMESTAMP
                """
            ),
            {"bloque": block, "payload": encoded},
        )
        db.commit()
        return JSONResponse({"success": True, "data": {"bloque": block, "lineas": lines}})
    except (sqlite3.OperationalError, SQLAlchemyError):
        db.rollback()
        return JSONResponse({"success": False, "error": "No se pudo escribir en la base de datos (modo solo lectura o bloqueo)."}, status_code=500)
    finally:
        db.close()


def clear_strategic_identity_block(bloque: str):
    _bind_core_symbols()
    block = str(bloque or "").strip().lower()
    if block not in {"mision", "vision", "valores"}:
        return JSONResponse({"success": False, "error": "Bloque inválido"}, status_code=400)
    prefix = "m" if block == "mision" else ("v" if block == "vision" else "val")
    lines = _normalize_identity_lines([], prefix)
    encoded = json.dumps(lines, ensure_ascii=False)
    db = SessionLocal()
    try:
        _ensure_strategic_identity_table(db)
        db.execute(
            text(
                """
                INSERT INTO strategic_identity_config (bloque, payload, updated_at)
                VALUES (:bloque, :payload, CURRENT_TIMESTAMP)
                ON CONFLICT (bloque)
                DO UPDATE SET payload = EXCLUDED.payload, updated_at = CURRENT_TIMESTAMP
                """
            ),
            {"bloque": block, "payload": encoded},
        )
        db.commit()
        return JSONResponse({"success": True, "data": {"bloque": block, "lineas": lines}})
    except (sqlite3.OperationalError, SQLAlchemyError):
        db.rollback()
        return JSONResponse({"success": False, "error": "No se pudo escribir en la base de datos (modo solo lectura o bloqueo)."}, status_code=500)
    finally:
        db.close()


def list_strategic_axes(request: Request):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        axes = (
            db.query(StrategicAxisConfig)
            .filter(StrategicAxisConfig.is_active == True)
            .order_by(StrategicAxisConfig.orden.asc(), StrategicAxisConfig.id.asc())
            .all()
        )
        if not axes:
            axes = db.query(StrategicAxisConfig).order_by(StrategicAxisConfig.orden.asc(), StrategicAxisConfig.id.asc()).all()
        payload_axes = [_serialize_strategic_axis(axis) for axis in axes]
        axis_kpis_by_axis = _axis_kpis_by_axis_ids(db, [int(axis.get("id") or 0) for axis in payload_axes if int(axis.get("id") or 0) > 0])
        objective_ids = sorted({int(obj.get("id") or 0) for axis in payload_axes for obj in axis.get("objetivos", []) if int(obj.get("id") or 0)})
        kpis_by_objective = _kpis_by_objective_ids(db, objective_ids)
        milestones_by_objective = _milestones_by_objective_ids(db, objective_ids)
        activities = db.query(POAActivity).filter(POAActivity.objective_id.in_(objective_ids)).all() if objective_ids else []
        activity_ids = [int(item.id) for item in activities if getattr(item, "id", None)]
        subactivities = db.query(POASubactivity).filter(POASubactivity.activity_id.in_(activity_ids)).all() if activity_ids else []
        sub_by_activity: Dict[int, List[Any]] = {}
        for sub in subactivities:
            sub_by_activity.setdefault(int(sub.activity_id), []).append(sub)
        today = datetime.utcnow().date()
        activity_progress_by_objective: Dict[int, List[int]] = {}
        for activity in activities:
            subs = sub_by_activity.get(int(activity.id), [])
            progress = int(round((sum(1 for sub in subs if sub.fecha_final and today >= sub.fecha_final) / len(subs)) * 100)) if subs else (100 if _activity_status(activity) == "Terminada" else 0)
            activity_progress_by_objective.setdefault(int(activity.objective_id), []).append(progress)
        mv_agg: Dict[str, List[int]] = {}
        for axis_data in payload_axes:
            axis_data["kpis"] = axis_kpis_by_axis.get(int(axis_data.get("id") or 0), [])
            objective_progress: List[int] = []
            for obj in axis_data.get("objetivos", []):
                obj_id = int(obj.get("id") or 0)
                obj["kpis"] = kpis_by_objective.get(obj_id, [])
                obj["hitos"] = milestones_by_objective.get(obj_id, [])
                if obj["hitos"]:
                    obj["hito"] = str(obj["hitos"][0].get("nombre") or obj.get("hito") or "")
                progress_list = activity_progress_by_objective.get(obj_id, [])
                obj_progress = int(round(sum(progress_list) / len(progress_list))) if progress_list else 0
                obj["avance"] = obj_progress
                objective_progress.append(obj_progress)
            axis_progress = int(round(sum(objective_progress) / len(objective_progress))) if objective_progress else 0
            axis_data["avance"] = axis_progress
            base_code = "".join(ch for ch in str(axis_data.get("codigo") or "").split("-", 1)[0].lower() if ch.isalnum())
            axis_data["base_code"] = base_code
            if base_code:
                mv_agg.setdefault(base_code, []).append(axis_progress)
        mv_data = [{"code": code, "avance": int(round(sum(values) / len(values))) if values else 0} for code, values in sorted(mv_agg.items(), key=lambda item: item[0])]
        return JSONResponse({"success": True, "data": payload_axes, "mision_vision_avance": mv_data})
    finally:
        db.close()


def list_strategic_axis_departments():
    _bind_core_symbols()
    db = SessionLocal()
    try:
        rows = db.query(Usuario.departamento).filter(Usuario.departamento.isnot(None)).all()
        unique_departments = sorted({(row[0] or "").strip() for row in rows if (row[0] or "").strip()}, key=lambda item: item.lower())
        return JSONResponse({"success": True, "data": unique_departments})
    finally:
        db.close()


def list_collaborators_by_department(department: str = Query(default="")):
    _bind_core_symbols()
    dep = (department or "").strip()
    if not dep:
        return JSONResponse({"success": True, "data": []})
    db = SessionLocal()
    try:
        rows = db.query(Usuario.nombre).filter(Usuario.departamento == dep).all()
        unique_collaborators = sorted({(row[0] or "").strip() for row in rows if (row[0] or "").strip()}, key=lambda item: item.lower())
        return JSONResponse({"success": True, "data": unique_collaborators})
    finally:
        db.close()


def list_strategic_axis_collaborators(axis_id: int):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        axis = db.query(StrategicAxisConfig).filter(StrategicAxisConfig.id == axis_id).first()
        if not axis:
            return JSONResponse({"success": False, "error": "Eje no encontrado"}, status_code=404)
        department = (axis.lider_departamento or "").strip()
        if not department:
            return JSONResponse({"success": True, "data": []})
        rows = db.query(Usuario.nombre).filter(Usuario.departamento == department).all()
        unique_collaborators = sorted({(row[0] or "").strip() for row in rows if (row[0] or "").strip()}, key=lambda item: item.lower())
        return JSONResponse({"success": True, "data": unique_collaborators})
    finally:
        db.close()


def create_strategic_axis(request: Request, data: dict = Body(...)):
    _bind_core_symbols()
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        return JSONResponse({"success": False, "error": "El nombre del eje es obligatorio"}, status_code=400)
    db = SessionLocal()
    try:
        max_order = db.query(func.max(StrategicAxisConfig.orden)).scalar() or 0
        axis_order = int(data.get("orden") or (max_order + 1))
        start_date, start_error = _parse_date_field(data.get("fecha_inicial"), "Fecha inicial", required=False)
        if start_error:
            return JSONResponse({"success": False, "error": start_error}, status_code=400)
        end_date, end_error = _parse_date_field(data.get("fecha_final"), "Fecha final", required=False)
        if end_error:
            return JSONResponse({"success": False, "error": end_error}, status_code=400)
        if (start_date and not end_date) or (end_date and not start_date):
            return JSONResponse({"success": False, "error": "Eje estratégico: fecha inicial y fecha final deben definirse juntas"}, status_code=400)
        if start_date and end_date:
            range_error = _validate_date_range(start_date, end_date, "Eje estratégico")
            if range_error:
                return JSONResponse({"success": False, "error": range_error}, status_code=400)
        base_code = (data.get("base_code") or "").strip()
        if not base_code:
            raw_code = (data.get("codigo") or "").strip().lower()
            base_code = raw_code.split("-", 1)[0] if "-" in raw_code else raw_code
        axis = StrategicAxisConfig(
            nombre=nombre,
            codigo=_compose_axis_code(base_code, axis_order),
            lider_departamento=(data.get("lider_departamento") or "").strip(),
            responsabilidad_directa=(data.get("responsabilidad_directa") or "").strip(),
            fecha_inicial=start_date,
            fecha_final=end_date,
            descripcion=(data.get("descripcion") or "").strip(),
            orden=axis_order,
            is_active=True,
        )
        db.add(axis)
        db.commit()
        if "kpis" in data:
            _replace_axis_kpis(db, int(axis.id), data.get("kpis"))
            db.commit()
        db.refresh(axis)
        payload = _serialize_strategic_axis(axis)
        payload["kpis"] = _axis_kpis_by_axis_ids(db, [int(axis.id)]).get(int(axis.id), [])
        return JSONResponse({"success": True, "data": payload})
    except (sqlite3.OperationalError, SQLAlchemyError):
        db.rollback()
        return JSONResponse({"success": False, "error": "No se pudo escribir en la base de datos (modo solo lectura o bloqueo)."}, status_code=500)
    finally:
        db.close()


def update_strategic_axis(axis_id: int, data: dict = Body(...)):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        axis = db.query(StrategicAxisConfig).filter(StrategicAxisConfig.id == axis_id).first()
        if not axis:
            return JSONResponse({"success": False, "error": "Eje no encontrado"}, status_code=404)
        nombre = (data.get("nombre") or "").strip()
        if not nombre:
            return JSONResponse({"success": False, "error": "El nombre del eje es obligatorio"}, status_code=400)
        axis_order = int(data.get("orden") or axis.orden or 1)
        start_date, start_error = _parse_date_field(data.get("fecha_inicial"), "Fecha inicial", required=False)
        if start_error:
            return JSONResponse({"success": False, "error": start_error}, status_code=400)
        end_date, end_error = _parse_date_field(data.get("fecha_final"), "Fecha final", required=False)
        if end_error:
            return JSONResponse({"success": False, "error": end_error}, status_code=400)
        if (start_date and not end_date) or (end_date and not start_date):
            return JSONResponse({"success": False, "error": "Eje estratégico: fecha inicial y fecha final deben definirse juntas"}, status_code=400)
        if start_date and end_date:
            range_error = _validate_date_range(start_date, end_date, "Eje estratégico")
            if range_error:
                return JSONResponse({"success": False, "error": range_error}, status_code=400)
        base_code = (data.get("base_code") or "").strip()
        if not base_code:
            raw_code = (data.get("codigo") or axis.codigo or "").strip().lower()
            base_code = raw_code.split("-", 1)[0] if "-" in raw_code else raw_code
        axis.nombre = nombre
        axis.codigo = _compose_axis_code(base_code, axis_order)
        axis.lider_departamento = (data.get("lider_departamento") or "").strip()
        axis.responsabilidad_directa = (data.get("responsabilidad_directa") or "").strip()
        axis.fecha_inicial = start_date
        axis.fecha_final = end_date
        axis.descripcion = (data.get("descripcion") or "").strip()
        axis.orden = axis_order
        db.add(axis)
        db.commit()
        if "kpis" in data:
            _replace_axis_kpis(db, int(axis.id), data.get("kpis"))
            db.commit()
        db.refresh(axis)
        payload = _serialize_strategic_axis(axis)
        payload["kpis"] = _axis_kpis_by_axis_ids(db, [int(axis.id)]).get(int(axis.id), [])
        return JSONResponse({"success": True, "data": payload})
    except (sqlite3.OperationalError, SQLAlchemyError):
        db.rollback()
        return JSONResponse({"success": False, "error": "No se pudo escribir en la base de datos (modo solo lectura o bloqueo)."}, status_code=500)
    finally:
        db.close()


def delete_strategic_axis(axis_id: int):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        axis = db.query(StrategicAxisConfig).filter(StrategicAxisConfig.id == axis_id).first()
        if not axis:
            return JSONResponse({"success": False, "error": "Eje no encontrado"}, status_code=404)
        _delete_axis_kpis(db, int(axis.id))
        db.delete(axis)
        db.commit()
        return JSONResponse({"success": True})
    except (sqlite3.OperationalError, SQLAlchemyError):
        db.rollback()
        return JSONResponse({"success": False, "error": "No se pudo escribir en la base de datos (modo solo lectura o bloqueo)."}, status_code=500)
    finally:
        db.close()


def create_strategic_objective(axis_id: int, data: dict = Body(...)):
    _bind_core_symbols()
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        return JSONResponse({"success": False, "error": "El nombre del objetivo es obligatorio"}, status_code=400)
    db = SessionLocal()
    try:
        axis = db.query(StrategicAxisConfig).filter(StrategicAxisConfig.id == axis_id).first()
        if not axis:
            return JSONResponse({"success": False, "error": "Eje no encontrado"}, status_code=404)
        start_date, start_error = _parse_date_field(data.get("fecha_inicial"), "Fecha inicial", required=False)
        if start_error:
            return JSONResponse({"success": False, "error": start_error}, status_code=400)
        end_date, end_error = _parse_date_field(data.get("fecha_final"), "Fecha final", required=False)
        if end_error:
            return JSONResponse({"success": False, "error": end_error}, status_code=400)
        if (start_date and not end_date) or (end_date and not start_date):
            return JSONResponse({"success": False, "error": "Objetivo: fecha inicial y fecha final deben definirse juntas"}, status_code=400)
        if start_date and end_date:
            range_error = _validate_date_range(start_date, end_date, "Objetivo")
            if range_error:
                return JSONResponse({"success": False, "error": range_error}, status_code=400)
        objective_leader = (data.get("lider") or "").strip()
        axis_department = (axis.lider_departamento or "").strip()
        if objective_leader and axis_department and not _collaborator_belongs_to_department(db, objective_leader, axis_department):
            return JSONResponse({"success": False, "error": "El líder debe pertenecer al personal del área/departamento del eje."}, status_code=400)
        max_order = db.query(func.max(StrategicObjectiveConfig.orden)).filter(StrategicObjectiveConfig.eje_id == axis_id).scalar() or 0
        objective_order = int(data.get("orden") or (max_order + 1))
        objective = StrategicObjectiveConfig(
            eje_id=axis_id,
            codigo=_compose_objective_code(axis.codigo or "", objective_order),
            nombre=nombre,
            hito=(data.get("hito") or "").strip(),
            lider=objective_leader,
            fecha_inicial=start_date,
            fecha_final=end_date,
            descripcion=(data.get("descripcion") or "").strip(),
            orden=objective_order,
            is_active=True,
        )
        db.add(objective)
        db.commit()
        db.refresh(objective)
        milestone_rows: List[Dict[str, Any]] = []
        if "hitos" in data:
            milestone_rows = _replace_objective_milestones(db, int(objective.id), data.get("hitos"))
            if milestone_rows:
                objective.hito = str(milestone_rows[0].get("nombre") or "").strip()
                db.add(objective)
                db.commit()
                db.refresh(objective)
        if "kpis" in data:
            _replace_objective_kpis(db, int(objective.id), data.get("kpis"))
            db.commit()
        payload = _serialize_strategic_objective(objective)
        if "hitos" in data:
            payload["hitos"] = milestone_rows
            if milestone_rows:
                payload["hito"] = str(milestone_rows[0].get("nombre") or "")
        return JSONResponse({"success": True, "data": payload})
    except (sqlite3.OperationalError, SQLAlchemyError):
        db.rollback()
        return JSONResponse({"success": False, "error": "No se pudo escribir en la base de datos (modo solo lectura o bloqueo)."}, status_code=500)
    finally:
        db.close()


def update_strategic_objective(objective_id: int, data: dict = Body(...)):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        objective = db.query(StrategicObjectiveConfig).filter(StrategicObjectiveConfig.id == objective_id).first()
        if not objective:
            return JSONResponse({"success": False, "error": "Objetivo no encontrado"}, status_code=404)
        nombre = (data.get("nombre") or "").strip()
        if not nombre:
            return JSONResponse({"success": False, "error": "El nombre del objetivo es obligatorio"}, status_code=400)
        start_date, start_error = _parse_date_field(data.get("fecha_inicial"), "Fecha inicial", required=False)
        if start_error:
            return JSONResponse({"success": False, "error": start_error}, status_code=400)
        end_date, end_error = _parse_date_field(data.get("fecha_final"), "Fecha final", required=False)
        if end_error:
            return JSONResponse({"success": False, "error": end_error}, status_code=400)
        if (start_date and not end_date) or (end_date and not start_date):
            return JSONResponse({"success": False, "error": "Objetivo: fecha inicial y fecha final deben definirse juntas"}, status_code=400)
        if start_date and end_date:
            range_error = _validate_date_range(start_date, end_date, "Objetivo")
            if range_error:
                return JSONResponse({"success": False, "error": range_error}, status_code=400)
        axis = db.query(StrategicAxisConfig).filter(StrategicAxisConfig.id == objective.eje_id).first()
        objective_leader = (data.get("lider") or "").strip()
        axis_department = (axis.lider_departamento or "").strip() if axis else ""
        if objective_leader and axis_department and not _collaborator_belongs_to_department(db, objective_leader, axis_department):
            return JSONResponse({"success": False, "error": "El líder debe pertenecer al personal del área/departamento del eje."}, status_code=400)
        objective_order = int(data.get("orden") or objective.orden or 1)
        objective.codigo = _compose_objective_code((axis.codigo if axis else ""), objective_order)
        objective.nombre = nombre
        objective.hito = (data.get("hito") or "").strip()
        objective.lider = objective_leader
        objective.fecha_inicial = start_date
        objective.fecha_final = end_date
        objective.descripcion = (data.get("descripcion") or "").strip()
        objective.orden = objective_order
        db.add(objective)
        milestone_rows: List[Dict[str, Any]] = []
        if "hitos" in data:
            milestone_rows = _replace_objective_milestones(db, int(objective.id), data.get("hitos"))
            objective.hito = str(milestone_rows[0].get("nombre") or "").strip() if milestone_rows else ""
            db.add(objective)
        if "kpis" in data:
            _replace_objective_kpis(db, int(objective.id), data.get("kpis"))
        db.commit()
        db.refresh(objective)
        payload = _serialize_strategic_objective(objective)
        if "hitos" in data:
            payload["hitos"] = milestone_rows
            if milestone_rows:
                payload["hito"] = str(milestone_rows[0].get("nombre") or "")
        return JSONResponse({"success": True, "data": payload})
    finally:
        db.close()


def delete_strategic_objective(objective_id: int):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        objective = db.query(StrategicObjectiveConfig).filter(StrategicObjectiveConfig.id == objective_id).first()
        if not objective:
            return JSONResponse({"success": False, "error": "Objetivo no encontrado"}, status_code=404)
        _delete_objective_kpis(db, int(objective.id))
        _delete_objective_milestones(db, int(objective.id))
        db.delete(objective)
        db.commit()
        return JSONResponse({"success": True})
    finally:
        db.close()

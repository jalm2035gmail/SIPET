from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO
import re

from fastapi import Body, File, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
import pandas as pd
import numpy as np

_CORE_BOUND = False

KPI_TEMPLATE_HEADERS = [
    "axis_codigo",
    "axis_nombre",
    "kpi_nombre",
    "responsable",
    "descripcion",
    "objetivo",
    "formula",
    "fuente_datos",
    "unidad",
    "frecuencia",
    "linea_MAIN",
    "estandar_meta",
    "categoria",
    "perspectiva",
    "semaforo_rojo",
    "semaforo_verde",
]


def _ensure_indicator_definition_table(db) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS brujula_indicator_definitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre VARCHAR(255) NOT NULL DEFAULT '',
            responsable VARCHAR(255) NOT NULL DEFAULT '',
            descripcion TEXT NOT NULL DEFAULT '',
            objetivo TEXT NOT NULL DEFAULT '',
            formula TEXT NOT NULL DEFAULT '',
            fuente_datos TEXT NOT NULL DEFAULT '',
            unidad VARCHAR(120) NOT NULL DEFAULT '',
            frecuencia VARCHAR(120) NOT NULL DEFAULT '',
            linea_MAIN TEXT NOT NULL DEFAULT '',
            estandar_meta TEXT NOT NULL DEFAULT '',
            categoria VARCHAR(255) NOT NULL DEFAULT '',
            perspectiva VARCHAR(255) NOT NULL DEFAULT '',
            semaforo_rojo TEXT NOT NULL DEFAULT '',
            semaforo_verde TEXT NOT NULL DEFAULT '',
            orden INTEGER NOT NULL DEFAULT 0
        )
    """))
    db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_brujula_indicator_definitions_nombre ON brujula_indicator_definitions(nombre)"))
    rows = db.execute(text("SELECT COUNT(*) FROM brujula_indicator_definitions")).fetchone()
    existing_total = int(rows[0] or 0) if rows else 0
    if existing_total > 0:
        return
    try:
        legacy = db.execute(text("""
            SELECT nombre, responsable, descripcion, objetivo, formula, fuente_datos,
                   unidad, frecuencia, linea_MAIN, estandar_meta, categoria, perspectiva,
                   semaforo_rojo, semaforo_verde, orden
            FROM strategic_axis_kpis
            WHERE TRIM(COALESCE(nombre, '')) <> ''
            ORDER BY orden ASC, id ASC
        """)).fetchall()
    except Exception:
        legacy = []
    seen = set()
    next_order = 0
    for row in legacy:
        nombre = str(row[0] or "").strip()
        key = nombre.lower()
        if not nombre or key in seen:
            continue
        seen.add(key)
        next_order += 1
        db.execute(text("""
            INSERT INTO brujula_indicator_definitions (
                nombre, responsable, descripcion, objetivo, formula, fuente_datos, unidad,
                frecuencia, linea_MAIN, estandar_meta, categoria, perspectiva, semaforo_rojo,
                semaforo_verde, orden
            ) VALUES (
                :nombre, :responsable, :descripcion, :objetivo, :formula, :fuente_datos, :unidad,
                :frecuencia, :linea_MAIN, :estandar_meta, :categoria, :perspectiva, :semaforo_rojo,
                :semaforo_verde, :orden
            )
        """), {
            "nombre": nombre,
            "responsable": str(row[1] or ""),
            "descripcion": str(row[2] or ""),
            "objetivo": str(row[3] or ""),
            "formula": str(row[4] or ""),
            "fuente_datos": str(row[5] or ""),
            "unidad": str(row[6] or ""),
            "frecuencia": str(row[7] or ""),
            "linea_MAIN": str(row[8] or ""),
            "estandar_meta": str(row[9] or ""),
            "categoria": str(row[10] or ""),
            "perspectiva": str(row[11] or ""),
            "semaforo_rojo": str(row[12] or ""),
            "semaforo_verde": str(row[13] or ""),
            "orden": int(row[14] or next_order),
        })


def _indicator_definition_from_row(row) -> dict:
    return {
        "id": int(row[0] or 0),
        "nombre": str(row[1] or ""),
        "responsable": str(row[2] or ""),
        "descripcion": str(row[3] or ""),
        "objetivo": str(row[4] or ""),
        "formula": str(row[5] or ""),
        "fuente_datos": str(row[6] or ""),
        "unidad": str(row[7] or ""),
        "frecuencia": str(row[8] or ""),
        "linea_MAIN": str(row[9] or ""),
        "estandar_meta": str(row[10] or ""),
        "categoria": str(row[11] or ""),
        "perspectiva": str(row[12] or ""),
        "semaforo_rojo": str(row[13] or ""),
        "semaforo_verde": str(row[14] or ""),
        "orden": int(row[15] or 0),
    }


def list_indicator_definitions(db) -> list[dict]:
    _ensure_indicator_definition_table(db)
    rows = db.execute(text("""
        SELECT id, nombre, responsable, descripcion, objetivo, formula, fuente_datos, unidad,
               frecuencia, linea_MAIN, estandar_meta, categoria, perspectiva, semaforo_rojo,
               semaforo_verde, orden
        FROM brujula_indicator_definitions
        ORDER BY orden ASC, id ASC
    """)).fetchall()
    return [_indicator_definition_from_row(row) for row in rows]


def save_indicator_definition_record(db, payload: dict, indicator_id: int | None = None) -> dict:
    _ensure_indicator_definition_table(db)
    nombre = str(payload.get("nombre") or "").strip()
    if not nombre:
        raise ValueError("El nombre del indicador es obligatorio.")
    current = {
        "nombre": nombre,
        "responsable": str(payload.get("responsable") or "").strip(),
        "descripcion": str(payload.get("descripcion") or "").strip(),
        "objetivo": str(payload.get("objetivo") or "").strip(),
        "formula": str(payload.get("formula") or "").strip(),
        "fuente_datos": str(payload.get("fuente_datos") or "").strip(),
        "unidad": str(payload.get("unidad") or "").strip(),
        "frecuencia": str(payload.get("frecuencia") or "").strip(),
        "linea_MAIN": str(payload.get("linea_MAIN") or "").strip(),
        "estandar_meta": str(payload.get("estandar_meta") or "").strip(),
        "categoria": str(payload.get("categoria") or "").strip(),
        "perspectiva": str(payload.get("perspectiva") or "").strip(),
        "semaforo_rojo": str(payload.get("semaforo_rojo") or "").strip(),
        "semaforo_verde": str(payload.get("semaforo_verde") or "").strip(),
    }
    duplicate = db.execute(
        text("""
            SELECT id FROM brujula_indicator_definitions
            WHERE lower(nombre) = :nombre AND (:indicator_id = 0 OR id <> :indicator_id)
        """),
        {"nombre": nombre.lower(), "indicator_id": int(indicator_id or 0)},
    ).fetchone()
    if duplicate:
        raise ValueError("Ya existe un indicador con ese nombre.")
    if indicator_id:
        db.execute(text("""
            UPDATE brujula_indicator_definitions
            SET nombre = :nombre,
                responsable = :responsable,
                descripcion = :descripcion,
                objetivo = :objetivo,
                formula = :formula,
                fuente_datos = :fuente_datos,
                unidad = :unidad,
                frecuencia = :frecuencia,
                linea_MAIN = :linea_MAIN,
                estandar_meta = :estandar_meta,
                categoria = :categoria,
                perspectiva = :perspectiva,
                semaforo_rojo = :semaforo_rojo,
                semaforo_verde = :semaforo_verde
            WHERE id = :id
        """), {**current, "id": int(indicator_id)})
    else:
        max_order_row = db.execute(text("SELECT COALESCE(MAX(orden), 0) FROM brujula_indicator_definitions")).fetchone()
        next_order = int(max_order_row[0] or 0) + 1 if max_order_row else 1
        db.execute(text("""
            INSERT INTO brujula_indicator_definitions (
                nombre, responsable, descripcion, objetivo, formula, fuente_datos, unidad,
                frecuencia, linea_MAIN, estandar_meta, categoria, perspectiva, semaforo_rojo,
                semaforo_verde, orden
            ) VALUES (
                :nombre, :responsable, :descripcion, :objetivo, :formula, :fuente_datos, :unidad,
                :frecuencia, :linea_MAIN, :estandar_meta, :categoria, :perspectiva, :semaforo_rojo,
                :semaforo_verde, :orden
            )
        """), {**current, "orden": next_order})
        indicator_id_row = db.execute(text("SELECT last_insert_rowid()")).fetchone()
        indicator_id = int(indicator_id_row[0] or 0) if indicator_id_row else 0
    row = db.execute(text("""
        SELECT id, nombre, responsable, descripcion, objetivo, formula, fuente_datos, unidad,
               frecuencia, linea_MAIN, estandar_meta, categoria, perspectiva, semaforo_rojo,
               semaforo_verde, orden
        FROM brujula_indicator_definitions
        WHERE id = :id
    """), {"id": int(indicator_id or 0)}).fetchone()
    if not row:
        raise ValueError("No se pudo guardar el indicador.")
    return _indicator_definition_from_row(row)


def delete_indicator_definition_record(db, indicator_id: int) -> None:
    _ensure_indicator_definition_table(db)
    db.execute(text("DELETE FROM brujula_indicator_definitions WHERE id = :id"), {"id": int(indicator_id)})


def _kpi_template_rows():
    return [
        {
            "axis_codigo": "m1-01",
            "axis_nombre": "Crecimiento institucional",
            "kpi_nombre": "Ingresos por ventas",
            "responsable": "Director Comercial",
            "descripcion": "Mide el monto total facturado en el periodo.",
            "objetivo": "Incrementar los ingresos frente al periodo anterior.",
            "formula": "Suma de facturas emitidas en el mes.",
            "fuente_datos": "ERP / Facturacion",
            "unidad": "MXN",
            "frecuencia": "Mensual",
            "linea_MAIN": "50000",
            "estandar_meta": "60000",
            "categoria": "Financiera",
            "perspectiva": "Financiera",
            "semaforo_rojo": "< 50000",
            "semaforo_verde": ">= 60000",
        },
        {
            "axis_codigo": "m2-02",
            "axis_nombre": "Experiencia del socio",
            "kpi_nombre": "Satisfaccion del socio",
            "responsable": "Gerencia de Servicio",
            "descripcion": "Promedio de satisfaccion en encuestas cerradas.",
            "objetivo": "Mejorar la experiencia de atencion.",
            "formula": "Promedio simple de calificaciones de encuesta.",
            "fuente_datos": "Encuestas digitales",
            "unidad": "%",
            "frecuencia": "Mensual",
            "linea_MAIN": "82",
            "estandar_meta": "90",
            "categoria": "Servicio",
            "perspectiva": "Cliente",
            "semaforo_rojo": "< 80",
            "semaforo_verde": ">= 90",
        },
    ]


def download_kpis_template():
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=KPI_TEMPLATE_HEADERS)
    writer.writeheader()
    for row in _kpi_template_rows():
        writer.writerow({key: row.get(key, "") for key in KPI_TEMPLATE_HEADERS})
    headers = {"Content-Disposition": 'attachment; filename="plantilla_importacion_kpis.csv"'}
    return Response(output.getvalue(), media_type="text/csv; charset=utf-8", headers=headers)


def _csv_field(row: dict, key: str) -> str:
    return str((row.get(key) or "")).strip()


def _normalize_import_kpi_row(row: dict) -> dict:
    return {
        "nombre": _csv_field(row, "kpi_nombre"),
        "responsable": _csv_field(row, "responsable"),
        "descripcion": _csv_field(row, "descripcion"),
        "objetivo": _csv_field(row, "objetivo"),
        "formula": _csv_field(row, "formula"),
        "fuente_datos": _csv_field(row, "fuente_datos"),
        "unidad": _csv_field(row, "unidad"),
        "frecuencia": _csv_field(row, "frecuencia"),
        "linea_MAIN": _csv_field(row, "linea_MAIN"),
        "estandar_meta": _csv_field(row, "estandar_meta"),
        "categoria": _csv_field(row, "categoria"),
        "perspectiva": _csv_field(row, "perspectiva"),
        "semaforo_rojo": _csv_field(row, "semaforo_rojo"),
        "semaforo_verde": _csv_field(row, "semaforo_verde"),
    }


async def import_kpis_template(file: UploadFile = File(...)):
    _bind_core_symbols()
    filename = str(file.filename or "").strip().lower()
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

    required_headers = ["kpi_nombre"]
    missing_headers = [header for header in required_headers if header not in reader.fieldnames]
    if missing_headers:
        return JSONResponse(
            {"success": False, "error": f"Faltan columnas obligatorias: {', '.join(missing_headers)}"},
            status_code=400,
        )

    db = SessionLocal()
    summary = {"created": 0, "updated": 0, "skipped": 0, "errors": []}
    try:
        _ensure_indicator_definition_table(db)
        db.commit()
        existing_rows = db.execute(text("""
            SELECT id, nombre
            FROM brujula_indicator_definitions
            ORDER BY orden ASC, id ASC
        """)).fetchall()
        existing_by_name = {
            str(row[1] or "").strip().lower(): int(row[0] or 0)
            for row in existing_rows
            if str(row[1] or "").strip()
        }

        for row_index, row in enumerate(reader, start=2):
            try:
                payload = _normalize_import_kpi_row(row)
                if not payload["nombre"]:
                    raise ValueError("kpi_nombre es obligatorio")
                existing_id = existing_by_name.get(payload["nombre"].lower())
                if existing_id:
                    save_indicator_definition_record(db, payload, existing_id)
                    summary["updated"] += 1
                else:
                    saved = save_indicator_definition_record(db, payload, None)
                    existing_by_name[payload["nombre"].lower()] = int(saved.get("id") or 0)
                    summary["created"] += 1
            except Exception as row_error:
                summary["skipped"] += 1
                summary["errors"].append(f"Fila {row_index}: {row_error}")

        db.commit()
        return JSONResponse({"success": True, "summary": summary})
    except Exception as exc:
        db.rollback()
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)
    finally:
        db.close()


def _bind_core_symbols() -> None:
    global _CORE_BOUND
    if _CORE_BOUND:
        return
    from fastapi_modulo import main as core

    globals()["SessionLocal"] = getattr(core, "SessionLocal")
    globals()["_normalize_tenant_id"] = getattr(core, "_normalize_tenant_id")
    globals()["get_current_tenant"] = getattr(core, "get_current_tenant")
    try:
        globals()["_ensure_objective_kpi_table"] = getattr(core, "_ensure_objective_kpi_table")
    except AttributeError:
        from fastapi_modulo.modulos.planificacion.modelos.plan_estrategico_service import _ensure_objective_kpi_table as ensure_objective_kpi_table

        globals()["_ensure_objective_kpi_table"] = ensure_objective_kpi_table
    _CORE_BOUND = True


def _current_tenant_id(request: Request | None = None) -> str:
    _bind_core_symbols()
    if request is None:
        return _normalize_tenant_id("default")
    return _normalize_tenant_id(get_current_tenant(request))


def _ensure_kpi_mediciones_table(db) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS kpi_mediciones (
            id          INTEGER  PRIMARY KEY AUTOINCREMENT,
            tenant_id   VARCHAR(100) NOT NULL DEFAULT 'default',
            kpi_id      INTEGER  NOT NULL,
            valor       REAL     NOT NULL,
            periodo     VARCHAR(50)  NOT NULL DEFAULT '',
            notas       TEXT         NOT NULL DEFAULT '',
            created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL DEFAULT ''
        )
    """))
    try:
        cols = db.execute(text("PRAGMA table_info(kpi_mediciones)")).fetchall()
        col_names = {str(col[1]).strip().lower() for col in cols if len(col) > 1}
        if "tenant_id" not in col_names:
            db.execute(text("ALTER TABLE kpi_mediciones ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'default'"))
        db.execute(text("UPDATE kpi_mediciones SET tenant_id = 'default' WHERE tenant_id IS NULL OR tenant_id = ''"))
        db.execute(text("CREATE INDEX IF NOT EXISTS ix_kpi_mediciones_tenant_id ON kpi_mediciones(tenant_id)"))
    except Exception:
        pass
    db.commit()


def _kpi_parse_referencia(referencia: str):
    ref = re.sub(r"[%\s]", "", str(referencia or ""))
    if "-" in ref:
        parts = ref.split("-", 1)
        try:
            return float(parts[0]), float(parts[1])
        except (ValueError, IndexError):
            return None, None
    try:
        return float(ref), None
    except ValueError:
        return None, None


def _kpi_evaluate_status(valor: float, estandar: str, referencia: str) -> str:
    lo, hi = _kpi_parse_referencia(referencia)
    if lo is None:
        return "sin_meta"
    std = str(estandar or "").strip().lower()
    if std == "mayor":
        if valor >= lo:
            return "ok"
        margin = abs(lo * 0.10) if lo != 0 else 0.5
        return "warning" if valor >= lo - margin else "alert"
    if std == "menor":
        if valor <= lo:
            return "ok"
        margin = abs(lo * 0.10) if lo != 0 else 0.5
        return "warning" if valor <= lo + margin else "alert"
    if std == "entre" and hi is not None:
        if lo <= valor <= hi:
            return "ok"
        rng = abs(hi - lo) * 0.10 or 0.5
        return "warning" if (lo - rng) <= valor <= (hi + rng) else "alert"
    if std == "igual":
        tol = abs(lo * 0.05) if lo != 0 else 0.5
        if abs(valor - lo) <= tol:
            return "ok"
        tol2 = abs(lo * 0.15) if lo != 0 else 1.0
        return "warning" if abs(valor - lo) <= tol2 else "alert"
    return "sin_meta"


def kpis_definiciones(request: Request):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        tenant_id = _current_tenant_id(request)
        _ensure_indicator_definition_table(db)
        _ensure_kpi_mediciones_table(db)
        rows = db.execute(text("""
            SELECT
                id, nombre, descripcion, formula, frecuencia, estandar_meta, orden,
                responsable, objetivo, fuente_datos, unidad, linea_MAIN, categoria,
                perspectiva, semaforo_rojo, semaforo_verde
            FROM brujula_indicator_definitions
            ORDER BY orden ASC, id ASC
        """)).fetchall()
        kpi_ids = [int(r[0]) for r in rows]
        latest_by_kpi = {}
        if kpi_ids:
            placeholders = ", ".join(f":k{i}" for i in range(len(kpi_ids)))
            params = {f"k{i}": v for i, v in enumerate(kpi_ids)}
            meds = db.execute(text(f"""
                SELECT kpi_id, valor, periodo, created_at
                FROM kpi_mediciones
                WHERE tenant_id = :tenant_id AND kpi_id IN ({placeholders})
                ORDER BY created_at DESC
            """), {"tenant_id": tenant_id, **params}).fetchall()
            seen = set()
            for m in meds:
                kid = int(m[0])
                if kid not in seen:
                    latest_by_kpi[kid] = {
                        "valor": float(m[1]),
                        "periodo": str(m[2] or ""),
                        "created_at": str(m[3] or ""),
                    }
                    seen.add(kid)
        data = []
        for r in rows:
            kpi_id = int(r[0])
            latest = latest_by_kpi.get(kpi_id)
            estandar = "mayor"
            referencia = str(r[5] or "")
            status = _kpi_evaluate_status(latest["valor"], estandar, referencia) if latest else "sin_medicion"
            data.append({
                "id": kpi_id,
                "objective_id": 0,
                "nombre": str(r[1] or ""),
                "proposito": str(r[2] or ""),
                "formula": str(r[3] or ""),
                "periodicidad": str(r[4] or ""),
                "estandar": estandar,
                "referencia": referencia,
                "orden": int(r[6] or 0),
                "obj_nombre": "",
                "obj_codigo": "",
                "axis_nombre": "Brújula",
                "axis_codigo": "BRJ",
                "responsable": str(r[7] or ""),
                "objetivo": str(r[8] or ""),
                "fuente_datos": str(r[9] or ""),
                "unidad": str(r[10] or ""),
                "linea_MAIN": str(r[11] or ""),
                "categoria": str(r[12] or ""),
                "perspectiva": str(r[13] or ""),
                "semaforo_rojo": str(r[14] or ""),
                "semaforo_verde": str(r[15] or ""),
                "ultimo_valor": latest["valor"] if latest else None,
                "ultimo_periodo": latest["periodo"] if latest else "",
                "ultima_medicion": latest["created_at"] if latest else "",
                "status": status,
            })
        return JSONResponse({"success": True, "total": len(data), "data": data})
    finally:
        db.close()


def kpis_mediciones_list(request: Request):
    _bind_core_symbols()
    kpi_id_raw = request.query_params.get("kpi_id", "")
    db = SessionLocal()
    try:
        tenant_id = _current_tenant_id(request)
        _ensure_kpi_mediciones_table(db)
        if kpi_id_raw:
            rows = db.execute(text("""
                SELECT id, kpi_id, valor, periodo, notas, created_at, created_by
                FROM kpi_mediciones WHERE tenant_id = :tenant_id AND kpi_id = :kid
                ORDER BY created_at DESC LIMIT 200
            """), {"tenant_id": tenant_id, "kid": int(kpi_id_raw)}).fetchall()
        else:
            rows = db.execute(text("""
                SELECT id, kpi_id, valor, periodo, notas, created_at, created_by
                FROM kpi_mediciones
                WHERE tenant_id = :tenant_id
                ORDER BY created_at DESC LIMIT 500
            """), {"tenant_id": tenant_id}).fetchall()
        data = [
            {
                "id": int(r[0]), "kpi_id": int(r[1]), "valor": float(r[2]),
                "periodo": str(r[3] or ""), "notas": str(r[4] or ""),
                "created_at": str(r[5] or ""), "created_by": str(r[6] or ""),
            }
            for r in rows
        ]
        return JSONResponse({"success": True, "total": len(data), "data": data})
    finally:
        db.close()


def kpis_estadisticas(request: Request):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        tenant_id = _current_tenant_id(request)
        _ensure_kpi_mediciones_table(db)
        rows = db.execute(text("""
            SELECT m.kpi_id, m.valor, m.periodo, m.created_at,
                   k.nombre AS kpi_nombre, 'mayor' AS estandar, k.estandar_meta AS referencia
            FROM kpi_mediciones m
            LEFT JOIN brujula_indicator_definitions k ON k.id = m.kpi_id
            WHERE m.tenant_id = :tenant_id
            ORDER BY m.kpi_id, m.created_at ASC
        """), {"tenant_id": tenant_id}).fetchall()
    finally:
        db.close()

    if not rows:
        return JSONResponse({"success": True, "total_kpis": 0, "data": []})

    df = pd.DataFrame([
        {
            "kpi_id": int(r[0]),
            "valor": float(r[1]),
            "periodo": str(r[2] or ""),
            "created_at": str(r[3] or ""),
            "nombre": str(r[4] or ""),
            "estandar": str(r[5] or ""),
            "referencia": str(r[6] or ""),
        }
        for r in rows
    ])

    result = []
    for kpi_id, group in df.groupby("kpi_id"):
        vals = group["valor"].values
        n = int(len(vals))
        nombre = group["nombre"].iloc[0]
        estandar = group["estandar"].iloc[0]
        referencia = group["referencia"].iloc[0]
        slope = float(np.polyfit(range(n), vals, 1)[0]) if n >= 2 else 0.0
        trend_label = "subiendo" if abs(slope) >= 0.5 and slope > 0 else ("bajando" if abs(slope) >= 0.5 else "estable")
        result.append({
            "kpi_id": int(kpi_id),
            "nombre": nombre,
            "estandar": estandar,
            "referencia": referencia,
            "n_mediciones": n,
            "media": round(float(vals.mean()), 4),
            "minimo": round(float(vals.min()), 4),
            "maximo": round(float(vals.max()), 4),
            "desv_std": round(float(vals.std()) if n > 1 else 0.0, 4),
            "ultimo_valor": round(float(vals[-1]), 4),
            "tendencia_pendiente": round(slope, 4),
            "tendencia": trend_label,
        })

    return JSONResponse({"success": True, "total_kpis": len(result), "data": result})


def kpi_medicion_save(request: Request, data: dict = Body(default={})):
    _bind_core_symbols()
    kpi_id_raw = data.get("kpi_id")
    valor_raw = data.get("valor")
    periodo = str(data.get("periodo") or "").strip()
    notas = str(data.get("notas") or "").strip()
    try:
        kpi_id = int(kpi_id_raw)
        valor = float(str(valor_raw).replace(",", ".").replace("%", "").strip())
    except (TypeError, ValueError):
        return JSONResponse({"success": False, "error": "kpi_id y valor son requeridos"}, status_code=400)
    db = SessionLocal()
    try:
        tenant_id = _current_tenant_id(request)
        _ensure_kpi_mediciones_table(db)
        created_by = str(
            getattr(request.state, "user_name", None)
            or request.cookies.get("user_name")
            or ""
        ).strip()
        db.execute(text("""
            INSERT INTO kpi_mediciones (tenant_id, kpi_id, valor, periodo, notas, created_at, created_by)
            VALUES (:tenant_id, :kpi_id, :valor, :periodo, :notas, :now, :by)
        """), {
            "tenant_id": tenant_id,
            "kpi_id": kpi_id, "valor": valor, "periodo": periodo,
            "notas": notas, "now": datetime.utcnow().isoformat(), "by": created_by,
        })
        db.commit()
        return JSONResponse({"success": True})
    except Exception as exc:
        db.rollback()
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)
    finally:
        db.close()


def kpi_medicion_delete(medicion_id: int, request: Request):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        tenant_id = _current_tenant_id(request)
        _ensure_kpi_mediciones_table(db)
        db.execute(text("DELETE FROM kpi_mediciones WHERE id = :mid AND tenant_id = :tenant_id"), {"mid": medicion_id, "tenant_id": tenant_id})
        db.commit()
        return JSONResponse({"success": True})
    except Exception as exc:
        db.rollback()
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)
    finally:
        db.close()

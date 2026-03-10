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
    "linea_base",
    "estandar_meta",
    "categoria",
    "perspectiva",
    "semaforo_rojo",
    "semaforo_verde",
]


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
            "linea_base": "50000",
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
            "linea_base": "82",
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
        "linea_base": _csv_field(row, "linea_base"),
        "estandar_meta": _csv_field(row, "estandar_meta"),
        "categoria": _csv_field(row, "categoria"),
        "perspectiva": _csv_field(row, "perspectiva"),
        "semaforo_rojo": _csv_field(row, "semaforo_rojo"),
        "semaforo_verde": _csv_field(row, "semaforo_verde"),
    }


async def import_kpis_template(file: UploadFile = File(...)):
    from fastapi_modulo.modulos.planificacion.plan_estrategico_service import _ensure_axis_kpi_table

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

    required_headers = ["axis_codigo", "kpi_nombre"]
    missing_headers = [header for header in required_headers if header not in reader.fieldnames]
    if missing_headers:
        return JSONResponse(
            {"success": False, "error": f"Faltan columnas obligatorias: {', '.join(missing_headers)}"},
            status_code=400,
        )

    db = SessionLocal()
    summary = {"created": 0, "updated": 0, "skipped": 0, "errors": []}
    try:
        try:
            bind = db.get_bind()
            if bind is not None:
                from fastapi_modulo import main as core

                core.StrategicAxisConfig.__table__.create(bind=bind, checkfirst=True)
        except Exception:
            pass
        _ensure_axis_kpi_table(db)
        db.commit()

        axis_rows = db.execute(text("SELECT id, codigo, nombre FROM strategic_axes_config")).fetchall()
        axis_by_code = {
            str(row[1] or "").strip().lower(): {
                "id": int(row[0] or 0),
                "codigo": str(row[1] or "").strip(),
                "nombre": str(row[2] or "").strip(),
            }
            for row in axis_rows
            if str(row[1] or "").strip()
        }

        existing_rows = db.execute(
            text(
                """
                SELECT id, axis_id, nombre
                FROM strategic_axis_kpis
                ORDER BY axis_id ASC, orden ASC, id ASC
                """
            )
        ).fetchall()
        existing_by_axis_and_name = {
            (int(row[1] or 0), str(row[2] or "").strip().lower()): int(row[0] or 0)
            for row in existing_rows
            if int(row[1] or 0) > 0 and str(row[2] or "").strip()
        }
        order_by_axis = {}
        for row in existing_rows:
            axis_id = int(row[1] or 0)
            if axis_id <= 0:
                continue
            order_by_axis[axis_id] = order_by_axis.get(axis_id, 0) + 1

        for row_index, row in enumerate(reader, start=2):
            try:
                axis_code = _csv_field(row, "axis_codigo").lower()
                axis_name = _csv_field(row, "axis_nombre")
                if not axis_code:
                    raise ValueError("axis_codigo es obligatorio")
                if axis_code not in axis_by_code:
                    raise ValueError(f"Eje no encontrado para axis_codigo '{axis_code}'")
                payload = _normalize_import_kpi_row(row)
                if not payload["nombre"]:
                    raise ValueError("kpi_nombre es obligatorio")
                axis = axis_by_code[axis_code]
                axis_id = int(axis["id"])
                existing_id = existing_by_axis_and_name.get((axis_id, payload["nombre"].lower()))
                if existing_id:
                    db.execute(
                        text(
                            """
                            UPDATE strategic_axis_kpis
                            SET nombre = :nombre,
                                descripcion = :descripcion,
                                objetivo = :objetivo,
                                formula = :formula,
                                responsable = :responsable,
                                fuente_datos = :fuente_datos,
                                unidad = :unidad,
                                frecuencia = :frecuencia,
                                linea_base = :linea_base,
                                estandar_meta = :estandar_meta,
                                semaforo_rojo = :semaforo_rojo,
                                semaforo_verde = :semaforo_verde,
                                categoria = :categoria,
                                perspectiva = :perspectiva
                            WHERE id = :id
                            """
                        ),
                        {**payload, "id": existing_id},
                    )
                    summary["updated"] += 1
                else:
                    next_order = int(order_by_axis.get(axis_id, 0)) + 1
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
                        {**payload, "axis_id": axis_id, "orden": next_order},
                    )
                    inserted_id_row = db.execute(text("SELECT last_insert_rowid()")).fetchone()
                    inserted_id = int(inserted_id_row[0] or 0) if inserted_id_row else 0
                    order_by_axis[axis_id] = next_order
                    existing_by_axis_and_name[(axis_id, payload["nombre"].lower())] = inserted_id
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
    try:
        globals()["_ensure_objective_kpi_table"] = getattr(core, "_ensure_objective_kpi_table")
    except AttributeError:
        from fastapi_modulo.modulos.planificacion.plan_estrategico_service import _ensure_objective_kpi_table as ensure_objective_kpi_table

        globals()["_ensure_objective_kpi_table"] = ensure_objective_kpi_table
    _CORE_BOUND = True


def _ensure_kpi_mediciones_table(db) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS kpi_mediciones (
            id          INTEGER  PRIMARY KEY AUTOINCREMENT,
            kpi_id      INTEGER  NOT NULL,
            valor       REAL     NOT NULL,
            periodo     VARCHAR(50)  NOT NULL DEFAULT '',
            notas       TEXT         NOT NULL DEFAULT '',
            created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL DEFAULT ''
        )
    """))
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
        _ensure_objective_kpi_table(db)
        _ensure_kpi_mediciones_table(db)
        rows = db.execute(text("""
            SELECT
                k.id, k.objective_id, k.nombre, k.proposito, k.formula,
                k.periodicidad, k.estandar, k.referencia, k.orden,
                o.nombre   AS obj_nombre,
                o.codigo   AS obj_codigo,
                a.nombre   AS axis_nombre,
                a.codigo   AS axis_codigo
            FROM strategic_objective_kpis k
            LEFT JOIN strategic_objective_configs o ON o.id = k.objective_id
            LEFT JOIN strategic_axis_configs a ON a.id = o.axis_id
            ORDER BY a.codigo ASC, o.codigo ASC, k.orden ASC, k.id ASC
        """)).fetchall()
        kpi_ids = [int(r[0]) for r in rows]
        latest_by_kpi = {}
        if kpi_ids:
            placeholders = ", ".join(f":k{i}" for i in range(len(kpi_ids)))
            params = {f"k{i}": v for i, v in enumerate(kpi_ids)}
            meds = db.execute(text(f"""
                SELECT kpi_id, valor, periodo, created_at
                FROM kpi_mediciones
                WHERE kpi_id IN ({placeholders})
                ORDER BY created_at DESC
            """), params).fetchall()
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
            estandar = str(r[6] or "")
            referencia = str(r[7] or "")
            status = _kpi_evaluate_status(latest["valor"], estandar, referencia) if latest else "sin_medicion"
            data.append({
                "id": kpi_id,
                "objective_id": int(r[1] or 0),
                "nombre": str(r[2] or ""),
                "proposito": str(r[3] or ""),
                "formula": str(r[4] or ""),
                "periodicidad": str(r[5] or ""),
                "estandar": estandar,
                "referencia": referencia,
                "orden": int(r[8] or 0),
                "obj_nombre": str(r[9] or ""),
                "obj_codigo": str(r[10] or ""),
                "axis_nombre": str(r[11] or ""),
                "axis_codigo": str(r[12] or ""),
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
        _ensure_kpi_mediciones_table(db)
        if kpi_id_raw:
            rows = db.execute(text("""
                SELECT id, kpi_id, valor, periodo, notas, created_at, created_by
                FROM kpi_mediciones WHERE kpi_id = :kid
                ORDER BY created_at DESC LIMIT 200
            """), {"kid": int(kpi_id_raw)}).fetchall()
        else:
            rows = db.execute(text("""
                SELECT id, kpi_id, valor, periodo, notas, created_at, created_by
                FROM kpi_mediciones
                ORDER BY created_at DESC LIMIT 500
            """)).fetchall()
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
        _ensure_kpi_mediciones_table(db)
        rows = db.execute(text("""
            SELECT m.kpi_id, m.valor, m.periodo, m.created_at,
                   k.nombre AS kpi_nombre, k.estandar, k.referencia
            FROM kpi_mediciones m
            LEFT JOIN strategic_objective_kpis k ON k.id = m.kpi_id
            ORDER BY m.kpi_id, m.created_at ASC
        """)).fetchall()
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
        _ensure_kpi_mediciones_table(db)
        created_by = str(
            getattr(request.state, "user_name", None)
            or request.cookies.get("user_name")
            or ""
        ).strip()
        db.execute(text("""
            INSERT INTO kpi_mediciones (kpi_id, valor, periodo, notas, created_at, created_by)
            VALUES (:kpi_id, :valor, :periodo, :notas, :now, :by)
        """), {
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
        _ensure_kpi_mediciones_table(db)
        db.execute(text("DELETE FROM kpi_mediciones WHERE id = :mid"), {"mid": medicion_id})
        db.commit()
        return JSONResponse({"success": True})
    except Exception as exc:
        db.rollback()
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)
    finally:
        db.close()

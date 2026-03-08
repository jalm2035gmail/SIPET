from __future__ import annotations

from datetime import datetime
import re

from fastapi import Body, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
import pandas as pd
import numpy as np

_CORE_BOUND = False


def _bind_core_symbols() -> None:
    global _CORE_BOUND
    if _CORE_BOUND:
        return
    from fastapi_modulo import main as core

    names = [
        "SessionLocal",
        "_ensure_objective_kpi_table",
    ]
    for name in names:
        globals()[name] = getattr(core, name)
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

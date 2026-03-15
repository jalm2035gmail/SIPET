"""Módulo de Análisis Predictivo — SIPET Fase 2.

Implementa:
  - Scoring de Engagement de Usuarios (0-100)
  - Detección de Riesgo de Inactividad (Churn interno)
  - Resumen de Riesgo KPI (basado en mediciones reales)
  - Resumen de Riesgo de Actividades POA
  - Infraestructura para futuro modelo ML (scikit-learn)
  - Dashboard consolidado en /ia/predictivo
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from html import escape
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, Body, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import text

router = APIRouter()

PREDICTIVO_TEMPLATE_PATH = os.path.join(
    "fastapi_modulo", "modulos", "ia", "vistas", "predictivo.html"
)

# ── Tabla de resultados de scoring ───────────────────────────────────────────

_SCORING_DDL = """
CREATE TABLE IF NOT EXISTS ia_scoring_results (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at      TEXT NOT NULL,
    scope       TEXT NOT NULL,
    entity_id   TEXT,
    entity_type TEXT,
    score       REAL,
    risk_level  TEXT,
    details     TEXT,
    run_by      TEXT
);
"""


def _ensure_scoring_table(db) -> None:
    try:
        db.execute(text(_SCORING_DDL))
        db.commit()
    except Exception:
        db.rollback()


# ── Scoring helpers ───────────────────────────────────────────────────────────

def _recency_score(last_used_at_str: Optional[str]) -> int:
    """0-50 puntos según antigüedad del último acceso."""
    if not last_used_at_str:
        return 0
    try:
        last = datetime.fromisoformat(last_used_at_str.replace("Z", "+00:00").replace("+00:00", ""))
        days_ago = (datetime.utcnow() - last).days
        if days_ago <= 7:
            return 50
        if days_ago <= 30:
            return 35
        if days_ago <= 90:
            return 15
        return 0
    except Exception:
        return 0


def _frequency_score(use_count: Optional[int]) -> int:
    """0-25 puntos según cantidad de sesiones."""
    n = int(use_count or 0)
    if n >= 100:
        return 25
    if n >= 50:
        return 20
    if n >= 20:
        return 15
    if n >= 5:
        return 8
    if n >= 1:
        return 3
    return 0


def _ia_adoption_score(interactions: int) -> int:
    """0-25 puntos según interacciones IA en los últimos 90 días."""
    n = int(interactions or 0)
    if n >= 20:
        return 25
    if n >= 10:
        return 20
    if n >= 5:
        return 15
    if n >= 1:
        return 8
    return 0


def _risk_level(score: int) -> str:
    if score >= 70:
        return "bajo"
    if score >= 40:
        return "medio"
    return "alto"


def _risk_badge_class(level: str) -> str:
    return {"bajo": "badge-success", "medio": "badge-warning", "alto": "badge-error"}.get(level, "badge-ghost")


def _risk_icon(level: str) -> str:
    return {"bajo": "🟢", "medio": "🟡", "alto": "🔴"}.get(level, "⚪")


# ── Cómputo de engagement de usuarios ────────────────────────────────────────

def _compute_user_scores(db) -> List[Dict]:
    """Calcula score de engagement para cada usuario activo."""
    users_raw = db.execute(text(
        "SELECT id, username, full_name, email, is_active FROM users ORDER BY id"
    )).fetchall()

    cutoff_90 = (datetime.utcnow() - timedelta(days=90)).isoformat()

    results = []
    for u in users_raw:
        uid, uname, full_name, email, is_active = u[0], u[1], u[2], u[3], u[4]

        # Recency + frequency desde tokens (mejor sesión activa para este usuario)
        tok = db.execute(text(
            "SELECT MAX(last_used_at), SUM(use_count) FROM tokens "
            "WHERE user_id = :uid AND revoked = 0"
        ), {"uid": uid}).fetchone()
        last_used = tok[0] if tok else None
        use_count = int(tok[1] or 0) if tok else 0

        # IA interactions últimos 90 días
        ia_count = db.execute(text(
            "SELECT COUNT(*) FROM ia_interactions "
            "WHERE user_id = :uid AND created_at >= :cutoff AND status = 'success'"
        ), {"uid": uid, "cutoff": cutoff_90}).fetchone()
        ia_n = int((ia_count[0] if ia_count else 0) or 0)

        r_score = _recency_score(last_used)
        f_score = _frequency_score(use_count)
        a_score = _ia_adoption_score(ia_n)
        total = r_score + f_score + a_score
        level = _risk_level(total)

        results.append({
            "user_id": uid,
            "username": uname or email or str(uid),
            "full_name": full_name or uname or "",
            "is_active": bool(is_active),
            "score": total,
            "risk_level": level,
            "r_score": r_score,
            "f_score": f_score,
            "a_score": a_score,
            "last_used": last_used,
            "use_count": use_count,
            "ia_interactions": ia_n,
        })

    results.sort(key=lambda x: x["score"])

    # Percentil de engagement: qué fracción de usuarios tiene score menor
    if results:
        scores_series = pd.Series([r["score"] for r in results])
        pcts = scores_series.rank(pct=True, method="min")
        for r, pct in zip(results, pcts):
            r["percentil"] = round(float(pct) * 100, 1)

    return results


# ── Resumen de riesgo por KPI ─────────────────────────────────────────────────

def _compute_kpi_risk_summary(db) -> Dict:
    """Cuenta KPIs por estado usando la tabla kpi_mediciones."""
    total = ok = warning = alert = sin_meta = 0

    try:
        # Traer últimas mediciones por KPI junto con definición
        rows = db.execute(text("""
            SELECT k.id, k.nombre, k.estandar, k.referencia,
                   m.valor
            FROM strategic_objective_kpis k
            LEFT JOIN (
                SELECT kpi_id, valor,
                       ROW_NUMBER() OVER (PARTITION BY kpi_id ORDER BY created_at DESC) rn
                FROM kpi_mediciones
            ) m ON m.kpi_id = k.id AND m.rn = 1
        """)).fetchall()

        from fastapi_modulo.modulos.planificacion.modelos.kpis_service import _kpi_evaluate_status

        at_risk = []
        for row in rows:
            kpi_id, nombre, estandar, referencia, valor = row
            total += 1
            if valor is None:
                sin_meta += 1
                continue
            status = _kpi_evaluate_status(float(valor), estandar or "", referencia or "")
            if status == "ok":
                ok += 1
            elif status == "warning":
                warning += 1
                at_risk.append({"kpi_id": kpi_id, "nombre": nombre, "status": status, "valor": valor})
            elif status == "alert":
                alert += 1
                at_risk.append({"kpi_id": kpi_id, "nombre": nombre, "status": status, "valor": valor})
            else:
                sin_meta += 1

        # Enriquecer at_risk con estadísticas de tendencia usando pandas
        if at_risk:
            risk_ids = [r["kpi_id"] for r in at_risk if r.get("kpi_id") is not None]
            if risk_ids:
                placeholders = ", ".join(f":k{i}" for i in range(len(risk_ids)))
                params: Dict[str, Any] = {f"k{i}": v for i, v in enumerate(risk_ids)}
                med_rows = db.execute(text(f"""
                    SELECT kpi_id, valor FROM kpi_mediciones
                    WHERE kpi_id IN ({placeholders})
                    ORDER BY kpi_id, created_at ASC
                """), params).fetchall()
                if med_rows:
                    mdf = pd.DataFrame(med_rows, columns=["kpi_id", "valor"])
                    mdf["valor"] = pd.to_numeric(mdf["valor"], errors="coerce")
                    trend_map: Dict[int, Dict] = {}
                    for kid, grp in mdf.groupby("kpi_id"):
                        vals = grp["valor"].dropna().values
                        n = len(vals)
                        slope = float(np.polyfit(range(n), vals, 1)[0]) if n >= 2 else 0.0
                        trend_map[int(kid)] = {
                            "n_mediciones": n,
                            "media": round(float(vals.mean()), 3),
                            "tendencia": "subiendo" if slope > 0.5 else ("bajando" if slope < -0.5 else "estable"),
                            "tendencia_pendiente": round(slope, 3),
                        }
                    for item in at_risk:
                        item.update(trend_map.get(item.get("kpi_id", -1), {}))

    except Exception as exc:
        return {
            "total": 0, "ok": 0, "warning": 0, "alert": 0, "sin_meta": 0,
            "at_risk": [], "error": str(exc),
        }

    return {
        "total": total, "ok": ok, "warning": warning,
        "alert": alert, "sin_meta": sin_meta,
        "at_risk": at_risk,
    }


# ── Resumen de riesgo de actividades POA ─────────────────────────────────────

def _compute_poa_risk_summary(db) -> Dict:
    """Cuenta actividades por estado de retraso."""
    today = datetime.utcnow().date().isoformat()
    try:
        total = db.execute(text("SELECT COUNT(*) FROM poa_activities")).fetchone()[0]
        atrasadas = db.execute(text(
            "SELECT COUNT(*) FROM poa_activities "
            "WHERE fecha_final < :today AND (entrega_estado IS NULL OR entrega_estado != 'aprobada')"
        ), {"today": today}).fetchone()[0]
        por_vencer = db.execute(text(
            "SELECT COUNT(*) FROM poa_activities "
            "WHERE fecha_final >= :today AND fecha_final <= :next7 "
            "AND (entrega_estado IS NULL OR entrega_estado != 'aprobada')"
        ), {"today": today, "next7": (datetime.utcnow().date() + timedelta(days=7)).isoformat()}).fetchone()[0]
        completadas = db.execute(text(
            "SELECT COUNT(*) FROM poa_activities WHERE entrega_estado = 'aprobada'"
        )).fetchone()[0]
        return {
            "total": int(total or 0),
            "completadas": int(completadas or 0),
            "atrasadas": int(atrasadas or 0),
            "por_vencer": int(por_vencer or 0),
            "en_tiempo": max(0, int((total or 0) - (atrasadas or 0) - (completadas or 0))),
        }
    except Exception as exc:
        return {"total": 0, "completadas": 0, "atrasadas": 0, "por_vencer": 0, "en_tiempo": 0, "error": str(exc)}


# ── Endpoint: Dashboard ───────────────────────────────────────────────────────

@router.get("/api/ia/predictivo/dashboard")
def ia_predictivo_dashboard(request: Request):
    from fastapi_modulo.db import SessionLocal
    db = SessionLocal()
    try:
        _ensure_scoring_table(db)
        user_scores = _compute_user_scores(db)
        kpi_risk = _compute_kpi_risk_summary(db)
        poa_risk = _compute_poa_risk_summary(db)

        total_users = len(user_scores)
        at_risk_users = [u for u in user_scores if u["risk_level"] == "alto"]
        medio_users = [u for u in user_scores if u["risk_level"] == "medio"]
        bajo_users = [u for u in user_scores if u["risk_level"] == "bajo"]

        risk_score_global = 0
        if total_users > 0:
            avg_engagement = sum(u["score"] for u in user_scores) / total_users
            risk_score_global = max(0, 100 - int(avg_engagement))

        return JSONResponse({
            "success": True,
            "run_at": datetime.utcnow().isoformat(),
            "engagement": {
                "total_users": total_users,
                "alto_riesgo": len(at_risk_users),
                "riesgo_medio": len(medio_users),
                "bajo_riesgo": len(bajo_users),
                "avg_score": round(sum(u["score"] for u in user_scores) / max(total_users, 1), 1),
                "risk_score_global": risk_score_global,
            },
            "kpis": kpi_risk,
            "actividades_poa": poa_risk,
        })
    finally:
        db.close()


# ── Endpoint: Usuarios ────────────────────────────────────────────────────────

@router.get("/api/ia/predictivo/usuarios")
def ia_predictivo_usuarios(request: Request):
    from fastapi_modulo.db import SessionLocal
    db = SessionLocal()
    try:
        _ensure_scoring_table(db)
        scores = _compute_user_scores(db)
        return JSONResponse({"success": True, "items": scores})
    finally:
        db.close()


# ── Endpoint: KPIs riesgo ─────────────────────────────────────────────────────

@router.get("/api/ia/predictivo/kpis-riesgo")
def ia_predictivo_kpis_riesgo(request: Request):
    from fastapi_modulo.db import SessionLocal
    db = SessionLocal()
    try:
        return JSONResponse({"success": True, **_compute_kpi_risk_summary(db)})
    finally:
        db.close()


# ── Endpoint: Recalcular y persistir ─────────────────────────────────────────

@router.post("/api/ia/predictivo/recalcular")
def ia_predictivo_recalcular(request: Request):
    from fastapi_modulo.db import SessionLocal
    db = SessionLocal()
    try:
        _ensure_scoring_table(db)
        scores = _compute_user_scores(db)
        kpi_risk = _compute_kpi_risk_summary(db)
        poa_risk = _compute_poa_risk_summary(db)
        run_at = datetime.utcnow().isoformat()
        run_by = str(getattr(request.state, "user_name", None) or "system").strip()

        # Persiste resultados de usuarios
        for u in scores:
            db.execute(text("""
                INSERT INTO ia_scoring_results
                    (run_at, scope, entity_id, entity_type, score, risk_level, details, run_by)
                VALUES (:run_at, 'engagement', :eid, 'user', :score, :risk_level, :details, :run_by)
            """), {
                "run_at": run_at,
                "eid": str(u["user_id"]),
                "score": u["score"],
                "risk_level": u["risk_level"],
                "details": json.dumps({
                    "r_score": u["r_score"], "f_score": u["f_score"],
                    "a_score": u["a_score"], "ia_interactions": u["ia_interactions"],
                }),
                "run_by": run_by,
            })

        # Persiste resumen KPI
        db.execute(text("""
            INSERT INTO ia_scoring_results
                (run_at, scope, entity_id, entity_type, score, risk_level, details, run_by)
            VALUES (:run_at, 'kpi_risk', 'aggregate', 'kpi_summary', :score, :risk_level, :details, :run_by)
        """), {
            "run_at": run_at,
            "score": kpi_risk.get("alert", 0) * 100 + kpi_risk.get("warning", 0) * 50,
            "risk_level": "alto" if kpi_risk.get("alert", 0) > 0 else (
                "medio" if kpi_risk.get("warning", 0) > 0 else "bajo"
            ),
            "details": json.dumps(kpi_risk),
            "run_by": run_by,
        })

        db.commit()
        return JSONResponse({
            "success": True,
            "run_at": run_at,
            "users_scored": len(scores),
            "kpis_evaluated": kpi_risk.get("total", 0),
            "activities_evaluated": poa_risk.get("total", 0),
        })
    except Exception as exc:
        db.rollback()
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)
    finally:
        db.close()


# ── Endpoint: Historial de scoring ───────────────────────────────────────────

@router.get("/api/ia/predictivo/historial")
def ia_predictivo_historial(request: Request):
    from fastapi_modulo.db import SessionLocal
    db = SessionLocal()
    try:
        _ensure_scoring_table(db)
        rows = db.execute(text(
            "SELECT run_at, scope, COUNT(*) as n, run_by "
            "FROM ia_scoring_results "
            "GROUP BY run_at, scope, run_by "
            "ORDER BY run_at DESC LIMIT 30"
        )).fetchall()
        items = [{"run_at": r[0], "scope": r[1], "count": r[2], "run_by": r[3]} for r in rows]
        return JSONResponse({"success": True, "items": items})
    finally:
        db.close()


# ── Página HTML ───────────────────────────────────────────────────────────────

def _load_predictivo_template() -> str:
    try:
        with open(PREDICTIVO_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return "<p>No se pudo cargar la vista predictiva.</p>"


@router.get("/ia/predictivo", response_class=HTMLResponse)
def ia_predictivo_page(request: Request):
    from fastapi_modulo.main import render_backend_page
    return render_backend_page(
        request,
        title="Análisis Predictivo",
        description="Scoring de engagement, riesgo KPI y riesgo de actividades.",
        content=_load_predictivo_template(),
        hide_floating_actions=True,
        show_page_header=False,
    )

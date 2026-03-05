"""
Módulo IA para SIPET

Este archivo implementa la lógica inicial para las funcionalidades de IA descritas en el documento funcional.
"""

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi import Body
from fastsipet_modulo.modulos.ia.ia_service import complete_with_fallback
from fastapi_modulo.db import SessionLocal, IAInteraction, IASuggestionDraft, IAFeatureFlag, IAJob
from datetime import datetime, timedelta
from fastapi.templating import Jinja2Templates
import re
import unicodedata
import json
import os
import math
import hashlib
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import text

router = APIRouter()
templates = Jinja2Templates(directory="fastsipet_modulo/modulos/ia")
_IA_JOB_EXECUTOR = ThreadPoolExecutor(max_workers=max(2, int(os.environ.get("IA_JOB_WORKERS", "4"))))
_RAG_MESSAGE_RETENTION_DAYS = max(1, int(os.environ.get("RAG_MESSAGE_RETENTION_DAYS", "2") or 2))
_BASE_IA_EXTRA_BLOCK = "base_ia_extra"
_BASE_IA_WEEKLY_META_BLOCK = "base_ia_weekly_meta"
_BASE_IA_WEEKLY_INTERVAL_DAYS = max(1, int(os.environ.get("BASE_IA_WEEKLY_INTERVAL_DAYS", "7") or 7))
_BASE_IA_CRON_LOCK = threading.Lock()

_POA_RISK_ALERTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ia_poa_risk_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    alert_key TEXT NOT NULL UNIQUE,
    activity_id INTEGER,
    objective_id INTEGER,
    axis_id INTEGER,
    severity TEXT NOT NULL,
    risk_score REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    owner TEXT DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    message TEXT NOT NULL DEFAULT '',
    recommendation TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'ia_risk_engine',
    resolved_at TEXT DEFAULT ''
);
"""

_IA_EXEC_REPORTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ia_executive_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    report_key TEXT NOT NULL,
    version_no INTEGER NOT NULL DEFAULT 1,
    title TEXT NOT NULL DEFAULT '',
    username TEXT DEFAULT '',
    role TEXT DEFAULT '',
    filters_json TEXT NOT NULL DEFAULT '{}',
    snapshot_json TEXT NOT NULL DEFAULT '{}',
    narrative_text TEXT NOT NULL DEFAULT '',
    model_name TEXT DEFAULT '',
    provider TEXT DEFAULT ''
);
"""

_IA_RAG_DOCUMENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ia_rag_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_doc_id INTEGER NOT NULL UNIQUE,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    estado TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    file_path TEXT NOT NULL DEFAULT '',
    creado_por TEXT NOT NULL DEFAULT '',
    enviado_por TEXT NOT NULL DEFAULT '',
    autorizado_por TEXT NOT NULL DEFAULT '',
    actualizado_por TEXT NOT NULL DEFAULT '',
    source_updated_at TEXT NOT NULL DEFAULT '',
    source_hash TEXT NOT NULL DEFAULT '',
    chunk_count INTEGER NOT NULL DEFAULT 0,
    indexed_at TEXT NOT NULL
);
"""

_IA_RAG_CHUNKS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ia_rag_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rag_document_id INTEGER NOT NULL,
    source_doc_id INTEGER NOT NULL,
    chunk_order INTEGER NOT NULL DEFAULT 0,
    content TEXT NOT NULL DEFAULT '',
    token_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (rag_document_id) REFERENCES ia_rag_documents(id)
);
"""

_IA_RAG_MESSAGES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ia_rag_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    username TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL DEFAULT '',
    message_type TEXT NOT NULL DEFAULT 'user',
    message_text TEXT NOT NULL DEFAULT '',
    citations_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);
"""


def _ensure_poa_risk_alerts_table(db) -> None:
    db.execute(text(_POA_RISK_ALERTS_TABLE_SQL))
    db.commit()


def _ensure_exec_reports_table(db) -> None:
    db.execute(text(_IA_EXEC_REPORTS_TABLE_SQL))
    db.commit()


def _ensure_rag_tables(db) -> None:
    db.execute(text(_IA_RAG_DOCUMENTS_TABLE_SQL))
    db.execute(text(_IA_RAG_CHUNKS_TABLE_SQL))
    db.execute(text(_IA_RAG_MESSAGES_TABLE_SQL))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_ia_rag_documents_tenant ON ia_rag_documents(tenant_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_ia_rag_documents_source_doc ON ia_rag_documents(source_doc_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_ia_rag_chunks_doc ON ia_rag_chunks(source_doc_id, rag_document_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_ia_rag_messages_conv ON ia_rag_messages(conversation_id, created_at)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_ia_rag_messages_user ON ia_rag_messages(username, created_at)"))
    db.commit()


def _ensure_strategic_identity_table(db) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS strategic_identity_config (
              bloque VARCHAR(40) PRIMARY KEY,
              payload TEXT NOT NULL DEFAULT '[]',
              updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    db.commit()


def _get_identity_payload_map(db, blocks: list[str]) -> dict:
    wanted = [str(item or "").strip().lower() for item in (blocks or []) if str(item or "").strip()]
    if not wanted:
        return {}
    placeholders = ", ".join([f":b{i}" for i in range(len(wanted))])
    params = {f"b{i}": value for i, value in enumerate(wanted)}
    rows = db.execute(
        text(
            f"""
            SELECT bloque, payload
            FROM strategic_identity_config
            WHERE lower(COALESCE(bloque,'')) IN ({placeholders})
            """
        ),
        params,
    ).fetchall()
    return {str(row[0] or "").strip().lower(): str(row[1] or "") for row in rows}


def _upsert_identity_payload(db, block: str, payload: dict) -> None:
    name = str(block or "").strip().lower()
    encoded = json.dumps(payload or {}, ensure_ascii=False)
    db.execute(
        text(
            """
            INSERT INTO strategic_identity_config (bloque, payload, updated_at)
            VALUES (:bloque, :payload, CURRENT_TIMESTAMP)
            ON CONFLICT (bloque)
            DO UPDATE SET payload = EXCLUDED.payload, updated_at = CURRENT_TIMESTAMP
            """
        ),
        {"bloque": name, "payload": encoded},
    )


def _build_weekly_progress_snapshot(db) -> dict:
    dataset = _compute_executive_dataset(db, {})
    today_iso = datetime.utcnow().date().isoformat()
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "cutoff_date": today_iso,
        "axes": int(dataset.get("axes", 0) or 0),
        "objectives": int(dataset.get("objectives", 0) or 0),
        "activities": int(dataset.get("activities", 0) or 0),
        "completed_activities": int(dataset.get("completed_activities", 0) or 0),
        "overdue_activities": int(dataset.get("overdue_activities", 0) or 0),
        "avg_objective_progress": float(dataset.get("avg_objective_progress", 0) or 0.0),
        "risk_high": int(dataset.get("ia_risk_high_count", 0) or 0),
        "risk_medium": int(dataset.get("ia_risk_medium_count", 0) or 0),
        "risk_low": int(dataset.get("ia_risk_low_count", 0) or 0),
    }


def _generate_weekly_base_extra_text(db, strategic_chunks: list, progress: dict) -> str:
    context_lines = []
    for item in (strategic_chunks or [])[:8]:
        title = _norm_text(item.get("title")) or "Base estratégica"
        content = _norm_text(item.get("content"))
        if content:
            context_lines.append(f"{title}: {content[:1200]}")
    prompt = (
        "Genera un resumen ejecutivo semanal en español para una base de conocimiento IA institucional. "
        "Debe ser claro, accionable y útil para responder preguntas de estrategia y táctica. "
        "Formato: 1) Panorama general, 2) Avance y brechas, 3) Prioridades de la semana, 4) Riesgos y mitigación. "
        "Máximo 450 palabras.\n\n"
        f"Snapshot de avance: {json.dumps(progress or {}, ensure_ascii=False)}\n\n"
        "Contexto estratégico:\n"
        + "\n\n".join(context_lines)
    )
    try:
        generated = _extract_text_from_provider_result(complete_with_fallback(prompt)).strip()
    except Exception:
        generated = ""
    if generated:
        return generated[:7000]
    return (
        "Panorama general:\n"
        f"- Corte: {progress.get('cutoff_date', '')}\n"
        f"- Ejes: {progress.get('axes', 0)} · Objetivos: {progress.get('objectives', 0)} · Actividades: {progress.get('activities', 0)}\n\n"
        "Avance y brechas:\n"
        f"- Avance promedio: {float(progress.get('avg_objective_progress', 0.0)):.2f}%\n"
        f"- Actividades completadas: {progress.get('completed_activities', 0)}\n"
        f"- Actividades vencidas: {progress.get('overdue_activities', 0)}\n\n"
        "Riesgos:\n"
        f"- Riesgo alto: {progress.get('risk_high', 0)} · medio: {progress.get('risk_medium', 0)} · bajo: {progress.get('risk_low', 0)}\n"
    )


def _refresh_weekly_strategic_extra_if_due(db, force: bool = False) -> dict:
    with _BASE_IA_CRON_LOCK:
        _ensure_strategic_identity_table(db)
        payload_map = _get_identity_payload_map(db, [_BASE_IA_WEEKLY_META_BLOCK])
        meta = _safe_json_loads(payload_map.get(_BASE_IA_WEEKLY_META_BLOCK, "{}"), {})
        last_refresh_raw = _norm_text(meta.get("last_refresh_at"))
        now = datetime.utcnow()
        last_refresh_dt = None
        if last_refresh_raw:
            try:
                last_refresh_dt = datetime.fromisoformat(last_refresh_raw)
            except Exception:
                last_refresh_dt = None
        due = force or (last_refresh_dt is None) or ((now - last_refresh_dt) >= timedelta(days=_BASE_IA_WEEKLY_INTERVAL_DAYS))
        if not due:
            next_at = (last_refresh_dt + timedelta(days=_BASE_IA_WEEKLY_INTERVAL_DAYS)).isoformat() if last_refresh_dt else ""
            return {
                "updated": False,
                "reason": "not_due",
                "last_refresh_at": last_refresh_raw,
                "next_refresh_at": next_at,
                "interval_days": _BASE_IA_WEEKLY_INTERVAL_DAYS,
            }
        progress = _build_weekly_progress_snapshot(db)
        strategic_chunks = _retrieve_strategic_context(db, "estrategia avance riesgos prioridades", top_k=8, include_extra=False)
        new_text = _generate_weekly_base_extra_text(db, strategic_chunks, progress)
        _upsert_identity_payload(db, _BASE_IA_EXTRA_BLOCK, {"texto": new_text})
        next_at = (now + timedelta(days=_BASE_IA_WEEKLY_INTERVAL_DAYS)).isoformat()
        new_meta = {
            "last_refresh_at": now.isoformat(),
            "next_refresh_at": next_at,
            "interval_days": _BASE_IA_WEEKLY_INTERVAL_DAYS,
            "last_status": "ok",
            "last_error": "",
            "generated_chars": len(new_text),
            "progress_snapshot": progress,
        }
        _upsert_identity_payload(db, _BASE_IA_WEEKLY_META_BLOCK, new_meta)
        db.commit()
        return {
            "updated": True,
            "last_refresh_at": new_meta["last_refresh_at"],
            "next_refresh_at": next_at,
            "interval_days": _BASE_IA_WEEKLY_INTERVAL_DAYS,
            "generated_chars": len(new_text),
        }


def _purge_expired_rag_messages(db, retention_days: int = _RAG_MESSAGE_RETENTION_DAYS) -> int:
    safe_days = max(1, int(retention_days or 2))
    cutoff_iso = (datetime.utcnow() - timedelta(days=safe_days)).isoformat()
    result = db.execute(
        text(
            """
            DELETE FROM ia_rag_messages
            WHERE created_at < :cutoff_iso
            """
        ),
        {"cutoff_iso": cutoff_iso},
    )
    db.commit()
    return int(getattr(result, "rowcount", 0) or 0)


def _extract_text_from_provider_result(result):
    if isinstance(result, dict):
        if isinstance(result.get("response"), str):
            return result.get("response", "").strip()
        choices = result.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0] or {}
            if isinstance(first, dict):
                if isinstance(first.get("text"), str):
                    return first.get("text", "").strip()
                message = first.get("message")
                if isinstance(message, dict) and isinstance(message.get("content"), str):
                    return message.get("content", "").strip()
    return str(result or "").strip()


def _extract_completion_meta(result: dict) -> dict:
    if not isinstance(result, dict):
        return {"provider": "", "model": "", "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "cost_estimated": 0.0}
    usage = result.get("usage") if isinstance(result.get("usage"), dict) else {}
    return {
        "provider": str(result.get("provider") or ""),
        "model": str(result.get("model") or result.get("model_name") or ""),
        "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
        "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
        "total_tokens": int(usage.get("total_tokens", 0) or 0),
        "cost_estimated": float(result.get("cost_estimated", 0) or 0),
    }


def _normalize_role_name(role_name: str) -> str:
    role = str(role_name or "").strip().lower()
    role = unicodedata.normalize("NFKD", role)
    role = "".join(ch for ch in role if not unicodedata.combining(ch))
    role = re.sub(r"[^a-z0-9]+", "_", role).strip("_")
    if role in {"superadmin", "super_admin", "super_administrador", "superadministrador", "superadministrdor"}:
        return "superadministrador"
    if role in {"admin", "administrador", "administador", "administrdor", "admnistrador"}:
        return "administrador"
    if role in {"autoridad", "autoridades", "authority", "authorities"}:
        return "autoridades"
    if role in {"department_manager", "departamento", "strategic_manager"}:
        return "departamento"
    if role in {"usuario", "viewer", "collaborator", "team_leader"}:
        return "usuario"
    return role or "usuario"


def _current_role(request: Request) -> str:
    role = getattr(request.state, "user_role", None)
    if role is None:
        role = request.cookies.get("user_role") or ""
    return _normalize_role_name(str(role or ""))


def _resolve_ia_feature_enabled(db, *, role: str, feature_key: str, module: str = "") -> bool:
    key = str(feature_key or "").strip().lower()
    mod = str(module or "").strip().lower()
    if not key:
        return True
    IAFeatureFlag.__table__.create(bind=db.get_bind(), checkfirst=True)
    rows = (
        db.query(IAFeatureFlag)
        .filter(IAFeatureFlag.feature_key == key)
        .all()
    )
    if not rows:
        return True
    normalized_role = _normalize_role_name(role)
    candidates = []
    for row in rows:
        row_role = _normalize_role_name(str(row.role or "").strip()) if row.role else ""
        row_mod = str(row.module or "").strip().lower()
        role_match = (not row_role) or (row_role == normalized_role)
        module_match = (not row_mod) or (row_mod == mod)
        if role_match and module_match:
            specificity = (2 if row_role else 0) + (1 if row_mod else 0)
            updated_rank = row.updated_at.timestamp() if row.updated_at else 0
            candidates.append((specificity, updated_rank, row))
    if not candidates:
        return True
    candidates.sort(key=lambda item: (item[0], item[1], int(item[2].id or 0)), reverse=True)
    winner = candidates[0][2]
    return bool(int(getattr(winner, "enabled", 1) or 0))


def _require_ia_feature(request: Request, db, *, feature_key: str, module: str = ""):
    role = _current_role(request)
    allowed = _resolve_ia_feature_enabled(db, role=role, feature_key=feature_key, module=module)
    if not allowed:
        raise PermissionError("Funcionalidad IA no habilitada para tu rol/módulo.")


def _is_admin_like(request: Request) -> bool:
    return _current_role(request) in {"superadministrador", "administrador"}


def _current_username(request: Request) -> str:
    username = getattr(request.state, "user_name", None)
    if username is None:
        username = request.cookies.get("user_name") or ""
    return str(username or "").strip()


def _json_load(value):
    raw = str(value or "").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _serialize_job(row: IAJob) -> dict:
    return {
        "id": int(row.id or 0),
        "status": str(row.status or "pending"),
        "progress": int(row.progress or 0),
        "job_type": str(row.job_type or ""),
        "feature_key": str(row.feature_key or ""),
        "module": str(row.module or ""),
        "queue": str(row.queue or "default"),
        "attempts": int(row.attempts or 0),
        "max_attempts": int(row.max_attempts or 1),
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "started_at": row.started_at.isoformat() if row.started_at else "",
        "finished_at": row.finished_at.isoformat() if row.finished_at else "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
        "username": str(row.username or ""),
        "role": str(row.role or ""),
        "provider": str(row.provider or ""),
        "model_name": str(row.model_name or ""),
        "input": _json_load(row.input_payload),
        "output": _json_load(row.output_payload),
        "error_message": str(row.error_message or ""),
    }


def _run_ia_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        IAJob.__table__.create(bind=db.get_bind(), checkfirst=True)
        IAInteraction.__table__.create(bind=db.get_bind(), checkfirst=True)
        job = db.query(IAJob).filter(IAJob.id == int(job_id)).first()
        if not job:
            return
        if str(job.status or "").lower() in {"completed", "canceled"}:
            return
        if str(job.status or "").lower() == "in_progress":
            return
        job.status = "in_progress"
        job.progress = 10
        job.started_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        job.attempts = int(job.attempts or 0) + 1
        db.add(job)
        db.commit()

        payload = _json_load(job.input_payload)
        prompt = str(payload.get("prompt", "") or payload.get("texto", "")).strip()
        if not prompt:
            raise RuntimeError("Prompt vacío para job IA.")

        interaction = IAInteraction(
            created_at=datetime.utcnow(),
            user_id=str(job.user_id or "") or None,
            username=str(job.username or "") or None,
            feature_key=str(job.feature_key or "suggest_objective_text"),
            input_payload=prompt,
            status="started",
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)

        job.progress = 40
        db.add(job)
        db.commit()

        result = complete_with_fallback(prompt)
        text_out = _extract_text_from_provider_result(result).strip()
        if not text_out:
            raise RuntimeError("La IA no devolvió contenido.")
        meta = _extract_completion_meta(result)

        interaction.output_payload = text_out
        interaction.model_name = meta["model"]
        interaction.tokens_in = meta["prompt_tokens"]
        interaction.tokens_out = meta["completion_tokens"]
        interaction.estimated_cost = str(meta["cost_estimated"])
        interaction.status = "success"
        db.add(interaction)

        out_payload = {
            "result_text": text_out,
            "job_type": str(job.job_type or ""),
            "provider": meta["provider"],
            "model": meta["model"],
            "usage": {
                "prompt_tokens": meta["prompt_tokens"],
                "completion_tokens": meta["completion_tokens"],
                "total_tokens": meta["total_tokens"],
            },
            "cost_estimated": meta["cost_estimated"],
        }
        job.output_payload = json.dumps(out_payload, ensure_ascii=False)
        job.provider = meta["provider"]
        job.model_name = meta["model"]
        job.status = "completed"
        job.progress = 100
        job.error_message = ""
        job.finished_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        db.add(job)
        db.commit()
    except Exception as exc:
        err = str(exc)
        try:
            job = db.query(IAJob).filter(IAJob.id == int(job_id)).first()
            if job:
                job.status = "error"
                job.progress = 100
                job.error_message = err
                job.finished_at = datetime.utcnow()
                job.updated_at = datetime.utcnow()
                db.add(job)
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


def _enqueue_ia_job(job_id: int) -> None:
    _IA_JOB_EXECUTOR.submit(_run_ia_job, int(job_id))


def _norm_text(value) -> str:
    return str(value or "").strip()


def _norm_status(value) -> str:
    s = _norm_text(value).lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s


def _parse_iso_date(value):
    raw = _norm_text(value)
    if not raw:
        return None
    try:
        if len(raw) >= 10:
            return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except Exception:
        return None
    return None


def _activity_state_label(status: str, end_date, progress: float, delivery_state: str) -> str:
    status_norm = _norm_status(status)
    delivery_norm = _norm_status(delivery_state)
    today = datetime.utcnow().date()
    if "revis" in delivery_norm or "revis" in status_norm:
        return "revision"
    if "terminad" in status_norm or "hech" in status_norm or progress >= 100:
        return "terminada"
    if end_date and end_date < today and progress < 100:
        return "atrasada"
    if "atras" in status_norm:
        return "atrasada"
    if "proceso" in status_norm or "iniciado" in status_norm:
        return "en_proceso"
    if end_date and today >= end_date and progress < 100:
        return "atrasada"
    return "sin_iniciar"


def _build_rule_recommendation(rule_hits: list) -> str:
    if not rule_hits:
        return "Revisar planificación y mantener seguimiento semanal."
    if "overdue" in rule_hits and "no_owner" in rule_hits:
        return "Asignar responsable hoy y reprogramar fecha final con plan de recuperación."
    if "overdue" in rule_hits:
        return "Definir plan de choque con tareas diarias hasta recuperar el atraso."
    if "stalled_review" in rule_hits:
        return "Resolver la revisión pendiente con aprobador y fecha compromiso."
    if "near_due_no_start" in rule_hits:
        return "Iniciar ejecución inmediata y validar recursos críticos de arranque."
    if "no_owner" in rule_hits:
        return "Asignar responsable directo y responsables de apoyo."
    return "Revisar dependencias y ajustar cronograma para evitar escalamiento de riesgo."


def _compute_poa_risk_items(db):
    rows = db.execute(
        text(
            """
            SELECT
                a.id AS activity_id,
                a.objective_id AS objective_id,
                o.eje_id AS axis_id,
                a.codigo AS activity_codigo,
                a.nombre AS activity_name,
                COALESCE(a.status, '') AS activity_status,
                COALESCE(a.entrega_estado, '') AS entrega_estado,
                COALESCE(a.avance, 0) AS progress,
                COALESCE(a.responsable, '') AS owner,
                COALESCE(a.fecha_inicial, '') AS start_date,
                COALESCE(a.fecha_final, '') AS end_date,
                COALESCE(a.updated_at, a.created_at) AS updated_at,
                COALESCE(o.nombre, '') AS objective_name,
                COALESCE(o.codigo, '') AS objective_code,
                COALESCE(ax.nombre, '') AS axis_name,
                COALESCE(ax.codigo, '') AS axis_code
            FROM poa_activities a
            LEFT JOIN strategic_objectives_config o ON o.id = a.objective_id
            LEFT JOIN strategic_axes_config ax ON ax.id = o.eje_id
            ORDER BY a.id ASC
            """
        )
    ).fetchall()
    today = datetime.utcnow().date()
    risk_items = []
    for row in rows:
        progress = float(row.progress or 0)
        end_date = _parse_iso_date(row.end_date)
        start_date = _parse_iso_date(row.start_date)
        updated_raw = _norm_text(row.updated_at)
        updated_date = _parse_iso_date(updated_raw) or today
        owner = _norm_text(row.owner)
        state = _activity_state_label(row.activity_status, end_date, progress, row.entrega_estado)
        score = 0.0
        rule_hits = []
        if ((end_date and end_date < today and progress < 100) or "atras" in _norm_status(row.activity_status)):
            score += 0.55
            rule_hits.append("overdue")
        if not owner:
            score += 0.2
            rule_hits.append("no_owner")
        if state == "revision":
            days_in_review = (today - updated_date).days
            if days_in_review >= 5:
                score += 0.2
                rule_hits.append("stalled_review")
        if state == "sin_iniciar" and end_date and (end_date - today).days <= 7:
            score += 0.18
            rule_hits.append("near_due_no_start")
        if start_date and today > start_date and progress <= 0 and state != "terminada":
            score += 0.12
            rule_hits.append("no_progress_after_start")
        if progress >= 100:
            score = 0.0
            rule_hits = []
        score = min(round(score, 4), 1.0)
        if score >= 0.7:
            severity = "high"
        elif score >= 0.4:
            severity = "medium"
        elif score > 0:
            severity = "low"
        else:
            severity = "none"
        title = f"Riesgo POA: {row.activity_name or 'Actividad sin nombre'}"
        message = (
            f"Eje {row.axis_code or 'N/D'} · Obj {row.objective_code or 'N/D'} · "
            f"Estado {state.replace('_', ' ')} · Avance {int(round(progress))}%"
        )
        risk_items.append(
            {
                "alert_key": f"poa:{int(row.activity_id or 0)}",
                "activity_id": int(row.activity_id or 0),
                "objective_id": int(row.objective_id or 0) if row.objective_id is not None else None,
                "axis_id": int(row.axis_id or 0) if row.axis_id is not None else None,
                "activity_code": _norm_text(row.activity_codigo),
                "activity_name": _norm_text(row.activity_name),
                "objective_name": _norm_text(row.objective_name),
                "objective_code": _norm_text(row.objective_code),
                "axis_name": _norm_text(row.axis_name),
                "axis_code": _norm_text(row.axis_code),
                "owner": owner,
                "status": _norm_text(row.activity_status),
                "delivery_status": _norm_text(row.entrega_estado),
                "start_date": _norm_text(row.start_date),
                "end_date": _norm_text(row.end_date),
                "progress": round(progress, 2),
                "risk_score": score,
                "severity": severity,
                "rule_hits": rule_hits,
                "state": state,
                "title": title,
                "message": message,
                "recommendation": _build_rule_recommendation(rule_hits),
            }
        )
    return risk_items


def _build_ia_recommendations(risk_items: list, top_n: int = 5) -> list:
    top = [item for item in risk_items if item.get("severity") in {"high", "medium"}]
    top = sorted(top, key=lambda item: item.get("risk_score", 0), reverse=True)[:top_n]
    if not top:
        return []
    compact = []
    for item in top:
        compact.append(
            {
                "activity": item.get("activity_name"),
                "axis": item.get("axis_name"),
                "objective": item.get("objective_name"),
                "progress": item.get("progress"),
                "state": item.get("state"),
                "owner": item.get("owner") or "sin responsable",
                "risk_score": item.get("risk_score"),
                "rules": item.get("rule_hits", []),
            }
        )
    prompt = (
        "Actúa como PMO. En español, genera recomendaciones accionables (1 por actividad) "
        "para reducir riesgo POA. Formato JSON estricto: "
        '{"recommendations":[{"activity":"...","action":"...","priority":"alta|media","horizon":"48h|7d|30d"}]}. '
        f"Datos: {json.dumps(compact, ensure_ascii=False)}"
    )
    try:
        out = _extract_text_from_provider_result(complete_with_fallback(prompt))
        parsed = json.loads(out)
        recs = parsed.get("recommendations", []) if isinstance(parsed, dict) else []
        if isinstance(recs, list):
            safe = []
            for rec in recs[:top_n]:
                if not isinstance(rec, dict):
                    continue
                safe.append(
                    {
                        "activity": _norm_text(rec.get("activity")),
                        "action": _norm_text(rec.get("action")),
                        "priority": _norm_text(rec.get("priority")) or "media",
                        "horizon": _norm_text(rec.get("horizon")) or "7d",
                    }
                )
            if safe:
                return safe
    except Exception:
        pass
    fallback = []
    for item in top:
        fallback.append(
            {
                "activity": item.get("activity_name"),
                "action": item.get("recommendation"),
                "priority": "alta" if item.get("severity") == "high" else "media",
                "horizon": "48h" if item.get("severity") == "high" else "7d",
            }
        )
    return fallback


def _persist_risk_alerts(db, risk_items: list, recommendations: list) -> dict:
    _ensure_poa_risk_alerts_table(db)
    now_iso = datetime.utcnow().isoformat()
    rec_map = {}
    for rec in recommendations or []:
        activity_name = _norm_text(rec.get("activity"))
        if activity_name:
            rec_map[activity_name.lower()] = rec
    active_keys = set()
    created = 0
    updated = 0
    for item in risk_items:
        if item.get("severity") not in {"high", "medium"}:
            continue
        alert_key = str(item.get("alert_key") or "").strip()
        if not alert_key:
            continue
        active_keys.add(alert_key)
        rec = rec_map.get(_norm_text(item.get("activity_name")).lower(), {})
        rec_text = _norm_text(rec.get("action")) or _norm_text(item.get("recommendation"))
        exists = db.execute(
            text("SELECT id FROM ia_poa_risk_alerts WHERE alert_key = :k LIMIT 1"),
            {"k": alert_key},
        ).fetchone()
        payload = {
            "updated_at": now_iso,
            "activity_id": item.get("activity_id"),
            "objective_id": item.get("objective_id"),
            "axis_id": item.get("axis_id"),
            "severity": item.get("severity"),
            "risk_score": float(item.get("risk_score") or 0),
            "status": "active",
            "owner": _norm_text(item.get("owner")),
            "title": _norm_text(item.get("title")),
            "message": _norm_text(item.get("message")),
            "recommendation": rec_text,
        }
        if exists:
            db.execute(
                text(
                    """
                    UPDATE ia_poa_risk_alerts
                    SET updated_at = :updated_at,
                        activity_id = :activity_id,
                        objective_id = :objective_id,
                        axis_id = :axis_id,
                        severity = :severity,
                        risk_score = :risk_score,
                        status = :status,
                        owner = :owner,
                        title = :title,
                        message = :message,
                        recommendation = :recommendation,
                        resolved_at = ''
                    WHERE alert_key = :alert_key
                    """
                ),
                {**payload, "alert_key": alert_key},
            )
            updated += 1
        else:
            db.execute(
                text(
                    """
                    INSERT INTO ia_poa_risk_alerts (
                        created_at, updated_at, alert_key, activity_id, objective_id, axis_id,
                        severity, risk_score, status, owner, title, message, recommendation, source, resolved_at
                    ) VALUES (
                        :created_at, :updated_at, :alert_key, :activity_id, :objective_id, :axis_id,
                        :severity, :risk_score, :status, :owner, :title, :message, :recommendation, 'ia_risk_engine', ''
                    )
                    """
                ),
                {**payload, "created_at": now_iso, "alert_key": alert_key},
            )
            created += 1
    if active_keys:
        placeholders = ", ".join([f":k{i}" for i in range(len(active_keys))])
        bind = {f"k{i}": key for i, key in enumerate(active_keys)}
        db.execute(
            text(
                f"""
                UPDATE ia_poa_risk_alerts
                SET status = 'resolved', resolved_at = :resolved_at, updated_at = :updated_at
                WHERE source = 'ia_risk_engine'
                  AND status = 'active'
                  AND alert_key NOT IN ({placeholders})
                """
            ),
            {"resolved_at": now_iso, "updated_at": now_iso, **bind},
        )
    else:
        db.execute(
            text(
                """
                UPDATE ia_poa_risk_alerts
                SET status = 'resolved', resolved_at = :resolved_at, updated_at = :updated_at
                WHERE source = 'ia_risk_engine' AND status = 'active'
                """
            ),
            {"resolved_at": now_iso, "updated_at": now_iso},
        )
    db.commit()
    return {"created": created, "updated": updated, "active_keys": len(active_keys)}


def _normalize_exec_filters(raw_filters: dict) -> dict:
    raw_filters = raw_filters if isinstance(raw_filters, dict) else {}
    filters = {
        "eje_id": _norm_text(raw_filters.get("eje_id")),
        "objective_id": _norm_text(raw_filters.get("objective_id")),
        "responsable": _norm_text(raw_filters.get("responsable") or raw_filters.get("usuario")),
        "status": _norm_text(raw_filters.get("status")),
        "fecha_desde": _norm_text(raw_filters.get("fecha_desde")),
        "fecha_hasta": _norm_text(raw_filters.get("fecha_hasta")),
        "only_overdue": bool(raw_filters.get("only_overdue", False)),
        "severity": _norm_text(raw_filters.get("severity")).lower(),
        "region": _norm_text(raw_filters.get("region")),
        "departamento": _norm_text(raw_filters.get("departamento")),
        "sucursal": _norm_text(raw_filters.get("sucursal")),
    }
    return filters


def _build_activities_where(filters: dict):
    clauses = []
    params = {}
    eje_id = _norm_text(filters.get("eje_id"))
    if eje_id:
        clauses.append("o.eje_id = :eje_id")
        params["eje_id"] = int(eje_id)
    objective_id = _norm_text(filters.get("objective_id"))
    if objective_id:
        clauses.append("a.objective_id = :objective_id")
        params["objective_id"] = int(objective_id)
    responsable = _norm_text(filters.get("responsable"))
    if responsable:
        clauses.append("lower(COALESCE(a.responsable, '')) = :responsable")
        params["responsable"] = responsable.lower()
    status = _norm_text(filters.get("status"))
    if status:
        clauses.append("lower(COALESCE(a.status, '')) LIKE :status")
        params["status"] = f"%{status.lower()}%"
    fecha_desde = _norm_text(filters.get("fecha_desde"))
    if fecha_desde:
        clauses.append("date(COALESCE(a.fecha_inicial, '')) >= date(:fecha_desde)")
        params["fecha_desde"] = fecha_desde
    fecha_hasta = _norm_text(filters.get("fecha_hasta"))
    if fecha_hasta:
        clauses.append("date(COALESCE(a.fecha_final, '')) <= date(:fecha_hasta)")
        params["fecha_hasta"] = fecha_hasta
    if bool(filters.get("only_overdue")):
        clauses.append(
            "("
            "(COALESCE(a.fecha_final, '') <> '' AND date(a.fecha_final) < date('now') AND COALESCE(a.avance, 0) < 100)"
            " OR lower(COALESCE(a.status, '')) LIKE '%atras%'"
            ")"
        )
    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where_sql, params


def _compute_executive_dataset(db, filters: dict) -> dict:
    where_sql, params = _build_activities_where(filters)
    axis_total = int(db.execute(text("SELECT COUNT(*) FROM strategic_axes_config WHERE is_active = 1")).scalar() or 0)
    objective_total = int(db.execute(text("SELECT COUNT(*) FROM strategic_objectives_config WHERE is_active = 1")).scalar() or 0)
    activity_total = int(
        db.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM poa_activities a
                LEFT JOIN strategic_objectives_config o ON o.id = a.objective_id
                {where_sql}
                """
            ),
            params,
        ).scalar()
        or 0
    )
    completed_total = int(
        db.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM poa_activities a
                LEFT JOIN strategic_objectives_config o ON o.id = a.objective_id
                {where_sql}
                {"AND" if where_sql else "WHERE"} (
                    lower(COALESCE(a.status, '')) LIKE '%terminad%'
                    OR COALESCE(a.avance, 0) >= 100
                )
                """
            ),
            params,
        ).scalar()
        or 0
    )
    overdue_total = int(
        db.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM poa_activities a
                LEFT JOIN strategic_objectives_config o ON o.id = a.objective_id
                {where_sql}
                {"AND" if where_sql else "WHERE"} (
                    (COALESCE(a.fecha_final, '') <> '' AND date(a.fecha_final) < date('now') AND COALESCE(a.avance, 0) < 100)
                    OR lower(COALESCE(a.status, '')) LIKE '%atras%'
                )
                """
            ),
            params,
        ).scalar()
        or 0
    )
    progress_avg = float(
        db.execute(
            text(
                f"""
                SELECT COALESCE(AVG(COALESCE(a.avance, 0)), 0)
                FROM poa_activities a
                LEFT JOIN strategic_objectives_config o ON o.id = a.objective_id
                {where_sql}
                """
            ),
            params,
        ).scalar()
        or 0.0
    )
    budget_total = float(db.execute(text("SELECT COALESCE(SUM(COALESCE(anual, 0)), 0) FROM poa_activity_budgets")).scalar() or 0.0)

    owners = db.execute(
        text(
            f"""
            SELECT COALESCE(a.responsable, '') AS owner, COUNT(*) AS qty
            FROM poa_activities a
            LEFT JOIN strategic_objectives_config o ON o.id = a.objective_id
            {where_sql}
            GROUP BY COALESCE(a.responsable, '')
            ORDER BY qty DESC
            LIMIT 5
            """
        ),
        params,
    ).fetchall()
    top_owners = [{"owner": _norm_text(row.owner) or "Sin responsable", "activities": int(row.qty or 0)} for row in owners]

    _ensure_poa_risk_alerts_table(db)
    severity_filter = _norm_text(filters.get("severity")).lower()
    risk_params = {}
    risk_where = "WHERE source = 'ia_risk_engine' AND status = 'active'"
    if severity_filter in {"high", "medium", "low"}:
        risk_where += " AND severity = :severity"
        risk_params["severity"] = severity_filter
    risk_rows = db.execute(
        text(
            f"""
            SELECT severity, COUNT(*) AS qty
            FROM ia_poa_risk_alerts
            {risk_where}
            GROUP BY severity
            """
        ),
        risk_params,
    ).fetchall()
    risk_counts = {"high": 0, "medium": 0, "low": 0}
    for row in risk_rows:
        sev = _norm_text(row.severity).lower()
        if sev in risk_counts:
            risk_counts[sev] = int(row.qty or 0)

    recommendations_rows = db.execute(
        text(
            f"""
            SELECT title, recommendation, severity, risk_score, updated_at
            FROM ia_poa_risk_alerts
            {risk_where}
            ORDER BY
                CASE severity WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 ELSE 0 END DESC,
                risk_score DESC,
                updated_at DESC
            LIMIT 5
            """
        ),
        risk_params,
    ).fetchall()
    recommendations = [
        {
            "title": _norm_text(row.title),
            "recommendation": _norm_text(row.recommendation),
            "severity": _norm_text(row.severity),
            "risk_score": float(row.risk_score or 0),
            "updated_at": _norm_text(row.updated_at),
        }
        for row in recommendations_rows
    ]
    return {
        "axes": axis_total,
        "objectives": objective_total,
        "activities": activity_total,
        "completed_activities": completed_total,
        "overdue_activities": overdue_total,
        "avg_objective_progress": round(progress_avg, 2),
        "budget_annual_total": round(budget_total, 2),
        "ia_risk_alerts_count": int(sum(risk_counts.values())),
        "ia_risk_high_count": int(risk_counts["high"]),
        "ia_risk_medium_count": int(risk_counts["medium"]),
        "ia_risk_low_count": int(risk_counts["low"]),
        "top_owners": top_owners,
        "ia_recommendations": recommendations,
        "filters_applied": filters,
        "generated_at": datetime.utcnow().isoformat(),
    }


def _render_exec_narrative(dataset: dict) -> str:
    payload = {
        "metrics": {
            "activities": dataset.get("activities", 0),
            "completed_activities": dataset.get("completed_activities", 0),
            "overdue_activities": dataset.get("overdue_activities", 0),
            "avg_objective_progress": dataset.get("avg_objective_progress", 0),
            "budget_annual_total": dataset.get("budget_annual_total", 0),
            "ia_risk_alerts_count": dataset.get("ia_risk_alerts_count", 0),
            "ia_risk_high_count": dataset.get("ia_risk_high_count", 0),
        },
        "top_owners": dataset.get("top_owners", [])[:5],
        "recommendations": dataset.get("ia_recommendations", [])[:5],
        "filters": dataset.get("filters_applied", {}),
    }
    prompt = (
        "Genera un reporte ejecutivo breve en español para dirección general. "
        "Incluye: 1) resumen general, 2) riesgos críticos, 3) concentración por responsables, "
        "4) acciones sugeridas a 7 días. Máximo 320 palabras. "
        f"Datos: {json.dumps(payload, ensure_ascii=False)}"
    )
    try:
        out = _extract_text_from_provider_result(complete_with_fallback(prompt)).strip()
        if out:
            return out
    except Exception:
        pass
    return (
        f"Resumen ejecutivo: Se registran {int(dataset.get('activities', 0))} actividades POA, "
        f"con {int(dataset.get('completed_activities', 0))} completadas y "
        f"{int(dataset.get('overdue_activities', 0))} atrasadas. "
        f"El avance promedio es {float(dataset.get('avg_objective_progress', 0)):.2f}%.\n\n"
        f"Riesgo IA: alertas activas {int(dataset.get('ia_risk_alerts_count', 0))}, "
        f"de las cuales {int(dataset.get('ia_risk_high_count', 0))} son de severidad alta.\n\n"
        "Acciones sugeridas:\n"
        + "\n".join([f"- {str(item.get('recommendation') or '').strip()}" for item in dataset.get("ia_recommendations", [])[:5]])
    ).strip()


def _make_report_key(filters: dict) -> str:
    return json.dumps(filters or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _persist_exec_report(db, *, username: str, role: str, filters: dict, dataset: dict, narrative: str) -> dict:
    _ensure_exec_reports_table(db)
    now_iso = datetime.utcnow().isoformat()
    report_key = _make_report_key(filters)
    next_version = int(
        db.execute(
            text("SELECT COALESCE(MAX(version_no), 0) + 1 FROM ia_executive_reports WHERE report_key = :rk"),
            {"rk": report_key},
        ).scalar()
        or 1
    )
    title = f"Reporte Ejecutivo IA v{next_version}"
    db.execute(
        text(
            """
            INSERT INTO ia_executive_reports (
                created_at, updated_at, report_key, version_no, title, username, role,
                filters_json, snapshot_json, narrative_text, model_name, provider
            ) VALUES (
                :created_at, :updated_at, :report_key, :version_no, :title, :username, :role,
                :filters_json, :snapshot_json, :narrative_text, :model_name, :provider
            )
            """
        ),
        {
            "created_at": now_iso,
            "updated_at": now_iso,
            "report_key": report_key,
            "version_no": next_version,
            "title": title,
            "username": username,
            "role": role,
            "filters_json": json.dumps(filters or {}, ensure_ascii=False),
            "snapshot_json": json.dumps(dataset or {}, ensure_ascii=False),
            "narrative_text": narrative or "",
            "model_name": "",
            "provider": "",
        },
    )
    db.commit()
    row_id = int(db.execute(text("SELECT last_insert_rowid()")).scalar() or 0)
    return {
        "id": row_id,
        "report_key": report_key,
        "version_no": next_version,
        "title": title,
        "created_at": now_iso,
    }


def _can_read_exec_report(role: str, current_username: str, row_username: str) -> bool:
    if role in {"superadministrador", "administrador"}:
        return True
    return bool(current_username and current_username.lower() == _norm_text(row_username).lower())


def _current_tenant(request: Request) -> str:
    tenant = _norm_text(getattr(request.state, "tenant_id", None))
    if tenant:
        return tenant.lower()
    tenant = _norm_text(request.cookies.get("tenant_id"))
    if tenant:
        return tenant.lower()
    tenant = _norm_text(request.headers.get("x-tenant-id"))
    return (tenant or "default").lower()


def _clean_text_for_index(raw: str) -> str:
    text_in = str(raw or "")
    text_in = re.sub(r"<script[\s\S]*?</script>", " ", text_in, flags=re.IGNORECASE)
    text_in = re.sub(r"<style[\s\S]*?</style>", " ", text_in, flags=re.IGNORECASE)
    text_in = re.sub(r"<[^>]+>", " ", text_in)
    text_in = text_in.replace("&nbsp;", " ").replace("&amp;", "&")
    text_in = re.sub(r"\s+", " ", text_in)
    return text_in.strip()


def _load_document_file_text(file_path: str) -> str:
    path_raw = _norm_text(file_path)
    if not path_raw:
        return ""
    candidates = [path_raw]
    if not os.path.isabs(path_raw):
        candidates.append(os.path.abspath(path_raw))
        candidates.append(os.path.abspath(os.path.join(os.getcwd(), path_raw)))
    resolved = ""
    for candidate in candidates:
        if candidate and os.path.exists(candidate) and os.path.isfile(candidate):
            resolved = candidate
            break
    if not resolved:
        return ""
    ext = os.path.splitext(resolved)[1].lower()
    if ext not in {".txt", ".md", ".html", ".htm", ".csv", ".json", ".log"}:
        return ""
    try:
        with open(resolved, "r", encoding="utf-8", errors="ignore") as fh:
            raw = fh.read()
        return _clean_text_for_index(raw)
    except Exception:
        return ""


def _chunk_text(text_in: str, max_chars: int = 900, overlap: int = 140) -> list:
    base = _clean_text_for_index(text_in)
    if not base:
        return []
    chunks = []
    start = 0
    n = len(base)
    while start < n:
        end = min(start + max_chars, n)
        chunk = base[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def _tokenize(text_in: str) -> list:
    norm = _norm_status(text_in)
    return [tok for tok in re.findall(r"[a-z0-9]{2,}", norm) if tok]


def _document_access_where(request: Request, role: str, username: str, tenant: str, table_alias: str = "d"):
    alias = table_alias
    clauses = []
    params = {}
    tenant_header = _norm_text(request.headers.get("x-tenant-id")).lower()
    if role == "superadministrador":
        if tenant_header and tenant_header != "all":
            clauses.append(f"lower(COALESCE({alias}.tenant_id,'default')) = :tenant_id")
            params["tenant_id"] = tenant_header
    else:
        clauses.append(f"lower(COALESCE({alias}.tenant_id,'default')) = :tenant_id")
        params["tenant_id"] = tenant
    if role not in {"superadministrador", "administrador"}:
        clauses.append(
            "("
            f"lower(COALESCE({alias}.estado,'')) IN ('autorizado','actualizado') "
            f"OR lower(COALESCE({alias}.creado_por,'')) = :username "
            f"OR lower(COALESCE({alias}.enviado_por,'')) = :username "
            f"OR lower(COALESCE({alias}.autorizado_por,'')) = :username "
            f"OR lower(COALESCE({alias}.actualizado_por,'')) = :username"
            ")"
        )
        params["username"] = username.lower()
    where_sql = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return where_sql, params


def _upsert_rag_document(db, source_doc) -> dict:
    src_title = _norm_text(source_doc.titulo)
    src_summary = _norm_text(source_doc.descripcion)
    src_notes = _norm_text(source_doc.observaciones)
    file_text = _load_document_file_text(_norm_text(source_doc.archivo_ruta))
    full_text = "\n\n".join([part for part in [src_title, src_summary, src_notes, file_text] if part]).strip()
    text_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest() if full_text else ""
    existing = db.execute(
        text("SELECT id, source_hash FROM ia_rag_documents WHERE source_doc_id = :sid LIMIT 1"),
        {"sid": int(source_doc.id or 0)},
    ).fetchone()
    indexed_at = datetime.utcnow().isoformat()
    if existing:
        rag_doc_id = int(existing.id or 0)
        db.execute(
            text(
                """
                UPDATE ia_rag_documents
                SET tenant_id = :tenant_id,
                    estado = :estado,
                    title = :title,
                    summary = :summary,
                    file_path = :file_path,
                    creado_por = :creado_por,
                    enviado_por = :enviado_por,
                    autorizado_por = :autorizado_por,
                    actualizado_por = :actualizado_por,
                    source_updated_at = :source_updated_at,
                    source_hash = :source_hash,
                    indexed_at = :indexed_at
                WHERE id = :id
                """
            ),
            {
                "id": rag_doc_id,
                "tenant_id": _norm_text(source_doc.tenant_id) or "default",
                "estado": _norm_text(source_doc.estado),
                "title": src_title,
                "summary": src_summary,
                "file_path": _norm_text(source_doc.archivo_ruta),
                "creado_por": _norm_text(source_doc.creado_por),
                "enviado_por": _norm_text(source_doc.enviado_por),
                "autorizado_por": _norm_text(source_doc.autorizado_por),
                "actualizado_por": _norm_text(source_doc.actualizado_por),
                "source_updated_at": _norm_text(source_doc.updated_at.isoformat() if source_doc.updated_at else ""),
                "source_hash": text_hash,
                "indexed_at": indexed_at,
            },
        )
    else:
        db.execute(
            text(
                """
                INSERT INTO ia_rag_documents (
                    source_doc_id, tenant_id, estado, title, summary, file_path,
                    creado_por, enviado_por, autorizado_por, actualizado_por,
                    source_updated_at, source_hash, chunk_count, indexed_at
                ) VALUES (
                    :source_doc_id, :tenant_id, :estado, :title, :summary, :file_path,
                    :creado_por, :enviado_por, :autorizado_por, :actualizado_por,
                    :source_updated_at, :source_hash, 0, :indexed_at
                )
                """
            ),
            {
                "source_doc_id": int(source_doc.id or 0),
                "tenant_id": _norm_text(source_doc.tenant_id) or "default",
                "estado": _norm_text(source_doc.estado),
                "title": src_title,
                "summary": src_summary,
                "file_path": _norm_text(source_doc.archivo_ruta),
                "creado_por": _norm_text(source_doc.creado_por),
                "enviado_por": _norm_text(source_doc.enviado_por),
                "autorizado_por": _norm_text(source_doc.autorizado_por),
                "actualizado_por": _norm_text(source_doc.actualizado_por),
                "source_updated_at": _norm_text(source_doc.updated_at.isoformat() if source_doc.updated_at else ""),
                "source_hash": text_hash,
                "indexed_at": indexed_at,
            },
        )
        rag_doc_id = int(db.execute(text("SELECT last_insert_rowid()")).scalar() or 0)
    chunks = _chunk_text(full_text)
    db.execute(text("DELETE FROM ia_rag_chunks WHERE rag_document_id = :rid"), {"rid": int(rag_doc_id)})
    for idx, chunk in enumerate(chunks, start=1):
        token_count = len(_tokenize(chunk))
        db.execute(
            text(
                """
                INSERT INTO ia_rag_chunks (rag_document_id, source_doc_id, chunk_order, content, token_count, created_at)
                VALUES (:rag_document_id, :source_doc_id, :chunk_order, :content, :token_count, :created_at)
                """
            ),
            {
                "rag_document_id": int(rag_doc_id),
                "source_doc_id": int(source_doc.id or 0),
                "chunk_order": int(idx),
                "content": chunk,
                "token_count": int(token_count),
                "created_at": indexed_at,
            },
        )
    db.execute(
        text("UPDATE ia_rag_documents SET chunk_count = :chunk_count, indexed_at = :indexed_at WHERE id = :id"),
        {"chunk_count": int(len(chunks)), "indexed_at": indexed_at, "id": int(rag_doc_id)},
    )
    return {
        "rag_document_id": int(rag_doc_id),
        "source_doc_id": int(source_doc.id or 0),
        "title": src_title,
        "chunk_count": int(len(chunks)),
    }


def _retrieve_rag_context(db, request: Request, role: str, username: str, tenant: str, query_text: str, top_k: int = 6) -> list:
    where_sql, params = _document_access_where(request, role, username, tenant, table_alias="d")
    rows = db.execute(
        text(
            f"""
            SELECT
                c.id AS chunk_id,
                c.content AS content,
                c.token_count AS token_count,
                d.source_doc_id AS source_doc_id,
                d.title AS title,
                d.summary AS summary,
                d.estado AS estado,
                d.file_path AS file_path
            FROM ia_rag_chunks c
            JOIN ia_rag_documents d ON d.id = c.rag_document_id
            {where_sql}
            ORDER BY d.indexed_at DESC, c.chunk_order ASC
            LIMIT 5000
            """
        ),
        params,
    ).fetchall()
    q_tokens = _tokenize(query_text)
    q_set = set(q_tokens)
    scored = []
    for row in rows:
        chunk = _norm_text(row.content)
        if not chunk:
            continue
        c_tokens = _tokenize(chunk)
        if not c_tokens:
            continue
        c_set = set(c_tokens)
        overlap = len(q_set.intersection(c_set))
        if overlap <= 0 and q_tokens:
            continue
        score = float(overlap) / math.sqrt(float(len(c_set) or 1))
        title_tokens = set(_tokenize(_norm_text(row.title)))
        if title_tokens and q_set.intersection(title_tokens):
            score += 0.5
        scored.append(
            {
                "score": round(score, 6),
                "chunk_id": int(row.chunk_id or 0),
                "content": chunk,
                "source_doc_id": int(row.source_doc_id or 0),
                "title": _norm_text(row.title) or f"Documento {int(row.source_doc_id or 0)}",
                "summary": _norm_text(row.summary),
                "estado": _norm_text(row.estado),
                "file_path": _norm_text(row.file_path),
            }
        )
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[: max(1, min(int(top_k or 6), 12))]


def _safe_json_loads(raw_value, default):
    try:
        parsed = json.loads(str(raw_value or ""))
        return parsed
    except Exception:
        return default


def _normalize_identity_block(payload, prefix: str) -> list:
    rows = payload if isinstance(payload, list) else []
    out = []
    seq = 1
    for row in rows:
        item = row if isinstance(row, dict) else {}
        text_value = _norm_text(item.get("text") or item.get("texto") or item.get("value") or item.get("descripcion"))
        if not text_value:
            continue
        code_value = _norm_text(item.get("code") or item.get("codigo"))
        if not code_value:
            code_value = f"{prefix}{seq:02d}"
        out.append({"code": code_value.lower(), "text": text_value})
        seq += 1
    return out


def _detect_query_intent(query_text: str) -> set:
    """Detecta qué módulos son relevantes para la pregunta."""
    q = _norm_text(query_text).lower()
    intents = set()
    poa_kw = {
        "poa", "actividad", "actividades", "plan operativo", "tarea", "tareas",
        "entrega", "avance", "responsable", "responsables", "obra", "obras",
        "cumplimiento", "ejecutar", "ejecucion", "quien", "quién", "persona",
        "colaborador", "departamento", "area", "sucursal", "region", "zona",
        "objetivo", "cumple", "atrasad", "terminad", "pendiente",
    }
    estrategia_kw = {
        "estrategia", "estrategic", "plan estrategico", "eje", "ejes",
        "mision", "misión", "vision", "visión", "valor", "valores",
        "fundamentacion", "fundamentación", "tactico", "táctico",
        "objetivo estrategico", "bsc", "balanced scorecard",
    }
    presupuesto_kw = {
        "presupuesto", "ingreso", "ingresos", "egreso", "egresos", "gasto",
        "gastos", "salario", "salarios", "rubro", "rubros", "monto", "montos",
        "proyectado", "realizado", "financiero", "financiera", "mensual",
        "mensualmente", "ejecucion presupuestal", "costo", "costos",
        "utilidad", "perdida", "resultado financiero",
    }
    region_dept_kw = {"region", "zona", "sucursal", "departamento", "area", "depto"}
    for kw in poa_kw:
        if kw in q:
            intents.add("poa")
            break
    for kw in estrategia_kw:
        if kw in q:
            intents.add("estrategia")
            break
    for kw in presupuesto_kw:
        if kw in q:
            intents.add("presupuesto")
            break
    for kw in region_dept_kw:
        if kw in q:
            # región/departamento puede tocar POA y presupuesto
            intents.add("poa")
            intents.add("presupuesto")
            break
    if not intents:
        intents = {"poa", "estrategia", "presupuesto"}
    return intents


def _retrieve_strategic_context(db, query_text: str, top_k: int = 4, include_extra: bool = True) -> list:
    intents = _detect_query_intent(query_text)

    # ── 1. Leer todos los bloques relevantes de strategic_identity_config ──
    all_blocks = [
        "mision", "vision", "valores", "fundamentacion",
        "base_ia_extra", "base_ia_weekly_meta",
        "poa_base_ia_extra", "poa_base_ia_weekly_meta",
        "presupuesto_base_ia_extra", "presupuesto_base_ia_weekly_meta",
    ]
    try:
        identity_rows = db.execute(
            text(
                "SELECT bloque, payload FROM strategic_identity_config WHERE bloque IN ("
                + ",".join(f"'{b}'" for b in all_blocks)
                + ")"
            )
        ).fetchall()
    except Exception:
        identity_rows = []
    identity_map = {str(row[0] or "").strip().lower(): str(row[1] or "") for row in identity_rows}

    chunks = []
    wants_estrategia = "estrategia" in intents
    wants_poa = "poa" in intents
    wants_presupuesto = "presupuesto" in intents

    # ── 2. Identidad institucional (siempre incluida, peso alto) ──
    mision = _normalize_identity_block(_safe_json_loads(identity_map.get("mision", "[]"), []), "m")
    vision = _normalize_identity_block(_safe_json_loads(identity_map.get("vision", "[]"), []), "v")
    valores = _normalize_identity_block(_safe_json_loads(identity_map.get("valores", "[]"), []), "val")
    if mision or vision or valores:
        parts = []
        if mision:
            parts.append("Misión: " + " | ".join(f"{i['code'].upper()}: {i['text']}" for i in mision[:8]))
        if vision:
            parts.append("Visión: " + " | ".join(f"{i['code'].upper()}: {i['text']}" for i in vision[:8]))
        if valores:
            parts.append("Valores: " + " | ".join(f"{i['code'].upper()}: {i['text']}" for i in valores[:12]))
        chunks.append({
            "score": 1.0 if wants_estrategia else 0.5,
            "source_tag": "S-IDENTIDAD",
            "title": "Identidad institucional (misión, visión, valores)",
            "content": "\n".join(parts),
            "source_type": "strategic_base",
        })

    # ── 3. Fundamentación ──
    fundamentacion_payload = _safe_json_loads(identity_map.get("fundamentacion", "{}"), {})
    fundamentacion_text = _clean_text_for_index(
        str((fundamentacion_payload if isinstance(fundamentacion_payload, dict) else {}).get("texto") or "")
    )
    if fundamentacion_text and wants_estrategia:
        chunks.append({
            "score": 0.8,
            "source_tag": "S-FUNDAMENTACION",
            "title": "Base estratégica: Fundamentación",
            "content": fundamentacion_text[:3000],
            "source_type": "strategic_base",
        })

    # ── 4. Base IA Estrategia (snapshot semanal generado por IA) ──
    if include_extra:
        extra_payload = _safe_json_loads(identity_map.get("base_ia_extra", "{}"), {})
        extra_text = _clean_text_for_index(str((extra_payload if isinstance(extra_payload, dict) else {}).get("texto") or ""))
        if extra_text:
            chunks.append({
                "score": 1.2 if wants_estrategia else 0.4,
                "source_tag": "S-ESTRATEGIA-EXTRA",
                "title": "Resumen semanal IA · Plan Estratégico",
                "content": extra_text[:4000],
                "source_type": "strategic_base",
            })

    weekly_meta = _safe_json_loads(identity_map.get("base_ia_weekly_meta", "{}"), {})
    if isinstance(weekly_meta, dict) and weekly_meta and wants_estrategia:
        progress_json = weekly_meta.get("progress_snapshot", {})
        chunks.append({
            "score": 0.9,
            "source_tag": "S-AVANCE-ESTRATEGIA",
            "title": "Avance plan estratégico (snapshot semanal)",
            "content": (
                f"Corte: {_norm_text(weekly_meta.get('last_refresh_at')) or 'N/D'}\n"
                + json.dumps(progress_json if isinstance(progress_json, dict) else {}, ensure_ascii=False)
            )[:3000],
            "source_type": "strategic_base",
        })

    # ── 5. POA: datos de actividades por responsable/departamento/region ──
    if wants_poa and include_extra:
        poa_extra = _safe_json_loads(identity_map.get("poa_base_ia_extra", "{}"), {})
        poa_text = _clean_text_for_index(str((poa_extra if isinstance(poa_extra, dict) else {}).get("texto") or ""))
        if poa_text:
            chunks.append({
                "score": 1.5,
                "source_tag": "S-POA-DATOS",
                "title": "Base IA · POA — ejes, objetivos, actividades por responsable",
                "content": poa_text[:5000],
                "source_type": "poa_base",
            })
        poa_meta = _safe_json_loads(identity_map.get("poa_base_ia_weekly_meta", "{}"), {})
        if isinstance(poa_meta, dict) and poa_meta:
            chunks.append({
                "score": 1.3,
                "source_tag": "S-POA-META",
                "title": "Estado avance POA (snapshot semanal)",
                "content": (
                    f"Corte: {_norm_text(poa_meta.get('last_refresh_at')) or 'N/D'} · "
                    f"Chars generados: {int(poa_meta.get('generated_chars') or 0)}"
                )[:500],
                "source_type": "poa_base",
            })

    # ── 6. Presupuesto: rubros, control mensual, ejecución ──
    if wants_presupuesto and include_extra:
        pres_extra = _safe_json_loads(identity_map.get("presupuesto_base_ia_extra", "{}"), {})
        pres_text = _clean_text_for_index(str((pres_extra if isinstance(pres_extra, dict) else {}).get("texto") or ""))
        if pres_text:
            chunks.append({
                "score": 1.5,
                "source_tag": "S-PRESUPUESTO-DATOS",
                "title": "Base IA · Presupuesto — rubros, ingresos, egresos, control mensual",
                "content": pres_text[:5000],
                "source_type": "presupuesto_base",
            })
        pres_meta = _safe_json_loads(identity_map.get("presupuesto_base_ia_weekly_meta", "{}"), {})
        if isinstance(pres_meta, dict) and pres_meta:
            last_ok = _norm_text(pres_meta.get("last_refresh_at")) or "N/D"
            next_ok = _norm_text(pres_meta.get("next_refresh_at")) or "N/D"
            chunks.append({
                "score": 1.0,
                "source_tag": "S-PRESUPUESTO-META",
                "title": "Estado snapshot presupuesto",
                "content": f"Corte: {last_ok} · Próxima actualización: {next_ok}",
                "source_type": "presupuesto_base",
            })

    # ── 7. Ejes y objetivos estratégicos (estructura) ──
    try:
        axis_rows = db.execute(
            text(
                """
                SELECT a.id, COALESCE(a.codigo,'') AS axis_code, COALESCE(a.nombre,'') AS axis_name,
                       o.id AS oid, COALESCE(o.codigo,'') AS obj_code, COALESCE(o.nombre,'') AS obj_name
                FROM strategic_axes_config a
                LEFT JOIN strategic_objectives_config o ON o.eje_id = a.id
                ORDER BY COALESCE(a.orden,0) ASC, a.id ASC, COALESCE(o.orden,0) ASC, o.id ASC
                """
            )
        ).fetchall()
    except Exception:
        axis_rows = []

    axis_map = {}
    for row in axis_rows:
        aid = int(row[0] or 0)
        if aid <= 0:
            continue
        if aid not in axis_map:
            axis_map[aid] = {"axis_code": _norm_text(row[1]), "axis_name": _norm_text(row[2]) or f"Eje {aid}", "objectives": []}
        obj_name = _norm_text(row[5])
        if obj_name:
            axis_map[aid]["objectives"].append({"code": _norm_text(row[4]) or f"OBJ-{int(row[3] or 0)}", "name": obj_name})
    for aid in sorted(axis_map.keys()):
        ax = axis_map[aid]
        obj_lines = [f"{o['code'].upper()}: {o['name']}" for o in ax["objectives"][:24]]
        chunks.append({
            "score": 1.0 if wants_estrategia else 0.3,
            "source_tag": f"S-EJE-{aid}",
            "title": f"Plan Estratégico: Eje {ax.get('axis_code') or aid} — {ax.get('axis_name')}",
            "content": (
                f"Eje {ax.get('axis_code') or aid}: {ax.get('axis_name')}\n"
                + ("Objetivos: " + " | ".join(obj_lines) if obj_lines else "Sin objetivos registrados")
            )[:3000],
            "source_type": "strategic_base",
        })

    # ── 8. Scoring BM25 sobre los chunks recopilados ──
    q_tokens = _tokenize(query_text)
    if not chunks:
        return []
    if not q_tokens:
        chunks.sort(key=lambda x: x["score"], reverse=True)
        return chunks[:max(1, min(int(top_k or 4), 12))]
    q_set = set(q_tokens)
    scored = []
    for item in chunks:
        c_tokens = _tokenize(item.get("content", ""))
        c_set = set(c_tokens)
        overlap = len(q_set.intersection(c_set))
        bm25 = float(overlap) / math.sqrt(float(len(c_set) or 1)) if overlap > 0 else 0.0
        # Combinar BM25 con score de intención base del chunk
        combined = bm25 + float(item.get("score", 0.0))
        scored.append({**item, "score": round(combined, 6)})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:max(1, min(int(top_k or 4), 12))]

@router.get("/ia", response_class=HTMLResponse)
def ia_home(request: Request):
    """
    Página principal del módulo IA.
    """
    return templates.TemplateResponse("ia.html", {"request": request})


# Endpoint para sugerencia de texto de objetivo
@router.post("/api/ia/suggest/objective-text", response_class=JSONResponse)
def suggest_objective_text(request: Request, payload: dict = Body(...)):
    texto = payload.get("texto", "")
    module = str(payload.get("target_module", "") or payload.get("module", "")).strip().lower()
    if not texto:
        return {"error": "Texto requerido"}
    db = SessionLocal()
    try:
        _require_ia_feature(request, db, feature_key="suggest_objective_text", module=module)
    except PermissionError as exc:
        db.close()
        return JSONResponse(status_code=403, content={"error": str(exc)})
    ia_interaction = IAInteraction(
        created_at=datetime.utcnow(),
        user_id=None,  # Aquí puedes extraer el usuario si está disponible
        username=None,
        feature_key="suggest_objective_text",
        input_payload=texto,
        status="started"
    )
    db.add(ia_interaction)
    db.commit()
    db.refresh(ia_interaction)
    try:
        prompt = f"Mejora o sugiere una redacción clara y estratégica para el siguiente objetivo: {texto}"
        result = complete_with_fallback(prompt)
        sugerencia = _extract_text_from_provider_result(result)
        meta = _extract_completion_meta(result)
        ia_interaction.output_payload = sugerencia.strip()
        ia_interaction.model_name = meta["model"]
        ia_interaction.tokens_in = meta["prompt_tokens"]
        ia_interaction.tokens_out = meta["completion_tokens"]
        ia_interaction.estimated_cost = str(meta["cost_estimated"])
        ia_interaction.status = "success"
        db.commit()
        return {"sugerencia": sugerencia.strip()}
    except Exception as e:
        ia_interaction.status = "error"
        ia_interaction.error_message = str(e)
        db.commit()
        return {"error": str(e)}
    finally:
        db.close()


@router.post("/api/ia/suggestions", response_class=JSONResponse)
def create_suggestion_draft(request: Request, payload: dict = Body(...)):
    prompt = str(payload.get("prompt", "") or payload.get("texto", "")).strip()
    if not prompt:
        return JSONResponse(status_code=400, content={"success": False, "error": "Prompt requerido"})
    module = str(payload.get("target_module", "") or payload.get("module", "")).strip().lower()
    db = SessionLocal()
    try:
        _require_ia_feature(request, db, feature_key="suggest_objective_text", module=module)
        IAInteraction.__table__.create(bind=db.get_bind(), checkfirst=True)
        IASuggestionDraft.__table__.create(bind=db.get_bind(), checkfirst=True)
        interaction = IAInteraction(
            created_at=datetime.utcnow(),
            user_id=None,
            username=None,
            feature_key="suggestion_draft_create",
            input_payload=prompt,
            status="started",
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        draft = IASuggestionDraft(
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            user_id=str(payload.get("user_id", "") or "").strip() or None,
            username=str(payload.get("username", "") or "").strip() or None,
            status="generated",
            target_module=str(payload.get("target_module", "") or "").strip(),
            target_entity=str(payload.get("target_entity", "") or "").strip(),
            target_entity_id=str(payload.get("target_entity_id", "") or "").strip(),
            target_field=str(payload.get("target_field", "") or "").strip(),
            prompt_text=prompt,
            original_text=str(payload.get("original_text", "") or "").strip(),
            interaction_id=int(interaction.id or 0),
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)
        try:
            result = complete_with_fallback(prompt)
            suggestion = _extract_text_from_provider_result(result).strip()
            if not suggestion:
                raise RuntimeError("La IA no devolvió contenido.")
            meta = _extract_completion_meta(result)
            draft.suggested_text = suggestion
            draft.edited_text = suggestion
            draft.status = "generated"
            draft.updated_at = datetime.utcnow()
            interaction.output_payload = suggestion
            interaction.model_name = meta["model"]
            interaction.tokens_in = meta["prompt_tokens"]
            interaction.tokens_out = meta["completion_tokens"]
            interaction.estimated_cost = str(meta["cost_estimated"])
            interaction.status = "success"
            db.commit()
            db.refresh(draft)
            return {
                "success": True,
                "data": {
                    "id": draft.id,
                    "status": draft.status,
                    "suggested_text": draft.suggested_text,
                    "edited_text": draft.edited_text,
                    "target_module": draft.target_module,
                    "target_entity": draft.target_entity,
                    "target_entity_id": draft.target_entity_id,
                    "target_field": draft.target_field,
                    "created_at": draft.created_at.isoformat() if draft.created_at else "",
                    "updated_at": draft.updated_at.isoformat() if draft.updated_at else "",
                },
            }
        except Exception as exc:
            err = str(exc)
            draft.status = "error"
            draft.error_message = err
            draft.updated_at = datetime.utcnow()
            interaction.status = "error"
            interaction.error_message = err
            db.commit()
            return JSONResponse(status_code=500, content={"success": False, "error": err})
    finally:
        db.close()


@router.post("/api/ia/suggestions/{draft_id}/apply", response_class=JSONResponse)
def apply_suggestion_draft(request: Request, draft_id: int, payload: dict = Body(...)):
    db = SessionLocal()
    try:
        IASuggestionDraft.__table__.create(bind=db.get_bind(), checkfirst=True)
        draft = db.query(IASuggestionDraft).filter(IASuggestionDraft.id == int(draft_id)).first()
        if not draft:
            return JSONResponse(status_code=404, content={"success": False, "error": "Sugerencia no encontrada"})
        _require_ia_feature(
            request,
            db,
            feature_key="suggest_objective_text",
            module=str(draft.target_module or "").strip().lower(),
        )
        edited = str(payload.get("edited_text", "") or "").strip()
        if not edited:
            edited = str(draft.edited_text or draft.suggested_text or "").strip()
        if not edited:
            return JSONResponse(status_code=400, content={"success": False, "error": "Texto aplicado vacío"})
        draft.edited_text = edited
        draft.applied_text = edited
        draft.status = "applied"
        draft.updated_at = datetime.utcnow()
        db.commit()
        return {
            "success": True,
            "data": {
                "id": draft.id,
                "status": draft.status,
                "applied_text": draft.applied_text,
                "updated_at": draft.updated_at.isoformat() if draft.updated_at else "",
            },
        }
    finally:
        db.close()


@router.post("/api/ia/suggestions/{draft_id}/discard", response_class=JSONResponse)
def discard_suggestion_draft(request: Request, draft_id: int, payload: dict = Body(...)):
    db = SessionLocal()
    try:
        IASuggestionDraft.__table__.create(bind=db.get_bind(), checkfirst=True)
        draft = db.query(IASuggestionDraft).filter(IASuggestionDraft.id == int(draft_id)).first()
        if not draft:
            return JSONResponse(status_code=404, content={"success": False, "error": "Sugerencia no encontrada"})
        _require_ia_feature(
            request,
            db,
            feature_key="suggest_objective_text",
            module=str(draft.target_module or "").strip().lower(),
        )
        reason = str(payload.get("reason", "") or "").strip()
        edited = str(payload.get("edited_text", "") or "").strip()
        if edited:
            draft.edited_text = edited
        draft.discard_reason = reason
        draft.status = "discarded"
        draft.updated_at = datetime.utcnow()
        db.commit()
        return {
            "success": True,
            "data": {
                "id": draft.id,
                "status": draft.status,
                "discard_reason": draft.discard_reason,
                "updated_at": draft.updated_at.isoformat() if draft.updated_at else "",
            },
        }
    finally:
        db.close()


@router.post("/api/ia/jobs", response_class=JSONResponse)
def create_ia_job(request: Request, payload: dict = Body(...)):
    module = str(payload.get("module", "") or payload.get("target_module", "")).strip().lower()
    feature_key = str(payload.get("feature_key", "")).strip().lower() or "suggest_objective_text"
    job_type = str(payload.get("job_type", "")).strip().lower() or "suggest_objective_text"
    queue = str(payload.get("queue", "")).strip().lower() or "default"
    max_attempts = int(payload.get("max_attempts", 1) or 1)
    if max_attempts < 1:
        max_attempts = 1
    prompt = str(payload.get("prompt", "") or payload.get("texto", "")).strip()
    if not prompt:
        return JSONResponse(status_code=400, content={"success": False, "error": "Prompt requerido"})
    db = SessionLocal()
    try:
        _require_ia_feature(request, db, feature_key=feature_key, module=module)
        IAJob.__table__.create(bind=db.get_bind(), checkfirst=True)
        role = _current_role(request)
        username = _current_username(request)
        input_payload = {
            "prompt": prompt,
            "module": module,
            "feature_key": feature_key,
            "job_type": job_type,
            "meta": payload.get("meta", {}) if isinstance(payload.get("meta", {}), dict) else {},
        }
        row = IAJob(
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            user_id=str(payload.get("user_id", "") or "").strip() or None,
            username=username or None,
            role=role or None,
            module=module,
            feature_key=feature_key,
            job_type=job_type,
            queue=queue,
            status="pending",
            progress=0,
            attempts=0,
            max_attempts=max_attempts,
            input_payload=json.dumps(input_payload, ensure_ascii=False),
            output_payload="",
            error_message="",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        _enqueue_ia_job(int(row.id))
        return {"success": True, "data": _serialize_job(row)}
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.get("/api/ia/jobs/{job_id}", response_class=JSONResponse)
def get_ia_job(request: Request, job_id: int):
    db = SessionLocal()
    try:
        IAJob.__table__.create(bind=db.get_bind(), checkfirst=True)
        row = db.query(IAJob).filter(IAJob.id == int(job_id)).first()
        if not row:
            return JSONResponse(status_code=404, content={"success": False, "error": "Job no encontrado"})
        role = _current_role(request)
        username = _current_username(request).lower()
        owner = str(row.username or "").strip().lower()
        if role not in {"superadministrador", "administrador"} and owner and owner != username:
            return JSONResponse(status_code=403, content={"success": False, "error": "No autorizado para ver este job"})
        return {"success": True, "data": _serialize_job(row)}
    finally:
        db.close()


@router.get("/api/ia/jobs", response_class=JSONResponse)
def list_ia_jobs(request: Request, status: str = "", module: str = "", limit: int = 50):
    if limit < 1:
        limit = 1
    if limit > 200:
        limit = 200
    db = SessionLocal()
    try:
        IAJob.__table__.create(bind=db.get_bind(), checkfirst=True)
        role = _current_role(request)
        username = _current_username(request).lower()
        query = db.query(IAJob)
        if status:
            query = query.filter(IAJob.status == str(status).strip().lower())
        if module:
            query = query.filter(IAJob.module == str(module).strip().lower())
        if role not in {"superadministrador", "administrador"}:
            query = query.filter(IAJob.username == (username or ""))
        rows = query.order_by(IAJob.created_at.desc(), IAJob.id.desc()).limit(limit).all()
        return {"success": True, "data": [_serialize_job(row) for row in rows]}
    finally:
        db.close()


@router.post("/api/ia/jobs/{job_id}/retry", response_class=JSONResponse)
def retry_ia_job(request: Request, job_id: int):
    db = SessionLocal()
    try:
        IAJob.__table__.create(bind=db.get_bind(), checkfirst=True)
        row = db.query(IAJob).filter(IAJob.id == int(job_id)).first()
        if not row:
            return JSONResponse(status_code=404, content={"success": False, "error": "Job no encontrado"})
        role = _current_role(request)
        username = _current_username(request).lower()
        owner = str(row.username or "").strip().lower()
        if role not in {"superadministrador", "administrador"} and owner and owner != username:
            return JSONResponse(status_code=403, content={"success": False, "error": "No autorizado para reintentar este job"})
        if str(row.status or "").lower() == "in_progress":
            return JSONResponse(status_code=400, content={"success": False, "error": "Job en ejecución"})
        if int(row.attempts or 0) >= int(row.max_attempts or 1):
            return JSONResponse(status_code=400, content={"success": False, "error": "Se alcanzó max_attempts"})
        row.status = "pending"
        row.progress = 0
        row.error_message = ""
        row.started_at = None
        row.finished_at = None
        row.updated_at = datetime.utcnow()
        db.add(row)
        db.commit()
        db.refresh(row)
        _enqueue_ia_job(int(row.id))
        return {"success": True, "data": _serialize_job(row)}
    finally:
        db.close()


@router.post("/api/ia/jobs/{job_id}/cancel", response_class=JSONResponse)
def cancel_ia_job(request: Request, job_id: int):
    db = SessionLocal()
    try:
        IAJob.__table__.create(bind=db.get_bind(), checkfirst=True)
        row = db.query(IAJob).filter(IAJob.id == int(job_id)).first()
        if not row:
            return JSONResponse(status_code=404, content={"success": False, "error": "Job no encontrado"})
        role = _current_role(request)
        username = _current_username(request).lower()
        owner = str(row.username or "").strip().lower()
        if role not in {"superadministrador", "administrador"} and owner and owner != username:
            return JSONResponse(status_code=403, content={"success": False, "error": "No autorizado para cancelar este job"})
        current_status = str(row.status or "").lower()
        if current_status == "in_progress":
            return JSONResponse(status_code=400, content={"success": False, "error": "Job en progreso, no cancelable"})
        if current_status in {"completed", "canceled"}:
            return JSONResponse(status_code=400, content={"success": False, "error": "Job ya finalizado"})
        row.status = "canceled"
        row.progress = 100
        row.finished_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        db.add(row)
        db.commit()
        return {"success": True, "data": _serialize_job(row)}
    finally:
        db.close()


@router.post("/api/v1/ia/suggest/kpi", response_class=JSONResponse)
def v1_suggest_kpi(request: Request, payload: dict = Body(...)):
    db = SessionLocal()
    try:
        _require_ia_feature(request, db, feature_key="suggest_kpi", module="kpis")
        nombre = str(payload.get("nombre", "")).strip()
        objetivo = str(payload.get("objetivo", "")).strip()
        eje = str(payload.get("eje", "")).strip()
        valor_actual = str(payload.get("valor_actual", "")).strip()
        meta = str(payload.get("meta", "")).strip()
        estado = str(payload.get("estado", "")).strip()
        if not (nombre or objetivo or eje):
            return JSONResponse(status_code=400, content={"success": False, "error": "Datos insuficientes para sugerir KPI"})
        prompt = "\n".join([
            "Genera una propuesta de KPI estratégico en español.",
            f"Eje: {eje or 'N/D'}",
            f"Objetivo: {objetivo or 'N/D'}",
            f"Nombre base: {nombre or 'N/D'}",
            f"Valor actual: {valor_actual or 'N/D'}",
            f"Meta: {meta or 'N/D'}",
            f"Estado: {estado or 'N/D'}",
            "Devuelve formato:",
            "Nombre:",
            "Propósito:",
            "Fórmula:",
            "Periodicidad:",
            "Estándar:",
        ])
        result = complete_with_fallback(prompt)
        suggestion = _extract_text_from_provider_result(result).strip()
        return {"success": True, "data": {"suggestion": suggestion}}
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"success": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.post("/api/v1/ia/suggest/activity-text", response_class=JSONResponse)
def v1_suggest_activity_text(request: Request, payload: dict = Body(...)):
    db = SessionLocal()
    try:
        _require_ia_feature(request, db, feature_key="suggest_activity_text", module="poa")
        eje = str(payload.get("eje", "")).strip()
        objetivo = str(payload.get("objetivo", "")).strip()
        actividad = str(payload.get("actividad", "")).strip()
        descripcion = str(payload.get("descripcion", "")).strip()
        if not (objetivo or actividad or descripcion):
            return JSONResponse(status_code=400, content={"success": False, "error": "Datos insuficientes para sugerir actividad"})
        prompt = "\n".join([
            "Mejora la redacción de una actividad POA en español.",
            f"Eje: {eje or 'N/D'}",
            f"Objetivo: {objetivo or 'N/D'}",
            f"Actividad: {actividad or 'N/D'}",
            f"Descripción actual: {descripcion or 'N/D'}",
            "Devuelve solo la descripción final, clara y medible.",
        ])
        result = complete_with_fallback(prompt)
        suggestion = _extract_text_from_provider_result(result).strip()
        return {"success": True, "data": {"suggestion": suggestion}}
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"success": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.post("/api/v1/ia/classify/activity", response_class=JSONResponse)
def v1_classify_activity(request: Request, payload: dict = Body(...)):
    db = SessionLocal()
    try:
        _require_ia_feature(request, db, feature_key="classify_activity", module="poa")
        text_in = " ".join([
            str(payload.get("nombre", "")).strip(),
            str(payload.get("descripcion", "")).strip(),
            str(payload.get("objetivo", "")).strip(),
        ]).strip().lower()
        if not text_in:
            return JSONResponse(status_code=400, content={"success": False, "error": "Texto de actividad requerido"})
        perspective = "Procesos"
        if any(k in text_in for k in ["socio", "cliente", "servicio", "fidel"]):
            perspective = "Socios"
        elif any(k in text_in for k in ["financ", "ingreso", "gasto", "presupuesto", "moros"]):
            perspective = "Financiera"
        elif any(k in text_in for k in ["capacit", "talento", "innov", "aprendiz", "digital"]):
            perspective = "Aprendizaje"
        risk = "medio"
        if any(k in text_in for k in ["urgente", "crítico", "atras", "bloqueo"]):
            risk = "alto"
        elif any(k in text_in for k in ["mantenimiento", "seguimiento", "rutina"]):
            risk = "bajo"
        category = "operativa"
        if any(k in text_in for k in ["política", "gobierno", "normativa", "riesgo"]):
            category = "control"
        elif any(k in text_in for k in ["campaña", "comercial", "marketing"]):
            category = "comercial"
        return {
            "success": True,
            "data": {
                "perspectiva_bsc": perspective,
                "riesgo": risk,
                "categoria": category,
            },
        }
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.post("/api/v1/ia/summarize/document", response_class=JSONResponse)
def v1_summarize_document(request: Request, payload: dict = Body(...)):
    db = SessionLocal()
    try:
        _require_ia_feature(request, db, feature_key="summarize_document", module="reports")
        content = str(payload.get("content", "") or payload.get("texto", "")).strip()
        max_chars = int(payload.get("max_chars", 1200) or 1200)
        if max_chars < 200:
            max_chars = 200
        if max_chars > 5000:
            max_chars = 5000
        if not content:
            return JSONResponse(status_code=400, content={"success": False, "error": "Contenido requerido"})
        prompt = "\n".join([
            "Resume el siguiente documento en español.",
            f"Longitud máxima: {max_chars} caracteres.",
            "Incluye: resumen ejecutivo, hallazgos clave y recomendaciones.",
            "Documento:",
            content[:25000],
        ])
        result = complete_with_fallback(prompt)
        summary = _extract_text_from_provider_result(result).strip()
        if len(summary) > max_chars:
            summary = summary[:max_chars].rstrip() + "..."
        return {"success": True, "data": {"summary": summary}}
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"success": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.get("/api/v1/ia/poa/risk-summary", response_class=JSONResponse)
def v1_poa_risk_summary(request: Request):
    db = SessionLocal()
    try:
        _require_ia_feature(request, db, feature_key="poa_risk_summary", module="poa")
        risk_items = _compute_poa_risk_items(db)
        total = len(risk_items)
        overdue = sum(1 for item in risk_items if item.get("state") == "atrasada")
        in_review = sum(1 for item in risk_items if item.get("state") == "revision")
        in_process = sum(1 for item in risk_items if item.get("state") == "en_proceso")
        no_owner = sum(1 for item in risk_items if not _norm_text(item.get("owner")))
        high = sum(1 for item in risk_items if item.get("severity") == "high")
        medium = sum(1 for item in risk_items if item.get("severity") == "medium")
        low = sum(1 for item in risk_items if item.get("severity") == "low")
        risk_index = round(sum(float(item.get("risk_score") or 0) for item in risk_items) / max(total, 1), 4)
        top_risks = sorted(
            [item for item in risk_items if item.get("severity") in {"high", "medium"}],
            key=lambda item: item.get("risk_score", 0),
            reverse=True,
        )[:10]
        recommendations = _build_ia_recommendations(top_risks, top_n=5)
        return {
            "success": True,
            "data": {
                "total_activities": total,
                "overdue": overdue,
                "in_review": in_review,
                "in_process": in_process,
                "without_owner": no_owner,
                "risk_index": risk_index,
                "risk_bands": {
                    "high": high,
                    "medium": medium,
                    "low": low,
                },
                "top_risks": top_risks,
                "recommendations": recommendations,
                "generated_at": datetime.utcnow().isoformat(),
            },
        }
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"success": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.post("/api/v1/ia/poa/risk-alerts/publish", response_class=JSONResponse)
def v1_poa_publish_risk_alerts(request: Request):
    db = SessionLocal()
    try:
        _require_ia_feature(request, db, feature_key="poa_risk_summary", module="poa")
        risk_items = _compute_poa_risk_items(db)
        top_for_recommendations = sorted(
            [item for item in risk_items if item.get("severity") in {"high", "medium"}],
            key=lambda item: item.get("risk_score", 0),
            reverse=True,
        )[:10]
        recommendations = _build_ia_recommendations(top_for_recommendations, top_n=8)
        persisted = _persist_risk_alerts(db, risk_items, recommendations)
        active_count = int(
            db.execute(
                text("SELECT COUNT(*) FROM ia_poa_risk_alerts WHERE source = 'ia_risk_engine' AND status = 'active'")
            ).scalar()
            or 0
        )
        return {
            "success": True,
            "data": {
                "published": persisted,
                "active_alerts": active_count,
                "recommendations": recommendations,
                "generated_at": datetime.utcnow().isoformat(),
            },
        }
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"success": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.get("/api/v1/ia/poa/risk-alerts", response_class=JSONResponse)
def v1_poa_list_risk_alerts(request: Request, status: str = "active", limit: int = 50):
    if limit < 1:
        limit = 1
    if limit > 300:
        limit = 300
    db = SessionLocal()
    try:
        _require_ia_feature(request, db, feature_key="poa_risk_summary", module="poa")
        _ensure_poa_risk_alerts_table(db)
        norm_status = _norm_text(status).lower()
        params = {"limit": int(limit)}
        where_sql = "WHERE source = 'ia_risk_engine'"
        if norm_status and norm_status != "all":
            where_sql += " AND status = :status"
            params["status"] = norm_status
        rows = db.execute(
            text(
                f"""
                SELECT id, created_at, updated_at, alert_key, activity_id, objective_id, axis_id,
                       severity, risk_score, status, owner, title, message, recommendation, resolved_at
                FROM ia_poa_risk_alerts
                {where_sql}
                ORDER BY
                    CASE severity WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 ELSE 0 END DESC,
                    risk_score DESC,
                    updated_at DESC,
                    id DESC
                LIMIT :limit
                """
            ),
            params,
        ).fetchall()
        data = []
        for row in rows:
            data.append(
                {
                    "id": int(row.id or 0),
                    "created_at": _norm_text(row.created_at),
                    "updated_at": _norm_text(row.updated_at),
                    "alert_key": _norm_text(row.alert_key),
                    "activity_id": int(row.activity_id or 0) if row.activity_id is not None else None,
                    "objective_id": int(row.objective_id or 0) if row.objective_id is not None else None,
                    "axis_id": int(row.axis_id or 0) if row.axis_id is not None else None,
                    "severity": _norm_text(row.severity) or "low",
                    "risk_score": float(row.risk_score or 0),
                    "status": _norm_text(row.status) or "active",
                    "owner": _norm_text(row.owner),
                    "title": _norm_text(row.title),
                    "message": _norm_text(row.message),
                    "recommendation": _norm_text(row.recommendation),
                    "resolved_at": _norm_text(row.resolved_at),
                }
            )
        return {"success": True, "total": len(data), "data": data}
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"success": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.get("/api/v1/ia/reports/executive", response_class=JSONResponse)
def v1_reports_executive(
    request: Request,
    eje_id: str = "",
    objective_id: str = "",
    responsable: str = "",
    status: str = "",
    fecha_desde: str = "",
    fecha_hasta: str = "",
    severity: str = "",
):
    db = SessionLocal()
    try:
        _require_ia_feature(request, db, feature_key="reports_executive", module="reports")
        filters = _normalize_exec_filters(
            {
                "eje_id": eje_id,
                "objective_id": objective_id,
                "responsable": responsable,
                "status": status,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta,
                "severity": severity,
            }
        )
        dataset = _compute_executive_dataset(db, filters)
        return {"success": True, "data": dataset}
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"success": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.post("/api/v1/ia/reports/executive/generate", response_class=JSONResponse)
def v1_generate_executive_report(request: Request, payload: dict = Body(...)):
    db = SessionLocal()
    try:
        _require_ia_feature(request, db, feature_key="reports_executive", module="reports")
        filters = _normalize_exec_filters(payload.get("filters", payload))
        dataset = _compute_executive_dataset(db, filters)
        narrative = _render_exec_narrative(dataset)
        saved = _persist_exec_report(
            db,
            username=_current_username(request),
            role=_current_role(request),
            filters=filters,
            dataset=dataset,
            narrative=narrative,
        )
        return {
            "success": True,
            "data": {
                "report": saved,
                "filters": filters,
                "snapshot": dataset,
                "narrative": narrative,
            },
        }
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"success": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.get("/api/v1/ia/reports/executive/history", response_class=JSONResponse)
def v1_list_executive_reports(request: Request, limit: int = 50):
    if limit < 1:
        limit = 1
    if limit > 300:
        limit = 300
    db = SessionLocal()
    try:
        _require_ia_feature(request, db, feature_key="reports_executive", module="reports")
        _ensure_exec_reports_table(db)
        role = _current_role(request)
        username = _current_username(request)
        where_sql = ""
        params = {"limit": int(limit)}
        if role not in {"superadministrador", "administrador"}:
            where_sql = "WHERE lower(COALESCE(username, '')) = :username"
            params["username"] = username.lower()
        rows = db.execute(
            text(
                f"""
                SELECT id, created_at, updated_at, report_key, version_no, title, username, role, filters_json
                FROM ia_executive_reports
                {where_sql}
                ORDER BY created_at DESC, id DESC
                LIMIT :limit
                """
            ),
            params,
        ).fetchall()
        data = []
        for row in rows:
            data.append(
                {
                    "id": int(row.id or 0),
                    "created_at": _norm_text(row.created_at),
                    "updated_at": _norm_text(row.updated_at),
                    "report_key": _norm_text(row.report_key),
                    "version_no": int(row.version_no or 1),
                    "title": _norm_text(row.title),
                    "username": _norm_text(row.username),
                    "role": _norm_text(row.role),
                    "filters": _json_load(row.filters_json),
                }
            )
        return {"success": True, "total": len(data), "data": data}
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"success": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.get("/api/v1/ia/reports/executive/history/{report_id}", response_class=JSONResponse)
def v1_get_executive_report(request: Request, report_id: int):
    db = SessionLocal()
    try:
        _require_ia_feature(request, db, feature_key="reports_executive", module="reports")
        _ensure_exec_reports_table(db)
        row = db.execute(
            text(
                """
                SELECT id, created_at, updated_at, report_key, version_no, title, username, role,
                       filters_json, snapshot_json, narrative_text, model_name, provider
                FROM ia_executive_reports
                WHERE id = :id
                LIMIT 1
                """
            ),
            {"id": int(report_id)},
        ).fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"success": False, "error": "Reporte no encontrado"})
        role = _current_role(request)
        username = _current_username(request)
        if not _can_read_exec_report(role, username, _norm_text(row.username)):
            return JSONResponse(status_code=403, content={"success": False, "error": "No autorizado"})
        return {
            "success": True,
            "data": {
                "id": int(row.id or 0),
                "created_at": _norm_text(row.created_at),
                "updated_at": _norm_text(row.updated_at),
                "report_key": _norm_text(row.report_key),
                "version_no": int(row.version_no or 1),
                "title": _norm_text(row.title),
                "username": _norm_text(row.username),
                "role": _norm_text(row.role),
                "filters": _json_load(row.filters_json),
                "snapshot": _json_load(row.snapshot_json),
                "narrative": _norm_text(row.narrative_text),
                "model_name": _norm_text(row.model_name),
                "provider": _norm_text(row.provider),
            },
        }
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"success": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.get("/api/v1/ia/reports/executive/history/{report_id}/download")
def v1_download_executive_report(request: Request, report_id: int, format: str = "txt"):
    db = SessionLocal()
    try:
        _require_ia_feature(request, db, feature_key="reports_executive", module="reports")
        _ensure_exec_reports_table(db)
        row = db.execute(
            text(
                """
                SELECT id, created_at, report_key, version_no, title, username, role,
                       filters_json, snapshot_json, narrative_text
                FROM ia_executive_reports
                WHERE id = :id
                LIMIT 1
                """
            ),
            {"id": int(report_id)},
        ).fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"success": False, "error": "Reporte no encontrado"})
        role = _current_role(request)
        username = _current_username(request)
        if not _can_read_exec_report(role, username, _norm_text(row.username)):
            return JSONResponse(status_code=403, content={"success": False, "error": "No autorizado"})
        snapshot = _json_load(row.snapshot_json)
        filters = _json_load(row.filters_json)
        narrative = _norm_text(row.narrative_text)
        file_tag = f"ia_reporte_ejecutivo_{int(row.id or 0)}_v{int(row.version_no or 1)}"
        fmt = _norm_text(format).lower() or "txt"
        if fmt == "json":
            body = json.dumps(
                {
                    "id": int(row.id or 0),
                    "title": _norm_text(row.title),
                    "version_no": int(row.version_no or 1),
                    "created_at": _norm_text(row.created_at),
                    "filters": filters,
                    "snapshot": snapshot,
                    "narrative": narrative,
                },
                ensure_ascii=False,
                indent=2,
            )
            return Response(
                content=body,
                media_type="application/json; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{file_tag}.json"'},
            )
        lines = [
            _norm_text(row.title) or "Reporte Ejecutivo IA",
            f"Versión: {int(row.version_no or 1)}",
            f"Fecha: {_norm_text(row.created_at)}",
            "",
            "Filtros aplicados:",
            json.dumps(filters, ensure_ascii=False, indent=2),
            "",
            "Narrativa ejecutiva:",
            narrative,
            "",
            "Snapshot:",
            json.dumps(snapshot, ensure_ascii=False, indent=2),
            "",
        ]
        body = "\n".join(lines)
        ext = "md" if fmt == "md" else "txt"
        return Response(
            content=body,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{file_tag}.{ext}"'},
        )
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"success": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.post("/api/v1/ia/rag/index-documents", response_class=JSONResponse)
def v1_rag_index_documents(request: Request, payload: dict = Body(...)):
    db = SessionLocal()
    try:
        _require_ia_feature(request, db, feature_key="rag_index", module="conversaciones")
        role = _current_role(request)
        if role not in {"superadministrador", "administrador"}:
            return JSONResponse(status_code=403, content={"success": False, "error": "Solo administradores pueden indexar documentos"})
        _ensure_rag_tables(db)
        from fastapi_modulo.main import DocumentoEvidencia

        limit = int(payload.get("limit", 300) or 300)
        if limit < 1:
            limit = 1
        if limit > 2000:
            limit = 2000
        where_sql, params = _document_access_where(
            request=request,
            role=role,
            username=_current_username(request),
            tenant=_current_tenant(request),
            table_alias="d",
        )
        doc_ids = db.execute(
            text(
                f"""
                SELECT d.id
                FROM documentos_evidencia d
                {where_sql}
                ORDER BY COALESCE(d.updated_at, d.creado_at) DESC, d.id DESC
                LIMIT :limit
                """
            ),
            {**params, "limit": int(limit)},
        ).fetchall()
        created_or_updated = 0
        total_chunks = 0
        errors = []
        for row in doc_ids:
            try:
                doc = db.query(DocumentoEvidencia).filter(DocumentoEvidencia.id == int(row.id or 0)).first()
                if not doc:
                    continue
                result = _upsert_rag_document(db, doc)
                created_or_updated += 1
                total_chunks += int(result.get("chunk_count", 0))
                if created_or_updated % 30 == 0:
                    db.commit()
            except Exception as exc:
                errors.append({"doc_id": int(row.id or 0), "error": str(exc)})
                db.rollback()
        db.commit()
        return {
            "success": True,
            "data": {
                "indexed_documents": int(created_or_updated),
                "indexed_chunks": int(total_chunks),
                "errors": errors[:30],
                "generated_at": datetime.utcnow().isoformat(),
            },
        }
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"success": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.get("/api/v1/ia/rag/index-status", response_class=JSONResponse)
def v1_rag_index_status(request: Request):
    db = SessionLocal()
    try:
        _require_ia_feature(request, db, feature_key="rag_chat", module="conversaciones")
        _ensure_rag_tables(db)
        role = _current_role(request)
        where_sql, params = _document_access_where(
            request=request,
            role=role,
            username=_current_username(request),
            tenant=_current_tenant(request),
            table_alias="d",
        )
        documents = int(
            db.execute(
                text(
                    f"""
                    SELECT COUNT(*)
                    FROM ia_rag_documents d
                    {where_sql}
                    """
                ),
                params,
            ).scalar()
            or 0
        )
        chunks = int(
            db.execute(
                text(
                    f"""
                    SELECT COUNT(*)
                    FROM ia_rag_chunks c
                    JOIN ia_rag_documents d ON d.id = c.rag_document_id
                    {where_sql}
                    """
                ),
                params,
            ).scalar()
            or 0
        )
        last_indexed = db.execute(
            text(
                f"""
                SELECT MAX(d.indexed_at)
                FROM ia_rag_documents d
                {where_sql}
                """
            ),
            params,
        ).scalar()
        return {
            "success": True,
            "data": {
                "documents": documents,
                "chunks": chunks,
                "last_indexed_at": _norm_text(last_indexed),
            },
        }
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"success": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.post("/api/v1/ia/strategic/weekly-refresh", response_class=JSONResponse)
def v1_strategic_weekly_refresh(request: Request, payload: dict = Body(default={})):
    db = SessionLocal()
    try:
        role = _current_role(request)
        if role not in {"superadministrador", "administrador"}:
            return JSONResponse(status_code=403, content={"success": False, "error": "Acceso denegado"})
        force = bool((payload or {}).get("force", True))
        result = _refresh_weekly_strategic_extra_if_due(db, force=force)
        return {"success": True, "data": result}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.post("/api/v1/ia/rag/chat", response_class=JSONResponse)
def v1_rag_chat(request: Request, payload: dict = Body(...)):
    db = SessionLocal()
    try:
        _require_ia_feature(request, db, feature_key="rag_chat", module="conversaciones")
        _ensure_rag_tables(db)
        _purge_expired_rag_messages(db)
        question = _norm_text(payload.get("message") or payload.get("question"))
        if not question:
            return JSONResponse(status_code=400, content={"success": False, "error": "Pregunta requerida"})
        role = _current_role(request)
        username = _current_username(request)
        tenant = _current_tenant(request)
        try:
            _refresh_weekly_strategic_extra_if_due(db, force=False)
        except Exception:
            db.rollback()
        top_k = int(payload.get("top_k", 6) or 6)

        # --- Respuesta conversacional directa (saludos, agradecimientos, etc.) ---
        _CONVERSATIONAL = {
            "hola", "buenos días", "buenos dias", "buenas tardes", "buenas noches",
            "buenas", "hey", "hi", "hello", "qué tal", "que tal", "cómo estás",
            "como estas", "cómo está", "como esta", "gracias", "muchas gracias",
            "ok", "okay", "perfecto", "de acuerdo", "entendido", "listo",
            "adios", "adiós", "hasta luego", "chao",
        }
        _q_lower = question.lower().strip().rstrip("!?.")
        if _q_lower in _CONVERSATIONAL or len(_q_lower.split()) <= 2 and _q_lower in _CONVERSATIONAL:
            _conv_prompt = (
                "Eres un asistente de una organización cooperativa. "
                "Responde de forma breve y natural en español. "
                "Varía tu respuesta según el saludo recibido: si es 'buenos días' responde acorde a la mañana, "
                "si es 'buenas tardes' a la tarde, si es un agradecimiento sé cálido pero distinto cada vez. "
                "NUNCA repitas siempre la misma frase como '¿En qué puedo ayudarte hoy?'. "
                "A veces solo saluda de vuelta sin preguntar nada. "
                "Sé variado, humano y sin emojis a menos que el usuario los use.\n\n"
                f"Usuario: {question}"
            )
            try:
                _conv_answer = _extract_text_from_provider_result(complete_with_fallback(_conv_prompt)).strip()
            except Exception:
                _conv_answer = ""
            if not _conv_answer:
                _conv_answer = "¡Hola! ¿En qué te puedo ayudar?"
            _now = datetime.utcnow().isoformat()
            _conv_id = _norm_text(payload.get("conversation_id")) or f"conv-{uuid.uuid4().hex[:12]}"
            for _role_msg, _text_msg, _cit in [
                ("user", question, "[]"),
                ("assistant", _conv_answer, "[]"),
            ]:
                db.execute(
                    text("""
                        INSERT INTO ia_rag_messages (
                            conversation_id, tenant_id, username, role, message_type, message_text, citations_json, created_at
                        ) VALUES (
                            :conversation_id, :tenant_id, :username, :role, :msg_type, :message_text, :cit, :created_at
                        )
                    """),
                    {"conversation_id": _conv_id, "tenant_id": tenant, "username": username,
                     "role": role, "msg_type": _role_msg, "message_text": _text_msg,
                     "cit": _cit, "created_at": _now},
                )
            db.commit()
            return {
                "success": True,
                "data": {"conversation_id": _conv_id, "answer": _conv_answer, "citations": [], "retrieved_chunks": 0},
            }
        # --- fin respuesta conversacional ---

        context_chunks = _retrieve_rag_context(db, request, role, username, tenant, question, top_k=top_k)
        strategic_chunks = _retrieve_strategic_context(db, question, top_k=max(2, min(top_k, 6)))
        conversation_id = _norm_text(payload.get("conversation_id")) or f"conv-{uuid.uuid4().hex[:12]}"
        if not context_chunks and not strategic_chunks:
            general_prompt = (
                "Eres un asistente amigable de una organización cooperativa. "
                "Responde en español de forma natural, directa y breve. "
                "No inventes datos ni cites documentos. "
                "Si la pregunta es ambigua o no tienes suficiente contexto para responderla bien, "
                "pide una aclaración con una sola pregunta precisa. "
                "Si la pregunta es clara pero no tienes información, dilo en una oración.\n\n"
                f"Pregunta: {question}"
            )
            try:
                answer = _extract_text_from_provider_result(complete_with_fallback(general_prompt)).strip()
            except Exception:
                answer = ""
            if not answer:
                answer = (
                    "Puedo ayudarte de forma general con esta consulta. "
                    "Si deseas una respuesta basada en documentos internos, indexa primero el repositorio RAG."
                )
            now_iso = datetime.utcnow().isoformat()
            db.execute(
                text(
                    """
                    INSERT INTO ia_rag_messages (
                        conversation_id, tenant_id, username, role, message_type, message_text, citations_json, created_at
                    ) VALUES (
                        :conversation_id, :tenant_id, :username, :role, 'user', :message_text, '[]', :created_at
                    )
                    """
                ),
                {
                    "conversation_id": conversation_id,
                    "tenant_id": tenant,
                    "username": username,
                    "role": role,
                    "message_text": question,
                    "created_at": now_iso,
                },
            )
            db.execute(
                text(
                    """
                    INSERT INTO ia_rag_messages (
                        conversation_id, tenant_id, username, role, message_type, message_text, citations_json, created_at
                    ) VALUES (
                        :conversation_id, :tenant_id, :username, :role, 'assistant', :message_text, '[]', :created_at
                    )
                    """
                ),
                {
                    "conversation_id": conversation_id,
                    "tenant_id": tenant,
                    "username": username,
                    "role": role,
                    "message_text": answer,
                    "created_at": now_iso,
                },
            )
            db.commit()
            return {
                "success": True,
                "data": {
                    "conversation_id": conversation_id,
                    "answer": answer,
                    "citations": [],
                    "retrieved_chunks": 0,
                },
            }

        context_lines = []
        citations = []
        seen_docs = set()
        for idx, item in enumerate(context_chunks, start=1):
            source_tag = f"D{idx}"
            content = _norm_text(item.get("content"))
            title = _norm_text(item.get("title"))
            source_doc_id = int(item.get("source_doc_id") or 0)
            context_lines.append(f"[{source_tag}] {title} (doc_id={source_doc_id}): {content[:1200]}")
            if source_doc_id not in seen_docs:
                citations.append(
                    {
                        "source_tag": source_tag,
                        "doc_id": source_doc_id,
                        "title": title,
                        "estado": _norm_text(item.get("estado")),
                        "file_path": _norm_text(item.get("file_path")),
                    }
                )
                seen_docs.add(source_doc_id)
        for idx, item in enumerate(strategic_chunks, start=1):
            source_tag = f"S{idx}"
            title = _norm_text(item.get("title")) or "Base estratégica"
            content = _norm_text(item.get("content"))
            if not content:
                continue
            context_lines.append(f"[{source_tag}] {title}: {content[:1600]}")
            citations.append(
                {
                    "source_tag": source_tag,
                    "doc_id": 0,
                    "title": title,
                    "estado": "base_estrategica",
                    "file_path": "db://strategic_base",
                    "source_type": "strategic_base",
                }
            )

        prompt = (
            "Eres un asistente experto de una organización cooperativa. "
            "Responde en español de forma natural, directa y concisa. "
            "Usa solo la información del contexto. "
            "Si la pregunta es ambigua o incompleta y no puedes responderla con certeza, "
            "no intentes adivinar: haz una sola pregunta de aclaración al usuario. "
            "Si la pregunta es clara pero el contexto no tiene la respuesta, dilo brevemente en una oración. "
            "Para preguntas concretas da la respuesta directamente sin preámbulos. "
            "Incluye citas al final usando etiquetas [D1], [D2], [S1], etc., solo si son relevantes.\n\n"
            f"Pregunta: {question}\n\n"
            "Contexto:\n"
            + "\n\n".join(context_lines)
        )
        answer = _extract_text_from_provider_result(complete_with_fallback(prompt)).strip()
        if not answer:
            answer = "No fue posible generar respuesta con la evidencia disponible."
        now_iso = datetime.utcnow().isoformat()
        db.execute(
            text(
                """
                INSERT INTO ia_rag_messages (
                    conversation_id, tenant_id, username, role, message_type, message_text, citations_json, created_at
                ) VALUES (
                    :conversation_id, :tenant_id, :username, :role, 'user', :message_text, '[]', :created_at
                )
                """
            ),
            {
                "conversation_id": conversation_id,
                "tenant_id": tenant,
                "username": username,
                "role": role,
                "message_text": question,
                "created_at": now_iso,
            },
        )
        db.execute(
            text(
                """
                INSERT INTO ia_rag_messages (
                    conversation_id, tenant_id, username, role, message_type, message_text, citations_json, created_at
                ) VALUES (
                    :conversation_id, :tenant_id, :username, :role, 'assistant', :message_text, :citations_json, :created_at
                )
                """
            ),
            {
                "conversation_id": conversation_id,
                "tenant_id": tenant,
                "username": username,
                "role": role,
                "message_text": answer,
                "citations_json": json.dumps(citations, ensure_ascii=False),
                "created_at": now_iso,
            },
        )
        db.commit()
        return {
            "success": True,
            "data": {
                "conversation_id": conversation_id,
                "answer": answer,
                "citations": citations,
                "retrieved_chunks": len(context_chunks),
            },
        }
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"success": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.get("/api/v1/ia/rag/conversations", response_class=JSONResponse)
def v1_rag_conversations(request: Request, limit: int = 40):
    if limit < 1:
        limit = 1
    if limit > 200:
        limit = 200
    db = SessionLocal()
    try:
        _require_ia_feature(request, db, feature_key="rag_chat", module="conversaciones")
        _ensure_rag_tables(db)
        _purge_expired_rag_messages(db)
        role = _current_role(request)
        username = _current_username(request)
        tenant = _current_tenant(request)
        where_clauses = ["tenant_id = :tenant_id"]
        params = {"tenant_id": tenant, "limit": int(limit)}
        if role not in {"superadministrador", "administrador"}:
            where_clauses.append("lower(COALESCE(username,'')) = :username")
            params["username"] = username.lower()
        where_sql = " WHERE " + " AND ".join(where_clauses)
        rows = db.execute(
            text(
                f"""
                SELECT
                    conversation_id,
                    MAX(created_at) AS last_at,
                    MAX(CASE WHEN message_type='user' THEN message_text ELSE '' END) AS last_question,
                    MAX(CASE WHEN message_type='assistant' THEN message_text ELSE '' END) AS last_answer,
                    MAX(username) AS username
                FROM ia_rag_messages
                {where_sql}
                GROUP BY conversation_id
                ORDER BY last_at DESC
                LIMIT :limit
                """
            ),
            params,
        ).fetchall()
        data = []
        for row in rows:
            data.append(
                {
                    "conversation_id": _norm_text(row.conversation_id),
                    "last_at": _norm_text(row.last_at),
                    "last_question": _norm_text(row.last_question)[:260],
                    "last_answer": _norm_text(row.last_answer)[:260],
                    "username": _norm_text(row.username),
                }
            )
        return {"success": True, "total": len(data), "data": data}
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"success": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.get("/api/v1/ia/rag/conversations/{conversation_id}", response_class=JSONResponse)
def v1_rag_conversation_detail(request: Request, conversation_id: str):
    conv = _norm_text(conversation_id)
    if not conv:
        return JSONResponse(status_code=400, content={"success": False, "error": "conversation_id requerido"})
    db = SessionLocal()
    try:
        _require_ia_feature(request, db, feature_key="rag_chat", module="conversaciones")
        _ensure_rag_tables(db)
        _purge_expired_rag_messages(db)
        role = _current_role(request)
        username = _current_username(request)
        tenant = _current_tenant(request)
        rows = db.execute(
            text(
                """
                SELECT id, conversation_id, tenant_id, username, role, message_type, message_text, citations_json, created_at
                FROM ia_rag_messages
                WHERE conversation_id = :conversation_id
                ORDER BY created_at ASC, id ASC
                """
            ),
            {"conversation_id": conv},
        ).fetchall()
        if not rows:
            return JSONResponse(status_code=404, content={"success": False, "error": "Conversación no encontrada"})
        first = rows[0]
        if role not in {"superadministrador", "administrador"}:
            if _norm_text(first.tenant_id).lower() != tenant.lower():
                return JSONResponse(status_code=403, content={"success": False, "error": "No autorizado"})
            if _norm_text(first.username).lower() != username.lower():
                return JSONResponse(status_code=403, content={"success": False, "error": "No autorizado"})
        data = []
        for row in rows:
            data.append(
                {
                    "id": int(row.id or 0),
                    "conversation_id": _norm_text(row.conversation_id),
                    "username": _norm_text(row.username),
                    "role": _norm_text(row.role),
                    "message_type": _norm_text(row.message_type),
                    "message_text": _norm_text(row.message_text),
                    "citations": _json_load(row.citations_json),
                    "created_at": _norm_text(row.created_at),
                }
            )
        return {"success": True, "total": len(data), "data": data}
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"success": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.get("/api/v1/ia/jobs/{job_id}", response_class=JSONResponse)
def v1_get_job(request: Request, job_id: int):
    return get_ia_job(request, job_id)


@router.get("/api/ia/audit/feed", response_class=JSONResponse)
def ia_audit_feed(request: Request, limit: int = 80):
    if limit < 1:
        limit = 1
    if limit > 400:
        limit = 400
    db = SessionLocal()
    try:
        role = _current_role(request)
        username = _current_username(request).lower()
        IAInteraction.__table__.create(bind=db.get_bind(), checkfirst=True)
        IAJob.__table__.create(bind=db.get_bind(), checkfirst=True)
        _ensure_exec_reports_table(db)
        _ensure_rag_tables(db)

        feed = []

        interactions_q = db.query(IAInteraction).order_by(IAInteraction.created_at.desc(), IAInteraction.id.desc())
        if role not in {"superadministrador", "administrador"}:
            interactions_q = interactions_q.filter(IAInteraction.username == username)
        for row in interactions_q.limit(limit).all():
            feed.append(
                {
                    "source": "interaction",
                    "event_id": f"interaction-{int(row.id or 0)}",
                    "created_at": row.created_at.isoformat() if row.created_at else "",
                    "username": _norm_text(row.username),
                    "feature_key": _norm_text(row.feature_key),
                    "module": "",
                    "status": _norm_text(row.status) or "pending",
                    "provider": "",
                    "model": _norm_text(row.model_name),
                    "prompt_tokens": int(row.tokens_in or 0),
                    "completion_tokens": int(row.tokens_out or 0),
                    "total_tokens": int((row.tokens_in or 0) + (row.tokens_out or 0)),
                    "cost_estimated": float(row.estimated_cost or 0),
                    "message": _norm_text(row.error_message) if _norm_text(row.error_message) else "Interacción IA",
                }
            )

        jobs_q = db.query(IAJob).order_by(IAJob.created_at.desc(), IAJob.id.desc())
        if role not in {"superadministrador", "administrador"}:
            jobs_q = jobs_q.filter(IAJob.username == username)
        for row in jobs_q.limit(limit).all():
            output = _json_load(row.output_payload)
            usage = output.get("usage", {}) if isinstance(output.get("usage", {}), dict) else {}
            feed.append(
                {
                    "source": "job",
                    "event_id": f"job-{int(row.id or 0)}",
                    "created_at": row.created_at.isoformat() if row.created_at else "",
                    "username": _norm_text(row.username),
                    "feature_key": _norm_text(row.feature_key),
                    "module": _norm_text(row.module),
                    "status": _norm_text(row.status) or "pending",
                    "provider": _norm_text(row.provider),
                    "model": _norm_text(row.model_name),
                    "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
                    "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
                    "total_tokens": int(usage.get("total_tokens", 0) or 0),
                    "cost_estimated": float(output.get("cost_estimated", 0) or 0),
                    "message": _norm_text(row.error_message) if _norm_text(row.error_message) else f"Job {row.job_type or ''}".strip(),
                }
            )

        report_where = ""
        report_params = {"limit": int(limit)}
        if role not in {"superadministrador", "administrador"}:
            report_where = "WHERE lower(COALESCE(username,'')) = :username"
            report_params["username"] = username
        reports = db.execute(
            text(
                f"""
                SELECT id, created_at, username, role, title, model_name, provider
                FROM ia_executive_reports
                {report_where}
                ORDER BY created_at DESC, id DESC
                LIMIT :limit
                """
            ),
            report_params,
        ).fetchall()
        for row in reports:
            feed.append(
                {
                    "source": "report",
                    "event_id": f"report-{int(row.id or 0)}",
                    "created_at": _norm_text(row.created_at),
                    "username": _norm_text(row.username),
                    "feature_key": "reports_executive",
                    "module": "reports",
                    "status": "generated",
                    "provider": _norm_text(row.provider),
                    "model": _norm_text(row.model_name),
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "cost_estimated": 0.0,
                    "message": _norm_text(row.title) or "Reporte ejecutivo IA",
                }
            )

        rag_where = "WHERE message_type = 'assistant' AND lower(COALESCE(tenant_id,'')) = :tenant_id"
        rag_params = {"tenant_id": _current_tenant(request), "limit": int(limit)}
        if role not in {"superadministrador", "administrador"}:
            rag_where += " AND lower(COALESCE(username,'')) = :username"
            rag_params["username"] = username
        rag_rows = db.execute(
            text(
                f"""
                SELECT id, created_at, username, message_text
                FROM ia_rag_messages
                {rag_where}
                ORDER BY created_at DESC, id DESC
                LIMIT :limit
                """
            ),
            rag_params,
        ).fetchall()
        for row in rag_rows:
            feed.append(
                {
                    "source": "rag_chat",
                    "event_id": f"rag-{int(row.id or 0)}",
                    "created_at": _norm_text(row.created_at),
                    "username": _norm_text(row.username),
                    "feature_key": "rag_chat",
                    "module": "conversaciones",
                    "status": "completed",
                    "provider": "",
                    "model": "",
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "cost_estimated": 0.0,
                    "message": _norm_text(row.message_text)[:240],
                }
            )

        feed.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        final = feed[: int(limit)]
        return {"success": True, "total": len(final), "data": final}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.get("/api/ia/audit/summary", response_class=JSONResponse)
def ia_audit_summary(request: Request, days: int = 30):
    if days < 1:
        days = 1
    if days > 365:
        days = 365
    db = SessionLocal()
    try:
        role = _current_role(request)
        username = _current_username(request).lower()
        IAInteraction.__table__.create(bind=db.get_bind(), checkfirst=True)
        IAJob.__table__.create(bind=db.get_bind(), checkfirst=True)

        since_iso = (datetime.utcnow() - timedelta(days=int(days))).isoformat()
        params = {"since": since_iso}
        where_user_interaction = ""
        where_user_jobs = ""
        if role not in {"superadministrador", "administrador"}:
            where_user_interaction = " AND lower(COALESCE(username,'')) = :username"
            where_user_jobs = " AND lower(COALESCE(username,'')) = :username"
            params["username"] = username

        interactions_total = int(
            db.execute(
                text(
                    f"""
                    SELECT COUNT(*)
                    FROM ia_interactions
                    WHERE COALESCE(created_at, '') >= :since
                    {where_user_interaction}
                    """
                ),
                params,
            ).scalar()
            or 0
        )
        interactions_error = int(
            db.execute(
                text(
                    f"""
                    SELECT COUNT(*)
                    FROM ia_interactions
                    WHERE COALESCE(created_at, '') >= :since
                      AND lower(COALESCE(status,'')) = 'error'
                    {where_user_interaction}
                    """
                ),
                params,
            ).scalar()
            or 0
        )
        jobs_total = int(
            db.execute(
                text(
                    f"""
                    SELECT COUNT(*)
                    FROM ia_jobs
                    WHERE COALESCE(created_at, '') >= :since
                    {where_user_jobs}
                    """
                ),
                params,
            ).scalar()
            or 0
        )
        jobs_error = int(
            db.execute(
                text(
                    f"""
                    SELECT COUNT(*)
                    FROM ia_jobs
                    WHERE COALESCE(created_at, '') >= :since
                      AND lower(COALESCE(status,'')) = 'error'
                    {where_user_jobs}
                    """
                ),
                params,
            ).scalar()
            or 0
        )
        token_row = db.execute(
            text(
                f"""
                SELECT
                    COALESCE(SUM(COALESCE(tokens_in,0)),0) AS tokens_in,
                    COALESCE(SUM(COALESCE(tokens_out,0)),0) AS tokens_out,
                    COALESCE(SUM(COALESCE(estimated_cost,0)),0) AS cost_total
                FROM ia_interactions
                WHERE COALESCE(created_at, '') >= :since
                {where_user_interaction}
                """
            ),
            params,
        ).fetchone()
        tokens_in = int((token_row.tokens_in if token_row else 0) or 0)
        tokens_out = int((token_row.tokens_out if token_row else 0) or 0)
        cost_total = float((token_row.cost_total if token_row else 0) or 0.0)
        operations_total = interactions_total + jobs_total
        operations_error = interactions_error + jobs_error
        error_rate = round((operations_error / operations_total) * 100, 2) if operations_total else 0.0
        return {
            "success": True,
            "data": {
                "days": int(days),
                "since": since_iso,
                "operations_total": operations_total,
                "operations_error": operations_error,
                "error_rate_pct": error_rate,
                "interactions_total": interactions_total,
                "jobs_total": jobs_total,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "tokens_total": int(tokens_in + tokens_out),
                "cost_total_estimated": round(cost_total, 8),
            },
        }
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.get("/api/ia/flags", response_class=JSONResponse)
def ia_flags_status(request: Request, module: str = "", feature_key: str = "suggest_objective_text"):
    db = SessionLocal()
    try:
        role = _current_role(request)
        enabled = _resolve_ia_feature_enabled(
            db,
            role=role,
            feature_key=str(feature_key or "").strip().lower() or "suggest_objective_text",
            module=str(module or "").strip().lower(),
        )
        return {
            "success": True,
            "data": {
                "role": role,
                "module": str(module or "").strip().lower(),
                "feature_key": str(feature_key or "").strip().lower() or "suggest_objective_text",
                "enabled": bool(enabled),
            },
        }
    finally:
        db.close()


@router.get("/api/ia/feature-flags", response_class=JSONResponse)
def list_ia_feature_flags(request: Request):
    if not _is_admin_like(request):
        return JSONResponse(status_code=403, content={"success": False, "error": "Acceso denegado"})
    db = SessionLocal()
    try:
        IAFeatureFlag.__table__.create(bind=db.get_bind(), checkfirst=True)
        rows = db.query(IAFeatureFlag).order_by(IAFeatureFlag.feature_key.asc(), IAFeatureFlag.module.asc(), IAFeatureFlag.role.asc(), IAFeatureFlag.id.asc()).all()
        return {
            "success": True,
            "data": [
                {
                    "id": int(row.id or 0),
                    "feature_key": str(row.feature_key or ""),
                    "enabled": bool(int(row.enabled or 0)),
                    "role": str(row.role or ""),
                    "module": str(row.module or ""),
                    "updated_at": row.updated_at.isoformat() if row.updated_at else "",
                }
                for row in rows
            ],
        }
    finally:
        db.close()


@router.post("/api/ia/feature-flags", response_class=JSONResponse)
def upsert_ia_feature_flag(request: Request, payload: dict = Body(...)):
    if not _is_admin_like(request):
        return JSONResponse(status_code=403, content={"success": False, "error": "Acceso denegado"})
    feature_key = str(payload.get("feature_key", "")).strip().lower()
    role = _normalize_role_name(str(payload.get("role", "")).strip()) if str(payload.get("role", "")).strip() else ""
    module = str(payload.get("module", "")).strip().lower()
    enabled = 1 if bool(payload.get("enabled", True)) else 0
    if not feature_key:
        return JSONResponse(status_code=400, content={"success": False, "error": "feature_key requerido"})
    db = SessionLocal()
    try:
        IAFeatureFlag.__table__.create(bind=db.get_bind(), checkfirst=True)
        row = (
            db.query(IAFeatureFlag)
            .filter(
                IAFeatureFlag.feature_key == feature_key,
                IAFeatureFlag.role == (role or None),
                IAFeatureFlag.module == (module or None),
            )
            .first()
        )
        if row:
            row.enabled = enabled
            row.updated_at = datetime.utcnow()
            db.add(row)
        else:
            row = IAFeatureFlag(
                feature_key=feature_key,
                enabled=enabled,
                role=role or None,
                module=module or None,
                updated_at=datetime.utcnow(),
            )
            db.add(row)
        db.commit()
        db.refresh(row)
        return {
            "success": True,
            "data": {
                "id": int(row.id or 0),
                "feature_key": str(row.feature_key or ""),
                "enabled": bool(int(row.enabled or 0)),
                "role": str(row.role or ""),
                "module": str(row.module or ""),
                "updated_at": row.updated_at.isoformat() if row.updated_at else "",
            },
        }
    finally:
        db.close()


@router.post("/api/ia/feature-flags/{flag_id}/delete", response_class=JSONResponse)
def delete_ia_feature_flag(request: Request, flag_id: int):
    if not _is_admin_like(request):
        return JSONResponse(status_code=403, content={"success": False, "error": "Acceso denegado"})
    db = SessionLocal()
    try:
        IAFeatureFlag.__table__.create(bind=db.get_bind(), checkfirst=True)
        row = db.query(IAFeatureFlag).filter(IAFeatureFlag.id == int(flag_id)).first()
        if not row:
            return JSONResponse(status_code=404, content={"success": False, "error": "Regla no encontrada"})
        db.delete(row)
        db.commit()
        return {"success": True}
    finally:
        db.close()

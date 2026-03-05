"""
Módulo de conversaciones directas entre usuarios.
Toda la lógica queda aquí; main.py solo incluye el router.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from fastapi_modulo.db import SessionLocal

router = APIRouter()

# ---------------------------------------------------------------------------
# Tabla única para mensajes directos entre usuarios
# ---------------------------------------------------------------------------
_DDL_DIRECT_MESSAGES = """
CREATE TABLE IF NOT EXISTS user_direct_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT    NOT NULL,
    from_username   TEXT    NOT NULL,
    to_usernames    TEXT    NOT NULL DEFAULT '[]',
    message_text    TEXT    NOT NULL DEFAULT '',
    is_read         INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL
)
"""
_DDL_INDEX_CONV = "CREATE INDEX IF NOT EXISTS ix_udm_conv ON user_direct_messages(conversation_id, created_at)"
_DDL_INDEX_FROM = "CREATE INDEX IF NOT EXISTS ix_udm_from ON user_direct_messages(from_username, created_at)"
_DDL_INDEX_READ = "CREATE INDEX IF NOT EXISTS ix_udm_read ON user_direct_messages(to_usernames, is_read)"


def _ensure_tables(db) -> None:
    db.execute(text(_DDL_DIRECT_MESSAGES))
    db.execute(text(_DDL_INDEX_CONV))
    db.execute(text(_DDL_INDEX_FROM))
    db.execute(text(_DDL_INDEX_READ))
    db.commit()


# ---------------------------------------------------------------------------
# Helpers de sesión / auth (misma estrategia que el módulo IA)
# ---------------------------------------------------------------------------
def _me(request: Request) -> str:
    u = getattr(request.state, "user_name", None) or request.cookies.get("user_name") or ""
    return str(u).strip().lower()


def _role(request: Request) -> str:
    r = getattr(request.state, "user_role", None) or request.cookies.get("user_role") or ""
    return str(r).strip().lower()


def _is_admin(request: Request) -> bool:
    return _role(request) in {"superadministrador", "administrador"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------------------
# conversation_id canónico para DMs: dm-{user_a}_{user_b}  (orden alfabético)
# ---------------------------------------------------------------------------
def _dm_conv_id(user_a: str, user_b: str) -> str:
    a, b = sorted([user_a.strip().lower(), user_b.strip().lower()])
    return f"dm-{a}_{b}"


# ---------------------------------------------------------------------------
# Endpoint: listar usuarios activos (para el selector de contacto)
# ---------------------------------------------------------------------------
@router.get("/api/v1/conversaciones/users", response_class=JSONResponse)
def list_users(request: Request):
    me = _me(request)
    if not me:
        return JSONResponse(status_code=401, content={"success": False, "error": "No autenticado"})
    db = SessionLocal()
    try:
        rows = db.execute(
            text(
                """
                SELECT username, full_name, role, imagen
                FROM users
                WHERE is_active = 1
                  AND LOWER(COALESCE(username,'')) != :me
                ORDER BY full_name ASC
                """
            ),
            {"me": me},
        ).fetchall()
        data = [
            {
                "username": str(r.username or ""),
                "full_name": str(r.full_name or r.username or ""),
                "role": str(r.role or ""),
                "imagen": str(r.imagen or "") if r.imagen else "",
            }
            for r in rows
        ]
        return {"success": True, "data": data}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Endpoint: listar mis conversaciones directas
# ---------------------------------------------------------------------------
@router.get("/api/v1/conversaciones/direct", response_class=JSONResponse)
def list_direct_conversations(request: Request):
    me = _me(request)
    if not me:
        return JSONResponse(status_code=401, content={"success": False, "error": "No autenticado"})
    db = SessionLocal()
    try:
        _ensure_tables(db)
        # Recupera la última actividad de cada conversación donde participo
        rows = db.execute(
            text(
                """
                SELECT
                    conversation_id,
                    MAX(created_at)   AS last_at,
                    MAX(CASE WHEN from_username = :me THEN message_text ELSE '' END) AS last_sent,
                    MAX(CASE WHEN from_username != :me THEN message_text ELSE '' END) AS last_received,
                    MAX(CASE WHEN from_username != :me THEN from_username ELSE '' END) AS other_user,
                    SUM(CASE WHEN is_read=0 AND from_username != :me THEN 1 ELSE 0 END) AS unread
                FROM user_direct_messages
                WHERE conversation_id LIKE 'dm-%'
                  AND (from_username = :me
                       OR to_usernames LIKE :me_pattern)
                GROUP BY conversation_id
                ORDER BY last_at DESC
                LIMIT 100
                """
            ),
            {"me": me, "me_pattern": f"%{me}%"},
        ).fetchall()

        data = []
        for r in rows:
            # Extraer el otro usuario del id `dm-a_b`
            other = str(r.other_user or "").strip()
            if not other:
                # Derivar desde el conversation_id
                parts = str(r.conversation_id or "").replace("dm-", "").split("_")
                other = next((p for p in parts if p != me), parts[0] if parts else "?")
            last_msg = str(r.last_received or r.last_sent or "")
            data.append({
                "conversation_id": str(r.conversation_id or ""),
                "other_user": other,
                "last_at": str(r.last_at or ""),
                "last_message": last_msg[:260],
                "unread": int(r.unread or 0),
            })
        return {"success": True, "data": data}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Endpoint: mensajes de una conversación
# ---------------------------------------------------------------------------
@router.get("/api/v1/conversaciones/direct/{conv_id:path}", response_class=JSONResponse)
def get_direct_conversation(request: Request, conv_id: str):
    me = _me(request)
    if not me:
        return JSONResponse(status_code=401, content={"success": False, "error": "No autenticado"})
    conv = str(conv_id or "").strip()
    if not conv:
        return JSONResponse(status_code=400, content={"success": False, "error": "conv_id requerido"})
    db = SessionLocal()
    try:
        _ensure_tables(db)
        # Verificar participación (salvo admin)
        if not _is_admin(request):
            count = db.execute(
                text(
                    "SELECT COUNT(*) FROM user_direct_messages "
                    "WHERE conversation_id=:conv AND (from_username=:me OR to_usernames LIKE :pat)"
                ),
                {"conv": conv, "me": me, "pat": f"%{me}%"},
            ).scalar()
            if not count:
                return JSONResponse(status_code=403, content={"success": False, "error": "No autorizado"})

        rows = db.execute(
            text(
                "SELECT id, from_username, to_usernames, message_text, is_read, created_at "
                "FROM user_direct_messages "
                "WHERE conversation_id = :conv "
                "ORDER BY created_at ASC, id ASC"
            ),
            {"conv": conv},
        ).fetchall()

        # Marcar como leídos los mensajes recibidos
        db.execute(
            text(
                "UPDATE user_direct_messages SET is_read=1 "
                "WHERE conversation_id=:conv AND from_username!=:me AND is_read=0"
            ),
            {"conv": conv, "me": me},
        )
        db.commit()

        data = [
            {
                "id": int(r.id or 0),
                "from_username": str(r.from_username or ""),
                "to_usernames": _safe_json(r.to_usernames, []),
                "message_text": str(r.message_text or ""),
                "is_read": bool(r.is_read),
                "created_at": str(r.created_at or ""),
                "is_mine": str(r.from_username or "").lower() == me,
            }
            for r in rows
        ]
        return {"success": True, "data": data}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Endpoint: enviar un mensaje directo
# ---------------------------------------------------------------------------
@router.post("/api/v1/conversaciones/direct/send", response_class=JSONResponse)
def send_direct_message(request: Request, payload: dict = Body(...)):
    me = _me(request)
    if not me:
        return JSONResponse(status_code=401, content={"success": False, "error": "No autenticado"})

    to_user = str(payload.get("to_username") or "").strip().lower()
    conv_id = str(payload.get("conversation_id") or "").strip()
    message = str(payload.get("message") or "").strip()

    if not message:
        return JSONResponse(status_code=400, content={"success": False, "error": "Mensaje vacío"})
    if not to_user and not conv_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "to_username o conversation_id requerido"})

    # Derivar conversation_id si no viene explícito
    if not conv_id:
        conv_id = _dm_conv_id(me, to_user)

    # Derivar to_user desde conv_id si no vino
    if not to_user:
        parts = conv_id.replace("dm-", "").split("_")
        to_user = next((p for p in parts if p != me), parts[0] if parts else "")

    db = SessionLocal()
    try:
        _ensure_tables(db)
        db.execute(
            text(
                "INSERT INTO user_direct_messages "
                "(conversation_id, from_username, to_usernames, message_text, is_read, created_at) "
                "VALUES (:conv, :from_u, :to_u, :msg, 0, :ts)"
            ),
            {
                "conv": conv_id,
                "from_u": me,
                "to_u": json.dumps([to_user], ensure_ascii=False),
                "msg": message,
                "ts": _now_iso(),
            },
        )
        db.commit()
        return {"success": True, "data": {"conversation_id": conv_id}}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Endpoint: eliminar conversación (solo participante o admin)
# ---------------------------------------------------------------------------
@router.delete("/api/v1/conversaciones/direct/{conv_id:path}", response_class=JSONResponse)
def delete_direct_conversation(request: Request, conv_id: str):
    me = _me(request)
    if not me:
        return JSONResponse(status_code=401, content={"success": False, "error": "No autenticado"})
    conv = str(conv_id or "").strip()
    if not conv:
        return JSONResponse(status_code=400, content={"success": False, "error": "conv_id requerido"})
    db = SessionLocal()
    try:
        _ensure_tables(db)
        if not _is_admin(request):
            count = db.execute(
                text(
                    "SELECT COUNT(*) FROM user_direct_messages "
                    "WHERE conversation_id=:conv AND (from_username=:me OR to_usernames LIKE :pat)"
                ),
                {"conv": conv, "me": me, "pat": f"%{me}%"},
            ).scalar()
            if not count:
                return JSONResponse(status_code=403, content={"success": False, "error": "No autorizado"})
        db.execute(text("DELETE FROM user_direct_messages WHERE conversation_id=:conv"), {"conv": conv})
        db.commit()
        return {"success": True}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Endpoint: conteo de mensajes no leídos
# ---------------------------------------------------------------------------
@router.get("/api/v1/conversaciones/unread-count", response_class=JSONResponse)
def unread_count(request: Request):
    me = _me(request)
    if not me:
        return {"success": True, "data": {"count": 0}}
    db = SessionLocal()
    try:
        _ensure_tables(db)
        count = db.execute(
            text(
                "SELECT COUNT(*) FROM user_direct_messages "
                "WHERE is_read=0 AND from_username!=:me AND to_usernames LIKE :pat"
            ),
            {"me": me, "pat": f"%{me}%"},
        ).scalar()
        return {"success": True, "data": {"count": int(count or 0)}}
    except Exception:
        return {"success": True, "data": {"count": 0}}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Helper privado
# ---------------------------------------------------------------------------
def _safe_json(value, default):
    try:
        return json.loads(str(value or ""))
    except Exception:
        return default

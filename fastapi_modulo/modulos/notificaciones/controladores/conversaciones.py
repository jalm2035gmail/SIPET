"""
Modulo de conversaciones entre usuarios.
Toda la logica de permisos, grupos y notificaciones flotantes queda aqui.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from fastapi_modulo.db import SessionLocal

router = APIRouter()
_MODULE_ROOT = os.path.dirname(os.path.dirname(__file__))
_ACCESS_CONFIG_PATH = os.path.join(_MODULE_ROOT, "conversation_access_config.json")

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
_DDL_GROUPS = """
CREATE TABLE IF NOT EXISTS conversation_groups (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id  TEXT    NOT NULL UNIQUE,
    group_name       TEXT    NOT NULL,
    created_by       TEXT    NOT NULL,
    member_usernames TEXT    NOT NULL DEFAULT '[]',
    created_at       TEXT    NOT NULL
)
"""
_DDL_GROUP_MESSAGES = """
CREATE TABLE IF NOT EXISTS conversation_group_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT    NOT NULL,
    from_username   TEXT    NOT NULL,
    to_usernames    TEXT    NOT NULL DEFAULT '[]',
    message_text    TEXT    NOT NULL DEFAULT '',
    is_read         INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL
)
"""
_DDL_NOTIFICATIONS = """
CREATE TABLE IF NOT EXISTS conversation_notifications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    from_username   TEXT    NOT NULL,
    to_usernames    TEXT    NOT NULL DEFAULT '[]',
    message_text    TEXT    NOT NULL DEFAULT '',
    scope           TEXT    NOT NULL DEFAULT 'conversation',
    conversation_id TEXT    NOT NULL DEFAULT '',
    is_read         INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL
)
"""
_DDL_INDEXES = (
    "CREATE INDEX IF NOT EXISTS ix_udm_conv ON user_direct_messages(conversation_id, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_udm_from ON user_direct_messages(from_username, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_udm_read ON user_direct_messages(to_usernames, is_read)",
    "CREATE INDEX IF NOT EXISTS ix_cg_conv ON conversation_groups(conversation_id)",
    "CREATE INDEX IF NOT EXISTS ix_cgm_conv ON conversation_group_messages(conversation_id, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_cgm_read ON conversation_group_messages(to_usernames, is_read)",
    "CREATE INDEX IF NOT EXISTS ix_cn_to_read ON conversation_notifications(to_usernames, is_read, created_at)",
)


def _ensure_tables(db) -> None:
    db.execute(text(_DDL_DIRECT_MESSAGES))
    db.execute(text(_DDL_GROUPS))
    db.execute(text(_DDL_GROUP_MESSAGES))
    db.execute(text(_DDL_NOTIFICATIONS))
    for ddl in _DDL_INDEXES:
        db.execute(text(ddl))
    db.commit()


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


def _safe_json(value: Any, default: Any):
    try:
        return json.loads(str(value or ""))
    except Exception:
        return default


def _clean_usernames(raw_values: Any) -> list[str]:
    if not isinstance(raw_values, list):
        return []
    clean: list[str] = []
    seen = set()
    for item in raw_values:
        name = str(item or "").strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        clean.append(name)
    return clean


def _dm_conv_id(user_a: str, user_b: str) -> str:
    a, b = sorted([user_a.strip().lower(), user_b.strip().lower()])
    return f"dm-{a}_{b}"


def _load_colab_meta() -> dict[str, Any]:
    app_env = (os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "development").strip().lower()
    sipet_data_dir = (os.environ.get("SIPET_DATA_DIR") or os.path.expanduser("~/.sipet/data")).strip()
    runtime_dir = (os.environ.get("RUNTIME_STORE_DIR") or os.path.join(sipet_data_dir, "runtime_store", app_env)).strip()
    meta_path = os.environ.get("COLAB_META_PATH") or os.path.join(runtime_dir, "colaboradores_meta.json")
    try:
        with open(meta_path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
            return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _normalize_conversation_access(raw_access: Any) -> dict[str, Any]:
    access = raw_access if isinstance(raw_access, dict) else {}
    role = str(access.get("role") or access.get("rol") or "").strip().lower()
    if role == "sin_acceso":
        role = ""
    if role not in {"", "usuario", "administrador"}:
        role = ""
    notification_scope = str(access.get("notification_scope") or access.get("scope") or "").strip().lower()
    if notification_scope not in {"", "department", "company"}:
        notification_scope = ""
    if role != "administrador" and notification_scope == "company":
        notification_scope = "department"
    if not bool(access.get("can_send_notifications", False)):
        notification_scope = ""
    return {
        "role": role,
        "can_create_groups": bool(access.get("can_create_groups", False)),
        "can_send_notifications": bool(access.get("can_send_notifications", False)),
        "notification_scope": notification_scope,
    }


def _conversation_access_for_username(db, username: str) -> dict[str, Any]:
    user = db.execute(
        text(
            """
            SELECT id, username, full_name, role, imagen
            FROM users
            WHERE LOWER(COALESCE(username,'')) = :username
            LIMIT 1
            """
        ),
        {"username": str(username or "").strip().lower()},
    ).fetchone()
    if not user:
        return _normalize_conversation_access(None)
    meta = _load_colab_meta()
    entry = meta.get(str(user.id), {}) if isinstance(meta, dict) else {}
    return _normalize_conversation_access(entry.get("conversation_access"))


def _module_user_row(db, username: str):
    return db.execute(
        text(
            """
            SELECT id, username, full_name, role, imagen
            FROM users
            WHERE LOWER(COALESCE(username,'')) = :username
            LIMIT 1
            """
        ),
        {"username": str(username or "").strip().lower()},
    ).fetchone()


def _module_users(db, exclude_username: str = "") -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT id, username, full_name, role, imagen
                 , departamento
            FROM users
            WHERE is_active = 1
            ORDER BY full_name ASC, username ASC
            """
        )
    ).fetchall()
    meta = _load_colab_meta()
    data: list[dict[str, Any]] = []
    exclude = str(exclude_username or "").strip().lower()
    for row in rows:
        username = str(row.username or "").strip().lower()
        if not username or username == exclude:
            continue
        entry = meta.get(str(row.id), {}) if isinstance(meta, dict) else {}
        access = _normalize_conversation_access(entry.get("conversation_access"))
        if not access.get("role"):
            continue
        data.append(
            {
                "id": int(row.id or 0),
                "username": username,
                "full_name": str(row.full_name or row.username or ""),
                "role": str(row.role or ""),
                "imagen": str(row.imagen or "") if row.imagen else "",
                "departamento": str(row.departamento or ""),
                "conversation_access": access,
            }
        )
    return data


def _department_for_username(db, username: str) -> str:
    row = db.execute(
        text(
            """
            SELECT departamento
            FROM users
            WHERE LOWER(COALESCE(username,'')) = :username
            LIMIT 1
            """
        ),
        {"username": str(username or "").strip().lower()},
    ).fetchone()
    return str(row.departamento or "").strip() if row else ""


def _notification_recipients_for_scope(db, sender_username: str, scope: str) -> list[str]:
    normalized_scope = str(scope or "").strip().lower()
    if normalized_scope == "company":
        return [user["username"] for user in _module_users(db, exclude_username=sender_username)]
    if normalized_scope == "department":
        sender_department = _department_for_username(db, sender_username)
        if not sender_department:
            return []
        users = _module_users(db, exclude_username=sender_username)
        return [
            user["username"]
            for user in users
            if str(user.get("departamento") or "").strip().lower() == sender_department.strip().lower()
        ]
    return []


def _require_module_access(request: Request):
    me = _me(request)
    if not me:
        return None, JSONResponse(status_code=401, content={"success": False, "error": "No autenticado"})
    db = SessionLocal()
    try:
        _ensure_tables(db)
        access = _conversation_access_for_username(db, me)
        if _is_admin(request) and not access.get("role"):
            access = {"role": "administrador", "can_create_groups": True, "can_send_notifications": True}
        if not access.get("role"):
            return None, JSONResponse(status_code=403, content={"success": False, "error": "Sin acceso a Conversaciones"})
        return access, None
    finally:
        db.close()


def _group_members(db, conversation_id: str) -> list[str]:
    row = db.execute(
        text("SELECT member_usernames FROM conversation_groups WHERE conversation_id = :conv LIMIT 1"),
        {"conv": conversation_id},
    ).fetchone()
    if not row:
        return []
    return _clean_usernames(_safe_json(row.member_usernames, []))


def _conversation_participants(db, conversation_id: str, me: str) -> list[str]:
    conv = str(conversation_id or "").strip()
    if conv.startswith("dm-"):
        users = [item for item in conv.replace("dm-", "").split("_") if item]
        return _clean_usernames(users)
    if conv.startswith("grp-"):
        return _group_members(db, conv)
    return [me] if me else []


def _can_access_conversation(db, request: Request, conversation_id: str, me: str) -> bool:
    if _is_admin(request):
        return True
    conv = str(conversation_id or "").strip()
    if conv.startswith("dm-"):
        participants = _conversation_participants(db, conv, me)
        return me in participants
    if conv.startswith("grp-"):
        return me in _group_members(db, conv)
    return False


def _send_floating_notification(db, from_username: str, recipients: list[str], message: str, scope: str, conversation_id: str = "") -> None:
    clean_recipients = _clean_usernames(recipients)
    if not clean_recipients:
        return
    db.execute(
        text(
            """
            INSERT INTO conversation_notifications
            (from_username, to_usernames, message_text, scope, conversation_id, is_read, created_at)
            VALUES (:from_u, :to_u, :msg, :scope, :conv, 0, :ts)
            """
        ),
        {
            "from_u": str(from_username or "").strip().lower(),
            "to_u": json.dumps(clean_recipients, ensure_ascii=False),
            "msg": str(message or "").strip(),
            "scope": str(scope or "conversation").strip(),
            "conv": str(conversation_id or "").strip(),
            "ts": _now_iso(),
        },
    )


def _load_conversation_access_config() -> dict[str, Any]:
    try:
        with open(_ACCESS_CONFIG_PATH, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


@router.get("/api/v1/conversaciones/access-config", response_class=JSONResponse)
def get_conversation_access_config(request: Request):
    return {"success": True, "data": _load_conversation_access_config()}


@router.get("/api/v1/conversaciones/access", response_class=JSONResponse)
def get_conversation_access(request: Request):
    access, error = _require_module_access(request)
    if error:
        return error
    return {"success": True, "data": access}


@router.get("/api/v1/conversaciones/users", response_class=JSONResponse)
def list_users(request: Request):
    access, error = _require_module_access(request)
    if error:
        return error
    db = SessionLocal()
    try:
        _ensure_tables(db)
        return {"success": True, "data": _module_users(db, exclude_username=_me(request)), "access": access}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.get("/api/v1/conversaciones/direct", response_class=JSONResponse)
def list_direct_conversations(request: Request):
    access, error = _require_module_access(request)
    if error:
        return error
    me = _me(request)
    db = SessionLocal()
    try:
        _ensure_tables(db)
        rows = db.execute(
            text(
                """
                SELECT
                    conversation_id,
                    MAX(created_at) AS last_at,
                    MAX(CASE WHEN from_username = :me THEN message_text ELSE '' END) AS last_sent,
                    MAX(CASE WHEN from_username != :me THEN message_text ELSE '' END) AS last_received,
                    MAX(CASE WHEN from_username != :me THEN from_username ELSE '' END) AS other_user,
                    SUM(CASE WHEN is_read=0 AND from_username != :me THEN 1 ELSE 0 END) AS unread
                FROM user_direct_messages
                WHERE conversation_id LIKE 'dm-%'
                  AND (from_username = :me OR to_usernames LIKE :me_pattern)
                GROUP BY conversation_id
                ORDER BY last_at DESC
                LIMIT 100
                """
            ),
            {"me": me, "me_pattern": f"%{me}%"},
        ).fetchall()
        data = []
        for row in rows:
            other = str(row.other_user or "").strip()
            if not other:
                parts = str(row.conversation_id or "").replace("dm-", "").split("_")
                other = next((p for p in parts if p != me), parts[0] if parts else "?")
            data.append(
                {
                    "conversation_id": str(row.conversation_id or ""),
                    "other_user": other,
                    "last_at": str(row.last_at or ""),
                    "last_message": str(row.last_received or row.last_sent or "")[:260],
                    "unread": int(row.unread or 0),
                }
            )
        return {"success": True, "data": data, "access": access}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.get("/api/v1/conversaciones/groups", response_class=JSONResponse)
def list_group_conversations(request: Request):
    access, error = _require_module_access(request)
    if error:
        return error
    me = _me(request)
    db = SessionLocal()
    try:
        _ensure_tables(db)
        rows = db.execute(
            text(
                """
                SELECT
                    g.conversation_id,
                    g.group_name,
                    g.created_by,
                    g.member_usernames,
                    MAX(m.created_at) AS last_at,
                    MAX(m.message_text) AS last_message,
                    SUM(CASE WHEN m.is_read=0 AND m.from_username != :me THEN 1 ELSE 0 END) AS unread
                FROM conversation_groups g
                LEFT JOIN conversation_group_messages m ON m.conversation_id = g.conversation_id
                WHERE LOWER(COALESCE(g.member_usernames,'')) LIKE :me_pattern
                GROUP BY g.conversation_id, g.group_name, g.created_by, g.member_usernames
                ORDER BY last_at DESC, g.group_name ASC
                """
            ),
            {"me": me, "me_pattern": f"%{me}%"},
        ).fetchall()
        data = []
        for row in rows:
            members = _clean_usernames(_safe_json(row.member_usernames, []))
            data.append(
                {
                    "conversation_id": str(row.conversation_id or ""),
                    "group_name": str(row.group_name or "Grupo"),
                    "created_by": str(row.created_by or ""),
                    "member_usernames": members,
                    "last_at": str(row.last_at or ""),
                    "last_message": str(row.last_message or "")[:260],
                    "unread": int(row.unread or 0),
                }
            )
        return {"success": True, "data": data, "access": access}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.post("/api/v1/conversaciones/groups", response_class=JSONResponse)
def create_group_conversation(request: Request, payload: dict = Body(...)):
    access, error = _require_module_access(request)
    if error:
        return error
    if not access.get("can_create_groups"):
        return JSONResponse(status_code=403, content={"success": False, "error": "No autorizado para crear grupos"})
    me = _me(request)
    group_name = str(payload.get("group_name") or "").strip()
    members = _clean_usernames(payload.get("member_usernames"))
    if me not in members:
        members.insert(0, me)
    members = _clean_usernames(members)
    if not group_name:
        return JSONResponse(status_code=400, content={"success": False, "error": "Nombre del grupo requerido"})
    if len(members) < 2:
        return JSONResponse(status_code=400, content={"success": False, "error": "Seleccione al menos dos participantes"})
    conv_id = f"grp-{me}-{int(datetime.now(timezone.utc).timestamp())}"
    db = SessionLocal()
    try:
        _ensure_tables(db)
        allowed_users = {item["username"] for item in _module_users(db)}
        if any(member not in allowed_users and member != me for member in members):
            return JSONResponse(status_code=400, content={"success": False, "error": "Hay usuarios sin acceso a Conversaciones"})
        db.execute(
            text(
                """
                INSERT INTO conversation_groups
                (conversation_id, group_name, created_by, member_usernames, created_at)
                VALUES (:conv, :name, :created_by, :members, :ts)
                """
            ),
            {
                "conv": conv_id,
                "name": group_name,
                "created_by": me,
                "members": json.dumps(members, ensure_ascii=False),
                "ts": _now_iso(),
            },
        )
        db.commit()
        return {"success": True, "data": {"conversation_id": conv_id, "group_name": group_name, "member_usernames": members}}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.get("/api/v1/conversaciones/groups/{conv_id:path}", response_class=JSONResponse)
def get_group_conversation(request: Request, conv_id: str):
    access, error = _require_module_access(request)
    if error:
        return error
    me = _me(request)
    conv = str(conv_id or "").strip()
    db = SessionLocal()
    try:
        _ensure_tables(db)
        if not _can_access_conversation(db, request, conv, me):
            return JSONResponse(status_code=403, content={"success": False, "error": "No autorizado"})
        group_row = db.execute(
            text("SELECT group_name, created_by, member_usernames FROM conversation_groups WHERE conversation_id = :conv LIMIT 1"),
            {"conv": conv},
        ).fetchone()
        if not group_row:
            return JSONResponse(status_code=404, content={"success": False, "error": "Grupo no encontrado"})
        rows = db.execute(
            text(
                """
                SELECT id, from_username, to_usernames, message_text, is_read, created_at
                FROM conversation_group_messages
                WHERE conversation_id = :conv
                ORDER BY created_at ASC, id ASC
                """
            ),
            {"conv": conv},
        ).fetchall()
        db.execute(
            text(
                """
                UPDATE conversation_group_messages
                SET is_read = 1
                WHERE conversation_id = :conv AND from_username != :me AND is_read = 0
                """
            ),
            {"conv": conv, "me": me},
        )
        db.commit()
        data = [
            {
                "id": int(row.id or 0),
                "from_username": str(row.from_username or ""),
                "to_usernames": _safe_json(row.to_usernames, []),
                "message_text": str(row.message_text or ""),
                "is_read": bool(row.is_read),
                "created_at": str(row.created_at or ""),
                "is_mine": str(row.from_username or "").lower() == me,
            }
            for row in rows
        ]
        return {
            "success": True,
            "data": data,
            "group": {
                "conversation_id": conv,
                "group_name": str(group_row.group_name or "Grupo"),
                "created_by": str(group_row.created_by or ""),
                "member_usernames": _clean_usernames(_safe_json(group_row.member_usernames, [])),
            },
            "access": access,
        }
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.post("/api/v1/conversaciones/groups/{conv_id:path}/send", response_class=JSONResponse)
def send_group_message(request: Request, conv_id: str, payload: dict = Body(...)):
    access, error = _require_module_access(request)
    if error:
        return error
    me = _me(request)
    conv = str(conv_id or "").strip()
    message = str(payload.get("message") or "").strip()
    if not message:
        return JSONResponse(status_code=400, content={"success": False, "error": "Mensaje vacio"})
    db = SessionLocal()
    try:
        _ensure_tables(db)
        members = _group_members(db, conv)
        if me not in members:
            return JSONResponse(status_code=403, content={"success": False, "error": "No autorizado"})
        recipients = [member for member in members if member != me]
        db.execute(
            text(
                """
                INSERT INTO conversation_group_messages
                (conversation_id, from_username, to_usernames, message_text, is_read, created_at)
                VALUES (:conv, :from_u, :to_u, :msg, 0, :ts)
                """
            ),
            {
                "conv": conv,
                "from_u": me,
                "to_u": json.dumps(recipients, ensure_ascii=False),
                "msg": message,
                "ts": _now_iso(),
            },
        )
        db.commit()
        return {"success": True, "data": {"conversation_id": conv}, "access": access}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.delete("/api/v1/conversaciones/groups/{conv_id:path}", response_class=JSONResponse)
def delete_group_conversation(request: Request, conv_id: str):
    access, error = _require_module_access(request)
    if error:
        return error
    me = _me(request)
    conv = str(conv_id or "").strip()
    db = SessionLocal()
    try:
        _ensure_tables(db)
        group_row = db.execute(
            text("SELECT created_by FROM conversation_groups WHERE conversation_id = :conv LIMIT 1"),
            {"conv": conv},
        ).fetchone()
        if not group_row:
            return JSONResponse(status_code=404, content={"success": False, "error": "Grupo no encontrado"})
        if not _is_admin(request) and str(group_row.created_by or "").strip().lower() != me:
            return JSONResponse(status_code=403, content={"success": False, "error": "Solo el creador puede eliminar el grupo"})
        db.execute(text("DELETE FROM conversation_group_messages WHERE conversation_id = :conv"), {"conv": conv})
        db.execute(text("DELETE FROM conversation_groups WHERE conversation_id = :conv"), {"conv": conv})
        db.commit()
        return {"success": True, "access": access}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.get("/api/v1/conversaciones/direct/{conv_id:path}", response_class=JSONResponse)
def get_direct_conversation(request: Request, conv_id: str):
    access, error = _require_module_access(request)
    if error:
        return error
    me = _me(request)
    conv = str(conv_id or "").strip()
    if not conv:
        return JSONResponse(status_code=400, content={"success": False, "error": "conv_id requerido"})
    db = SessionLocal()
    try:
        _ensure_tables(db)
        if not _can_access_conversation(db, request, conv, me):
            return JSONResponse(status_code=403, content={"success": False, "error": "No autorizado"})
        rows = db.execute(
            text(
                """
                SELECT id, from_username, to_usernames, message_text, is_read, created_at
                FROM user_direct_messages
                WHERE conversation_id = :conv
                ORDER BY created_at ASC, id ASC
                """
            ),
            {"conv": conv},
        ).fetchall()
        db.execute(
            text(
                """
                UPDATE user_direct_messages
                SET is_read = 1
                WHERE conversation_id = :conv AND from_username != :me AND is_read = 0
                """
            ),
            {"conv": conv, "me": me},
        )
        db.commit()
        data = [
            {
                "id": int(row.id or 0),
                "from_username": str(row.from_username or ""),
                "to_usernames": _safe_json(row.to_usernames, []),
                "message_text": str(row.message_text or ""),
                "is_read": bool(row.is_read),
                "created_at": str(row.created_at or ""),
                "is_mine": str(row.from_username or "").lower() == me,
            }
            for row in rows
        ]
        return {"success": True, "data": data, "access": access}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.post("/api/v1/conversaciones/direct/send", response_class=JSONResponse)
def send_direct_message(request: Request, payload: dict = Body(...)):
    access, error = _require_module_access(request)
    if error:
        return error
    me = _me(request)
    to_user = str(payload.get("to_username") or "").strip().lower()
    conv_id = str(payload.get("conversation_id") or "").strip()
    message = str(payload.get("message") or "").strip()
    if not message:
        return JSONResponse(status_code=400, content={"success": False, "error": "Mensaje vacio"})
    if not to_user and not conv_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "to_username o conversation_id requerido"})
    if not to_user:
        parts = conv_id.replace("dm-", "").split("_")
        to_user = next((p for p in parts if p != me), parts[0] if parts else "")
    conv_id = _dm_conv_id(me, to_user)
    db = SessionLocal()
    try:
        _ensure_tables(db)
        target_access = _conversation_access_for_username(db, to_user)
        if not target_access.get("role"):
            return JSONResponse(status_code=400, content={"success": False, "error": "El usuario no tiene acceso a Conversaciones"})
        db.execute(
            text(
                """
                INSERT INTO user_direct_messages
                (conversation_id, from_username, to_usernames, message_text, is_read, created_at)
                VALUES (:conv, :from_u, :to_u, :msg, 0, :ts)
                """
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
        return {"success": True, "data": {"conversation_id": conv_id}, "access": access}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.delete("/api/v1/conversaciones/direct/{conv_id:path}", response_class=JSONResponse)
def delete_direct_conversation(request: Request, conv_id: str):
    access, error = _require_module_access(request)
    if error:
        return error
    me = _me(request)
    conv = str(conv_id or "").strip()
    if not conv:
        return JSONResponse(status_code=400, content={"success": False, "error": "conv_id requerido"})
    db = SessionLocal()
    try:
        _ensure_tables(db)
        if not _can_access_conversation(db, request, conv, me):
            return JSONResponse(status_code=403, content={"success": False, "error": "No autorizado"})
        db.execute(text("DELETE FROM user_direct_messages WHERE conversation_id = :conv"), {"conv": conv})
        db.commit()
        return {"success": True, "access": access}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.post("/api/v1/conversaciones/notifications/send", response_class=JSONResponse)
def send_conversation_notification(request: Request, payload: dict = Body(...)):
    access, error = _require_module_access(request)
    if error:
        return error
    if not access.get("can_send_notifications"):
        return JSONResponse(status_code=403, content={"success": False, "error": "No autorizado para enviar notificaciones"})
    me = _me(request)
    conv = str(payload.get("conversation_id") or "").strip()
    message = str(payload.get("message") or "").strip()
    requested_scope = str(payload.get("scope") or "").strip().lower()
    if not message:
        return JSONResponse(status_code=400, content={"success": False, "error": "Mensaje requerido"})
    db = SessionLocal()
    try:
        _ensure_tables(db)
        sender_scope = str(access.get("notification_scope") or "").strip().lower()
        allowed_scopes = {"conversation"}
        if sender_scope in {"department", "company"}:
            allowed_scopes.add("department")
        if sender_scope == "company":
            allowed_scopes.add("company")
        normalized_scope = requested_scope if requested_scope in allowed_scopes else "conversation"
        if normalized_scope == "conversation":
            recipients = [user for user in _conversation_participants(db, conv, me) if user != me]
        else:
            recipients = _notification_recipients_for_scope(db, me, normalized_scope)
        if not recipients:
            return JSONResponse(status_code=400, content={"success": False, "error": "No hay destinatarios para esta notificacion"})
        _send_floating_notification(db, me, recipients, message, normalized_scope, conv)
        db.commit()
        return {"success": True, "data": {"recipients": recipients, "scope": normalized_scope}, "access": access}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.get("/api/v1/conversaciones/notifications/inbox", response_class=JSONResponse)
def get_notification_inbox(request: Request):
    access, error = _require_module_access(request)
    if error:
        return error
    me = _me(request)
    db = SessionLocal()
    try:
        _ensure_tables(db)
        rows = db.execute(
            text(
                """
                SELECT id, from_username, message_text, scope, conversation_id, created_at
                FROM conversation_notifications
                WHERE is_read = 0 AND to_usernames LIKE :me_pattern
                ORDER BY created_at ASC, id ASC
                LIMIT 20
                """
            ),
            {"me_pattern": f"%{me}%"},
        ).fetchall()
        ids = [int(row.id) for row in rows if row.id is not None]
        if ids:
            db.execute(
                text(
                    f"UPDATE conversation_notifications SET is_read = 1 WHERE id IN ({','.join(str(i) for i in ids)})"
                )
            )
            db.commit()
        data = [
            {
                "id": int(row.id or 0),
                "from_username": str(row.from_username or ""),
                "message_text": str(row.message_text or ""),
                "scope": str(row.scope or "conversation"),
                "conversation_id": str(row.conversation_id or ""),
                "created_at": str(row.created_at or ""),
            }
            for row in rows
        ]
        return {"success": True, "data": data, "access": access}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
    finally:
        db.close()


@router.get("/api/v1/conversaciones/unread-count", response_class=JSONResponse)
def unread_count(request: Request):
    access, error = _require_module_access(request)
    if error:
        return {"success": True, "data": {"count": 0}}
    me = _me(request)
    db = SessionLocal()
    try:
        _ensure_tables(db)
        direct_count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM user_direct_messages
                WHERE is_read = 0 AND from_username != :me AND to_usernames LIKE :pat
                """
            ),
            {"me": me, "pat": f"%{me}%"},
        ).scalar()
        group_count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM conversation_group_messages
                WHERE is_read = 0 AND from_username != :me AND to_usernames LIKE :pat
                """
            ),
            {"me": me, "pat": f"%{me}%"},
        ).scalar()
        notification_count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM conversation_notifications
                WHERE is_read = 0 AND to_usernames LIKE :pat
                """
            ),
            {"pat": f"%{me}%"},
        ).scalar()
        total = int(direct_count or 0) + int(group_count or 0) + int(notification_count or 0)
        return {"success": True, "data": {"count": total}, "access": access}
    except Exception:
        return {"success": True, "data": {"count": 0}}
    finally:
        db.close()

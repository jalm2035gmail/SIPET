from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar

from fastapi_modulo.db import SessionLocal

_CURRENT_TENANT: ContextVar[str] = ContextVar("control_interno_tenant", default="default")


def set_current_tenant(tenant_id: str) -> None:
    _CURRENT_TENANT.set(str(tenant_id or "default").strip() or "default")


def get_current_tenant() -> str:
    return _CURRENT_TENANT.get()


@contextmanager
def session_scope():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

__all__ = ["get_current_tenant", "session_scope", "set_current_tenant"]

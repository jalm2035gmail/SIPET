from __future__ import annotations

from fastapi import Request


_CORE_SYMBOLS_BOUND = False


def bind_core_dependencies() -> None:
    global _CORE_SYMBOLS_BOUND
    if _CORE_SYMBOLS_BOUND:
        return
    from fastapi_modulo import main as core

    for name in ("SessionLocal", "_normalize_tenant_id", "get_current_tenant", "render_backend_page"):
        globals()[name] = getattr(core, name)
    _CORE_SYMBOLS_BOUND = True


def get_session_local():
    bind_core_dependencies()
    return globals()["SessionLocal"]


def resolve_current_tenant_id(request: Request | None = None) -> str:
    bind_core_dependencies()
    normalize = globals()["_normalize_tenant_id"]
    if request is None:
        tenant_id = normalize("default")
    else:
        tenant_id = normalize(globals()["get_current_tenant"](request))
    tenant_id = str(tenant_id or "").strip()
    if not tenant_id:
        return "default"
    return tenant_id


def render_backend_screen(*args, **kwargs):
    bind_core_dependencies()
    return globals()["render_backend_page"](*args, **kwargs)

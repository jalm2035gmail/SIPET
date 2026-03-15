from __future__ import annotations


def require_tenant_id(tenant_id: str | None) -> str:
    normalized = str(tenant_id or "").strip().lower()
    if not normalized:
        raise ValueError("tenant_id es obligatorio.")
    return normalized

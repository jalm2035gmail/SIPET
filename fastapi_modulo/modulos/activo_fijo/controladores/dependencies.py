from __future__ import annotations

from fastapi import HTTPException, Request


def require_activo_fijo_access(request: Request) -> None:
    from fastapi_modulo.main import _get_user_app_access, is_admin_or_superadmin

    if is_admin_or_superadmin(request):
        return
    if "ActivoFijo" in _get_user_app_access(request):
        return
    raise HTTPException(status_code=403, detail="Acceso restringido al módulo Activo Fijo")

from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.exc import IntegrityError

from fastapi_modulo.modulos.multiempresa.modelos.me_models import EmpresaCreate, EmpresaUpdate
from fastapi_modulo.modulos.multiempresa.modelos.me_store import (
    create_empresa,
    delete_empresa,
    get_empresa,
    get_logo_path,
    get_me_consolidado,
    list_empresas,
    save_logo,
    update_empresa,
)

_MODULE_ROOT = os.path.dirname(os.path.dirname(__file__))

# ── Niveles de acceso ─────────────────────────────────────────────────────────
#
#  superadministrador         → sin restricciones
#  administrador_multiempresa → gestión de TODAS las empresas
#  administrador              → sólo su empresa (filtrado por tenant_id)
#  usuario con "Multiempresa" → sólo su empresa


def _get_me_scope(request: Request) -> Optional[str]:
    """
    Verifica acceso y retorna el filtro de tenant:
    - None → acceso irrestricto (superadmin, administrador_multiempresa)
    - str  → empresa del usuario (administrador, app_access)
    Lanza 403 si no tiene acceso.
    """
    from fastapi_modulo.main import _get_user_app_access, get_current_role

    role = get_current_role(request)

    if role in ("superadministrador", "administrador_multiempresa"):
        return None

    if role == "administrador":
        tenant = (getattr(request.state, "tenant_id", None) or "").strip()
        if not tenant:
            raise HTTPException(
                status_code=403,
                detail="El administrador no tiene empresa asignada (tenant_id vacío)",
            )
        return tenant

    if "Multiempresa" in _get_user_app_access(request):
        tenant = (getattr(request.state, "tenant_id", None) or "").strip()
        return tenant or "default"

    raise HTTPException(status_code=403, detail="Acceso restringido al módulo Multiempresa")


def _require_full_access(request: Request) -> None:
    """Solo superadministrador y administrador_multiempresa pueden crear/eliminar empresas."""
    from fastapi_modulo.main import get_current_role

    role = get_current_role(request)
    if role not in ("superadministrador", "administrador_multiempresa"):
        raise HTTPException(
            status_code=403,
            detail="Solo superadministrador o administrador_multiempresa puede realizar esta operación",
        )


router = APIRouter()


# ── Vista HTML ────────────────────────────────────────────────────────────────

@router.get("/multiempresa", response_class=HTMLResponse)
def multiempresa_page(request: Request):
    _get_me_scope(request)
    from fastapi_modulo.main import render_backend_page
    html_path = os.path.join(_MODULE_ROOT, "vistas", "multiempresa.html")
    with open(html_path, encoding="utf-8") as f:
        content = f.read()
    return render_backend_page(
        request,
        title="Multiempresa",
        description="Administración de empresas del sistema SIPET.",
        content=content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/api/multiempresa/assets/multiempresa.js")
def multiempresa_js():
    js_path = os.path.join(_MODULE_ROOT, "static", "js", "multiempresa.js")
    with open(js_path, encoding="utf-8") as f:
        content = f.read()
    return Response(content=content, media_type="application/javascript")


# ── Scope del usuario actual ──────────────────────────────────────────────────

@router.get("/api/multiempresa/scope")
def api_scope(request: Request):
    """Devuelve el nivel de acceso del usuario al módulo Multiempresa."""
    from fastapi_modulo.main import get_current_role

    tenant_filter = _get_me_scope(request)
    role = get_current_role(request)

    if role == "superadministrador":
        nivel = "superadmin"
    elif role == "administrador_multiempresa":
        nivel = "multiempresa"
    else:
        nivel = "admin"

    return {
        "nivel": nivel,
        "tenant_filter": tenant_filter,
        "puede_crear": nivel in ("superadmin", "multiempresa"),
        "puede_eliminar": nivel in ("superadmin", "multiempresa"),
    }


# ── Logos (servir archivos) ───────────────────────────────────────────────────

@router.get("/api/multiempresa/logos/{filename}")
def serve_logo(filename: str):
    import mimetypes
    path = get_logo_path(filename)
    if not path:
        raise HTTPException(status_code=404, detail="Logo no encontrado")
    mime, _ = mimetypes.guess_type(str(path))
    return Response(content=path.read_bytes(), media_type=mime or "application/octet-stream")


# ── Consolidado ───────────────────────────────────────────────────────────────

@router.get("/api/multiempresa/consolidado")
def api_consolidado(request: Request):
    scope = _get_me_scope(request)
    return get_me_consolidado(tenant_filter=scope)


# ── Empresas CRUD ─────────────────────────────────────────────────────────────

@router.get("/api/multiempresa/empresas")
def api_list_empresas(request: Request, estado: str = Query(default="")):
    scope = _get_me_scope(request)
    return list_empresas(estado=estado or None, tenant_filter=scope)


@router.get("/api/multiempresa/empresas/{empresa_id}")
def api_get_empresa(empresa_id: int, request: Request):
    scope = _get_me_scope(request)
    obj = get_empresa(empresa_id, tenant_filter=scope)
    if not obj:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return obj


@router.post("/api/multiempresa/empresas", status_code=201)
def api_create_empresa(body: EmpresaCreate, request: Request):
    _require_full_access(request)
    try:
        return create_empresa(body.model_dump(exclude_none=True))
    except IntegrityError as e:
        err = str(e.orig).lower() if e.orig else ""
        if "codigo" in err or "UNIQUE" in str(e):
            raise HTTPException(status_code=409, detail="Ya existe una empresa con ese código o tenant_id")
        raise HTTPException(status_code=409, detail="Conflicto al crear la empresa")


@router.put("/api/multiempresa/empresas/{empresa_id}")
def api_update_empresa(empresa_id: int, body: EmpresaUpdate, request: Request):
    scope = _get_me_scope(request)
    try:
        obj = update_empresa(empresa_id, body.model_dump(exclude_none=True), tenant_filter=scope)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Conflicto al actualizar")
    if not obj:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return obj


@router.delete("/api/multiempresa/empresas/{empresa_id}", status_code=204)
def api_delete_empresa(empresa_id: int, request: Request):
    _require_full_access(request)
    if not delete_empresa(empresa_id):
        raise HTTPException(status_code=404, detail="Empresa no encontrada")


# ── Logo upload ───────────────────────────────────────────────────────────────

@router.post("/api/multiempresa/empresas/{empresa_id}/logo")
async def api_upload_logo(empresa_id: int, request: Request, file: UploadFile = File(...)):
    scope = _get_me_scope(request)
    data = await file.read()
    content_type = file.content_type or "application/octet-stream"
    try:
        obj = save_logo(empresa_id, file.filename or "", data, content_type, tenant_filter=scope)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not obj:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return obj

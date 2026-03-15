from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse


def _render_backend_MAIN(
    request: Request,
    title: str,
    subtitle: Optional[str] = None,
    description: Optional[str] = None,
    content: str = "",
    view_buttons: Optional[List[Dict]] = None,
    view_buttons_html: str = "",
    hide_floating_actions: bool = True,
    show_page_header: bool = True,
    page_title: Optional[str] = None,
    page_description: Optional[str] = None,
    section_title: Optional[str] = None,
    section_label: Optional[str] = None,
    floating_buttons: Optional[List[Dict]] = None,
    floating_actions_html: str = "",
    floating_actions_screen: str = "personalization",
) -> HTMLResponse:
    from fastapi_modulo import main as core

    rendered_view_buttons = view_buttons_html or core.build_view_buttons_html(view_buttons)
    can_manage_personalization = core.is_superadmin(request)
    login_identity = core._get_login_identity_context()
    sidebar_logo_url = core._resolve_sidebar_logo_url(login_identity)
    resolved_title = (page_title or title or "Sin titulo").strip()
    resolved_description = (page_description or description or subtitle or "Descripcion pendiente").strip()

    context = {
        "request": request,
        "title": title,
        "subtitle": subtitle,
        "page_title": resolved_title,
        "page_description": resolved_description,
        "section_title": (section_title or "Contenido").strip(),
        "section_label": (section_label or "Seccion").strip(),
        "content": content,
        "view_buttons_html": rendered_view_buttons,
        "floating_buttons": floating_buttons,
        "floating_actions_html": floating_actions_html,
        "floating_actions_screen": floating_actions_screen,
        "hide_floating_actions": hide_floating_actions,
        "show_page_header": show_page_header,
        "colores": core.get_colores_context(),
        "can_manage_personalization": can_manage_personalization,
        "app_favicon_url": login_identity.get("login_favicon_url"),
        "login_logo_url": login_identity.get("login_logo_url"),
        "sidebar_logo_url": sidebar_logo_url,
        "user_app_access": core._get_user_app_access(request),
        "active_module_keys": core.get_active_module_keys(),
        "modules_payload": core.list_modules_payload(),
        "modules_payload_map": {item["key"]: item for item in core.list_modules_payload()},
        "active_system_modules": core.get_active_app_access_names(),
        "user_strategy_submenu_access_levels": core._get_user_strategy_submenu_access_levels(request),
        "app_env": core.APP_ENV,
        "is_superadmin_user": core.is_superadmin(request),
        "is_admin_or_superadmin_user": core.is_admin_or_superadmin(request),
    }
    return core.templates.TemplateResponse("MAIN.html", context)


def backend_screen(
    request: Request,
    title: str,
    subtitle: Optional[str] = None,
    description: Optional[str] = None,
    content: str = "",
    view_buttons: Optional[List[Dict]] = None,
    view_buttons_html: str = "",
    floating_buttons: Optional[List[Dict]] = None,
    hide_floating_actions: bool = False,
    show_page_header: bool = True,
    page_title: Optional[str] = None,
    page_description: Optional[str] = None,
    section_title: Optional[str] = None,
    section_label: Optional[str] = None,
):
    return _render_backend_MAIN(
        request=request,
        title=title,
        subtitle=subtitle,
        description=description,
        content=content,
        view_buttons=view_buttons,
        view_buttons_html=view_buttons_html,
        hide_floating_actions=hide_floating_actions,
        show_page_header=show_page_header,
        page_title=page_title,
        page_description=page_description,
        section_title=section_title,
        section_label=section_label,
        floating_buttons=floating_buttons,
    )


def render_backend_page(
    request: Request,
    title: str,
    description: str = "",
    content: str = "",
    subtitle: Optional[str] = None,
    hide_floating_actions: bool = True,
    view_buttons: Optional[List[Dict]] = None,
    view_buttons_html: str = "",
    floating_actions_html: str = "",
    floating_actions_screen: str = "personalization",
    show_page_header: bool = True,
    section_title: Optional[str] = None,
    section_label: Optional[str] = None,
) -> HTMLResponse:
    return _render_backend_MAIN(
        request=request,
        title=title,
        subtitle=subtitle,
        description=description,
        content=content,
        view_buttons=view_buttons,
        view_buttons_html=view_buttons_html,
        hide_floating_actions=hide_floating_actions,
        show_page_header=show_page_header,
        page_title=title,
        page_description=description,
        section_title=section_title,
        section_label=section_label,
        floating_actions_html=floating_actions_html,
        floating_actions_screen=floating_actions_screen,
    )


async def enforce_backend_login(request: Request, call_next):
    from fastapi_modulo import main as core
    from fastapi_modulo import db as core_db

    host_token = core_db.set_request_host(
        request.headers.get("x-forwarded-host")
        or request.headers.get("host")
        or request.url.hostname
    )
    path = request.url.path
    public_paths = {
        "/",
        "/backend",
        "/backend/descripcion",
        "/backend/funcionalidades",
        "/backend/404",
        "/backend/login",
        "/logout",
        "/health",
        "/healthz",
        "/favicon.ico",
        "/api/backend/me",
    }
    if core.ENABLE_API_DOCS:
        public_paths.update({"/docs", "/redoc", "/openapi.json"})
    if (
        request.method == "OPTIONS"
        or path in public_paths
        or __import__(
            "fastapi_modulo.modulos.frontend.controladores.frontend",
            fromlist=["_is_public_frontend_page_path"],
        )._is_public_frontend_page_path(path)
        or path.startswith("/api/public/")
        or path.startswith("/backend/passkey/")
        or path.startswith("/identidad-institucional")
        or path.startswith("/templates/")
        or path.startswith("/static/")
        or path.startswith("/icon/")
        or path.startswith("/imagenes/")
        or path.startswith("/docs/")
        or path.startswith("/redoc/")
    ):
        try:
            return await call_next(request)
        finally:
            core_db.reset_request_host(host_token)

    session_token = request.cookies.get(core.AUTH_COOKIE_NAME, "")
    session_data = core._read_session_cookie(session_token)
    if not session_data:
        try:
            if path.startswith("/api/") or path.startswith("/guardar-colores"):
                return JSONResponse({"success": False, "error": "No autenticado"}, status_code=401)
            return core.templates.TemplateResponse(
                "not_found.html",
                core._not_found_context(request),
                status_code=404,
            )
        finally:
            core_db.reset_request_host(host_token)

    try:
        request.state.user_name = session_data["username"]
        request.state.user_role = session_data["role"]
        request.state.tenant_id = core._normalize_tenant_id(session_data.get("tenant_id"))

        if (
            core.CSRF_PROTECTION_ENABLED
            and request.method in {"POST", "PUT", "PATCH", "DELETE"}
            and not path.startswith("/backend/passkey/")
            and not path.startswith("/identidad-institucional")
            and not core._is_same_origin_request(request)
        ):
            if path.startswith("/api/") or path.startswith("/guardar-colores"):
                return JSONResponse({"success": False, "error": "CSRF validation failed"}, status_code=403)
            return core.templates.TemplateResponse(
                "not_found.html",
                core._not_found_context(request, title="Solicitud no válida"),
                status_code=403,
            )

        return await call_next(request)
    finally:
        core_db.reset_request_host(host_token)

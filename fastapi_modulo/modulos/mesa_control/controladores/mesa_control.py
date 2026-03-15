from __future__ import annotations

from html import escape
import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse


router = APIRouter()
MODULE_DIR = Path(__file__).resolve().parent.parent
MESA_CONTROL_TEMPLATE_PATH = MODULE_DIR / "vistas" / "mesa_de_control.html"


def _render_no_access(request: Request, *, title: str, description: str) -> HTMLResponse:
    from fastapi_modulo.main import _render_no_access_module_page

    return _render_no_access_module_page(
        request,
        title=title,
        description=description,
        message="Sin acceso, consulte con el administrador",
    )


def _render_mesa_de_control_page(request: Request) -> HTMLResponse:
    from fastapi_modulo.main import (
        _get_login_identity_context,
        _has_app_access,
        _resolve_sidebar_logo_url,
        render_backend_page,
    )

    if not _has_app_access(request, "Mesa de control"):
        return _render_no_access(
            request,
            title="Mesa de control",
            description="Seguimiento visual de flujo institucional y control ejecutivo.",
        )
    try:
        content = MESA_CONTROL_TEMPLATE_PATH.read_text(encoding="utf-8")
    except OSError:
        return _render_no_access(
            request,
            title="Mesa de control",
            description="Seguimiento visual de flujo institucional y control ejecutivo.",
        )
    login_identity = _get_login_identity_context()
    company_logo_url = _resolve_sidebar_logo_url(login_identity) or "/templates/icon/icon.png"
    content = content.replace("__COMPANY_LOGO_URL__", escape(company_logo_url))
    return render_backend_page(
        request,
        title="Mesa de control",
        description="Seguimiento visual de flujo institucional y control ejecutivo.",
        content=content,
        hide_floating_actions=True,
        show_page_header=True,
    )


@router.get("/mesa-de-control", response_class=HTMLResponse)
@router.get("/mesa-de-control/", response_class=HTMLResponse)
def mesa_de_control_page(request: Request):
    return _render_mesa_de_control_page(request)


@router.get("/mesa-de-control/captura-consolidacion", response_class=HTMLResponse)
def mesa_de_control_captura_consolidacion_page(request: Request):
    return _render_no_access(
        request,
        title="Captura y consolidacion",
        description="Captura y consolidación de mesa de control.",
    )


@router.get("/mesa-de-control/analisis-priorizacion", response_class=HTMLResponse)
def mesa_de_control_analisis_priorizacion_page(request: Request):
    return _render_no_access(
        request,
        title="Analisis y priorizacion",
        description="Análisis y priorización de mesa de control.",
    )


@router.get("/mesa-de-control/comite-decisiones", response_class=HTMLResponse)
def mesa_de_control_comite_decisiones_page(request: Request):
    return _render_no_access(
        request,
        title="Comite y decisiones",
        description="Comité y decisiones de mesa de control.",
    )


@router.get("/mesa-de-control/monitoreo-cierre", response_class=HTMLResponse)
def mesa_de_control_monitoreo_cierre_page(request: Request):
    return _render_no_access(
        request,
        title="Monitoreo y cierre",
        description="Monitoreo y cierre de mesa de control.",
    )


def _render_control_template(
    request: Request,
    *,
    template_name: str,
    title: str,
    description: str,
    fallback_title: str,
) -> HTMLResponse:
    from fastapi_modulo.main import render_backend_page

    template_path = os.path.join(
        "fastapi_modulo",
        "templates",
        "modulos",
        "control_seguimiento",
        template_name,
    )
    try:
        with open(template_path, "r", encoding="utf-8") as handle:
            content = handle.read()
    except OSError:
        content = f"""
        <section style="padding:24px;border:1px solid #dbe2ea;border-radius:16px;background:#ffffff;">
            <h2 style="margin:0 0 12px;color:#0f172a;">{fallback_title}</h2>
            <p style="margin:0;color:#475569;">No se pudo cargar la plantilla del módulo.</p>
        </section>
        """
    return render_backend_page(
        request,
        title=title,
        description=description,
        content=content,
        hide_floating_actions=True,
        show_page_header=True,
    )


@router.get("/control-seguimiento", response_class=HTMLResponse)
def control_seguimiento_page(request: Request):
    return _render_control_template(
        request,
        template_name="control_seguimiento.html",
        title="Control y seguimiento",
        description="Seguimiento multinivel para persona, sucursal, departamento, región y cooperativa.",
        fallback_title="Control y seguimiento",
    )


@router.get("/contraloria", response_class=HTMLResponse)
@router.get("/control-seguimiento/contraloria", response_class=HTMLResponse)
def control_seguimiento_contraloria_page(request: Request):
    return _render_control_template(
        request,
        template_name="contraloria.html",
        title="Contraloria",
        description="Panel ejecutivo de contraloría para seguimiento institucional, diagnósticos y planes de trabajo.",
        fallback_title="Contraloria",
    )


@router.get("/control-seguimiento/gestion-riesgos", response_class=HTMLResponse)
def control_seguimiento_gestion_riesgos_page(request: Request):
    return _render_control_template(
        request,
        template_name="gestion_riesgos.html",
        title="Gestión de riesgos",
        description="Administración integral de riesgos y seguimiento de mitigación.",
        fallback_title="Gestión de riesgos",
    )

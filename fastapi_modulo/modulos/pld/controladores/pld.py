from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse


router = APIRouter()
MODULE_DIR = Path(__file__).resolve().parent.parent
PLD_TEMPLATE_PATH = MODULE_DIR / "vistas" / "pld.html"


def _render_no_access(request: Request, *, title: str, description: str) -> HTMLResponse:
    from fastapi_modulo.main import _render_no_access_module_page

    return _render_no_access_module_page(
        request,
        title=title,
        description=description,
        message="Sin acceso, consulte con el administrador",
    )


@router.get("/pld", response_class=HTMLResponse)
def pld_page(request: Request):
    from fastapi_modulo.main import render_backend_page

    try:
        content = PLD_TEMPLATE_PATH.read_text(encoding="utf-8")
    except OSError:
        return _render_no_access(
            request,
            title="PLD",
            description="Prevención de lavado de dinero y cumplimiento normativo.",
        )
    return render_backend_page(
        request,
        title="PLD",
        description="Prevención de lavado de dinero y cumplimiento normativo.",
        content=content,
        hide_floating_actions=True,
        show_page_header=True,
    )


@router.get("/pld/alertas-sospechosas", response_class=HTMLResponse)
def pld_alertas_sospechosas_page(request: Request):
    return _render_no_access(
        request,
        title="Alertas Sospechosas",
        description="Alertas sospechosas de PLD.",
    )


@router.get("/pld/investigacion", response_class=HTMLResponse)
def pld_investigacion_page(request: Request):
    return _render_no_access(
        request,
        title="Investigacion",
        description="Investigación de casos PLD.",
    )


@router.get("/pld/riesgo-clientes", response_class=HTMLResponse)
def pld_riesgo_clientes_page(request: Request):
    return _render_no_access(
        request,
        title="Riesgo de Clientes",
        description="Riesgo de clientes en PLD.",
    )


@router.get("/pld/expedientes-analisis", response_class=HTMLResponse)
def pld_expedientes_analisis_page(request: Request):
    return _render_no_access(
        request,
        title="Expedientes y Analisis",
        description="Expedientes y análisis de PLD.",
    )


@router.get("/pld/configuracion", response_class=HTMLResponse)
def pld_configuracion_page(request: Request):
    return _render_no_access(
        request,
        title="Configuracion",
        description="Configuración de PLD.",
    )

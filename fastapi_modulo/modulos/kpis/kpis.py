import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()
KPIS_TEMPLATE_PATH = os.path.join("fastapi_modulo", "templates", "modulos", "kpis", "kpis.html")


def _load_kpis_template() -> str:
    try:
        with open(KPIS_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return "<p>No se pudo cargar la vista de KPIs.</p>"


@router.get("/kpis", response_class=HTMLResponse)
def kpis_page(request: Request):
    from fastapi_modulo.main import render_backend_page

    return render_backend_page(
        request,
        title="KPIs",
        description="Gestión y seguimiento de indicadores clave de desempeño.",
        content=_load_kpis_template(),
        hide_floating_actions=True,
        show_page_header=False,
    )

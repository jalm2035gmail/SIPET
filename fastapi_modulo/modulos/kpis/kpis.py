import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()
_KPIS_LOCKED_CONTENT = """
<section class="w-full max-w-3xl mx-auto">
  <article class="card rounded-box border border-base-300 bg-base-100 shadow-sm">
    <div class="card-body gap-4 text-center">
      <h2 class="text-2xl font-bold">KPIs</h2>
      <p class="text-base-content/70">No tiene acceso, contacte al administrador.</p>
    </div>
  </article>
</section>
"""
KPIS_TEMPLATE_PATH = os.path.join("fastapi_modulo", "templates", "modulos", "kpis", "kpis.html")
KPIS_INDICADORES_TEMPLATE_PATH = os.path.join(
    "fastapi_modulo", "templates", "modulos", "kpis", "indicadores.html"
)


def _load_kpis_template() -> str:
    try:
        with open(KPIS_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return "<p>No se pudo cargar la vista de KPIs.</p>"


def _load_kpis_indicadores_template() -> str:
    try:
        with open(KPIS_INDICADORES_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return "<p>No se pudo cargar la vista de indicadores.</p>"


@router.get("/kpis", response_class=HTMLResponse)
def kpis_page(request: Request):
    from fastapi_modulo.main import render_backend_page

    return render_backend_page(
        request,
        title="KPIs",
        description="Acceso restringido al módulo KPIs.",
        content=_KPIS_LOCKED_CONTENT,
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/kpis/indicadores", response_class=HTMLResponse)
def kpis_indicadores_page(request: Request):
    from fastapi_modulo.main import render_backend_page

    return render_backend_page(
        request,
        title="Indicadores",
        description="Pantalla reservada para indicadores.",
        content=_load_kpis_indicadores_template(),
        hide_floating_actions=True,
        show_page_header=False,
    )

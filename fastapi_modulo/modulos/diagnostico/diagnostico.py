import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()
BASE_TEMPLATE_PATH = os.path.join("fastapi_modulo", "templates", "modulos", "diagnostico")


def _bind_core_symbols() -> None:
    if globals().get('_CORE_BOUND'):
        return
    from fastapi_modulo import main as core

    globals()['render_backend_page'] = getattr(core, 'render_backend_page')
    globals()['_render_blank_management_screen'] = getattr(core, '_render_blank_management_screen', None)
    globals()['_CORE_BOUND'] = True


def _load_template(filename: str) -> str:
    path = os.path.join(BASE_TEMPLATE_PATH, filename)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return "<p>No se pudo cargar la vista de diagnóstico.</p>"


@router.get('/diagnostico', response_class=HTMLResponse)
def diagnostico_page(request: Request):
    _bind_core_symbols()
    if callable(globals().get('_render_blank_management_screen')):
        return _render_blank_management_screen(request, 'Diagnóstico')
    return render_backend_page(
        request,
        title='Diagnóstico',
        description='Selecciona una herramienta de diagnóstico para comenzar.',
        content='<p>Selecciona FODA, PESTEL, PORTER o Percepción del cliente desde el menú.</p>',
        hide_floating_actions=True,
        show_page_header=True,
    )


@router.get('/diagnostico/foda', response_class=HTMLResponse)
def diagnostico_foda_page(request: Request):
    _bind_core_symbols()
    return render_backend_page(
        request,
        title='FODA',
        description='Identifica factores internos y externos para el diagnóstico estratégico.',
        content=_load_template("foda.html"),
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get('/diagnostico/pestel', response_class=HTMLResponse)
def diagnostico_pestel_page(request: Request):
    _bind_core_symbols()
    return render_backend_page(
        request,
        title='PESTEL',
        description='Analiza factores externos que impactan la estrategia institucional.',
        content=_load_template("pestel.html"),
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get('/diagnostico/porter', response_class=HTMLResponse)
def diagnostico_porter_page(request: Request):
    _bind_core_symbols()
    return render_backend_page(
        request,
        title='PORTER',
        description='Evalúa las cinco fuerzas competitivas para priorizar decisiones estratégicas.',
        content=_load_template("porter.html"),
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get('/diagnostico/percepcion-cliente', response_class=HTMLResponse)
def diagnostico_percepcion_cliente_page(request: Request):
    _bind_core_symbols()
    return render_backend_page(
        request,
        title='Percepción del cliente',
        description='Monitorea feedback para detectar fortalezas y brechas del servicio.',
        content=_load_template("percepcion_cliente.html"),
        hide_floating_actions=True,
        show_page_header=False,
    )

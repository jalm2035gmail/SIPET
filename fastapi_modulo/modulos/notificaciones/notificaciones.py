import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from fastapi_modulo.modulos.notificaciones.conversaciones import router as conversaciones_router

router = APIRouter()
router.include_router(conversaciones_router)
NOTIFICACIONES_TEMPLATE_PATH = os.path.join(
    'fastapi_modulo', 'templates', 'modulos', 'notificaciones', 'notificaciones.html'
)


def _load_notificaciones_template() -> str:
    try:
        with open(NOTIFICACIONES_TEMPLATE_PATH, 'r', encoding='utf-8') as fh:
            return fh.read()
    except OSError:
        return '<p>No se pudo cargar la vista de notificaciones.</p>'


@router.get('/notificaciones', response_class=HTMLResponse)
def notificaciones_page(request: Request):
    from fastapi_modulo.main import render_backend_page

    return render_backend_page(
        request,
        title='Conversaciones',
        description='Chat IA AVAN con RAG documental y fuentes citadas.',
        content=_load_notificaciones_template(),
        hide_floating_actions=True,
        show_page_header=True,
    )


@router.get('/conversaciones', response_class=HTMLResponse)
def conversaciones_page(request: Request):
    return notificaciones_page(request)

import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse

from fastapi_modulo.modulos.notificaciones.controladores.conversaciones import router as conversaciones_router

router = APIRouter()
router.include_router(conversaciones_router)
_MODULE_ROOT = os.path.dirname(os.path.dirname(__file__))
NOTIFICACIONES_TEMPLATE_PATH = os.path.join(_MODULE_ROOT, "vistas", "conversaciones.html")
_ASSET_FILES = {
    "conversaciones.css": os.path.join(_MODULE_ROOT, "static", "css", "conversaciones.css"),
    "conversaciones.js": os.path.join(_MODULE_ROOT, "static", "js", "conversaciones.js"),
}


def _load_notificaciones_template() -> str:
    try:
        with open(NOTIFICACIONES_TEMPLATE_PATH, 'r', encoding='utf-8') as fh:
            return fh.read()
    except OSError:
        return '<p>No se pudo cargar la vista de notificaciones.</p>'


@router.get("/notificaciones/assets/{filename}")
def notificaciones_asset(filename: str, request: Request):
    file_path = _ASSET_FILES.get(str(filename or "").strip())
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    return FileResponse(file_path)


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

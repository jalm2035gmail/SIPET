"""Rutas HTML del modulo de capacitacion."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse

from fastapi_modulo.modulos.capacitacion.controladores.dependencies import is_admin_or_superadmin
from fastapi_modulo.modulos.capacitacion.controladores.utils import (
    STATIC_DIR,
    image_response,
    render_editor_page,
    render_module_page,
)

router = APIRouter()


def _serve_static_file(asset_path: str) -> FileResponse:
    relative_path = Path(asset_path)
    target = (STATIC_DIR / relative_path).resolve()
    static_root = STATIC_DIR.resolve()
    if not str(target).startswith(str(static_root)) or not target.is_file():
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    return FileResponse(target)


@router.get("/capacitacion", response_class=HTMLResponse)
def cap_page(request: Request):
    return render_module_page(title="Capacitación", request=request, filename="capacitacion.html", menu_key="catalogo")


@router.get("/modulos/capacitacion/imagenes/{filename}")
def cap_image(filename: str):
    return image_response(filename)


@router.get("/capacitacion/assets/{asset_path:path}")
def cap_asset(asset_path: str):
    return _serve_static_file(asset_path)


@router.get("/modulos/capacitacion/static/{asset_path:path}")
def cap_module_static(asset_path: str):
    return _serve_static_file(asset_path)


@router.get("/capacitacion/curso/{curso_id}", response_class=HTMLResponse)
def cap_curso_page(curso_id: int, request: Request):
    return render_module_page(title="Curso", request=request, filename="capacitacion_player.html", menu_key="catalogo")


@router.get("/capacitacion/evaluacion/{eval_id}", response_class=HTMLResponse)
def cap_eval_page(eval_id: int, request: Request):
    return render_module_page(title="Evaluación", request=request, filename="capacitacion_eval.html", menu_key="catalogo")


@router.get("/capacitacion/mis-certificados", response_class=HTMLResponse)
def cap_mis_certificados_page(request: Request):
    return render_module_page(title="Mis Certificados", request=request, filename="capacitacion_certificados.html", menu_key="certificados")


@router.get("/capacitacion/certificado/{cert_id}", response_class=HTMLResponse)
def cap_cert_view_page(cert_id: int, request: Request):
    return render_module_page(title="Certificado", request=request, filename="capacitacion_cert_view.html", menu_key="certificados")


@router.get("/capacitacion/verificar/{folio}", response_class=HTMLResponse)
def cap_verificar_page(folio: str, request: Request):
    return render_module_page(title="Verificar Certificado", request=request, filename="capacitacion_verificar.html", menu_key="certificados")


@router.get("/capacitacion/dashboard", response_class=HTMLResponse)
def cap_dashboard_page(request: Request):
    if not is_admin_or_superadmin(request):
        raise HTTPException(status_code=403, detail="Solo administradores pueden acceder al dashboard")
    return render_module_page(title="Dashboard Capacitación", request=request, filename="capacitacion_dashboard.html", menu_key="dashboard")


@router.get("/capacitacion/mi-progreso", response_class=HTMLResponse)
def cap_progreso_page(request: Request):
    return render_module_page(title="Mi Progreso — Capacitación", request=request, filename="capacitacion_progreso.html", menu_key="progreso")


@router.get("/capacitacion/gamificacion", response_class=HTMLResponse)
def cap_gamificacion_page(request: Request):
    return render_module_page(title="Gamificación — Capacitación", request=request, filename="capacitacion_gamificacion.html", menu_key="gamificacion")


@router.get("/capacitacion/presentaciones", response_class=HTMLResponse)
def cap_presentaciones_page(request: Request):
    return render_module_page(title="Presentaciones — Capacitación", request=request, filename="capacitacion_presentaciones.html", menu_key="presentaciones")


@router.get("/capacitacion/presentacion/{pres_id}/editor", response_class=HTMLResponse)
def cap_editor_page(pres_id: int, request: Request):
    return render_editor_page(pres_id=pres_id, request=request, menu_key="presentaciones")


@router.get("/capacitacion/presentacion/{pres_id}/ver", response_class=HTMLResponse)
def cap_visor_page(pres_id: int, request: Request):
    return render_module_page(
        title="Ver Presentación",
        request=request,
        filename="capacitacion_visor.html",
        menu_key="presentaciones",
        replacements={"__PRES_ID__": str(pres_id)},
    )

__all__ = ["router"]

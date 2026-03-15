import os
import json

# Módulo inicial para endpoints y lógica de departamentos
from fastapi import APIRouter, Request, Body
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from typing import List, Dict, Any
from fastapi_modulo.modulos.empleados.modelos.puestos_laborales_store import (
    delete_puesto,
    load_puestos,
    update_puesto_notebook,
    upsert_puesto,
)
from fastapi_modulo.modulos.empleados.modelos.departamentos_service import (
    delete_departamento_payload,
    ensure_departamentos_schema,
    get_departamentos_catalog,
    list_departamentos_payload,
    save_departamentos_payload,
)

router = APIRouter()
DEPARTAMENTOS_TEMPLATE_PATH = os.path.join("fastapi_modulo", "modulos", "empleados", "vistas", "departamentos.html")
PUESTOS_LABORALES_TEMPLATE_PATH = os.path.join("fastapi_modulo", "modulos", "empleados", "vistas", "puestos_laborales.html")
PUESTOS_LABORALES_JS_PATH = os.path.join("fastapi_modulo", "modulos", "empleados", "static", "js", "puestos_laborales.js")
PUESTOS_LABORALES_CSS_PATH = os.path.join("fastapi_modulo", "modulos", "empleados", "static", "css", "puestos_laborales.css")
EMPLEADOS_PLACEHOLDER_TEMPLATE_PATH = os.path.join(
    "fastapi_modulo",
    "modulos",
    "empleados",
    "vistas",
    "placeholder_no_access.html",
)
DEPARTAMENTOS_PUBLIC_ACCESS = str(
    os.getenv("DEPARTAMENTOS_PUBLIC_ACCESS", "0")
).strip().lower() in {"1", "true", "yes", "on"}
def _enforce_departamentos_write_permission(request: Request) -> None:
    # Temporal: permitir operación abierta del módulo de departamentos.
    if DEPARTAMENTOS_PUBLIC_ACCESS:
        return
    from fastapi_modulo.main import require_admin_or_superadmin

    require_admin_or_superadmin(request)


def _render_departamentos_page(request: Request) -> HTMLResponse:
    from fastapi_modulo.main import render_backend_page

    try:
        with open(DEPARTAMENTOS_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            areas_content = fh.read()
    except OSError:
        areas_content = ""
    return render_backend_page(
        request,
        title="Departamentos",
        description="Administra la estructura de departamentos de la organización",
        content=areas_content,
        hide_floating_actions=True,
        show_page_header=False,
    )


def _render_empleados_placeholder(
    request: Request,
    *,
    title: str,
    description: str,
    message: str = "No tiene acceso, comuníquese con el administrador.",
) -> HTMLResponse:
    from fastapi_modulo.main import render_backend_page

    try:
        with open(EMPLEADOS_PLACEHOLDER_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        content = "<p>No se pudo cargar la vista.</p>"

    content = content.replace("__PLACEHOLDER_TITLE__", "Sin acceso")
    content = content.replace("__PLACEHOLDER_MESSAGE__", message)
    return render_backend_page(
        request,
        title=title,
        description=description,
        content=content,
        hide_floating_actions=True,
        floating_actions_screen="personalization",
    )


@router.get("/departamentos", response_class=HTMLResponse)
def departamentos_page(request: Request):
    # Redirige a la vista backend oficial con estilos y layout unificados.
    return RedirectResponse(url="/inicio/departamentos", status_code=307)


@router.get("/inicio/departamentos", response_class=HTMLResponse)
def inicio_departamentos_page(request: Request):
    return _render_departamentos_page(request)


@router.get("/modulos/empleados/puestos_laborales.js")
def puestos_laborales_js():
    return FileResponse(PUESTOS_LABORALES_JS_PATH, media_type="application/javascript")


@router.get("/modulos/empleados/puestos_laborales.css")
def puestos_laborales_css():
    return FileResponse(PUESTOS_LABORALES_CSS_PATH, media_type="text/css")


@router.get("/api/puestos-laborales")
def api_puestos_laborales_list():
    return {"success": True, "data": load_puestos()}


@router.post("/api/puestos-laborales")
async def api_puestos_laborales_save(request: Request):
    try:
        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError
        action = body.get("action", "save")

        if action == "delete":
            puestos = delete_puesto(str(body.get("id", "")))
            return {"success": True, "data": puestos}

        if action == "update_notebook":
            return update_puesto_notebook(
                str(body.get("id", "")),
                habilidades_requeridas=body.get("habilidades_requeridas", []),
                kpis=body.get("kpis"),
                colaboradores_asignados=body.get("colaboradores_asignados"),
            )

        return upsert_puesto(body, get_departamentos_catalog())
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/inicio/departamentos/puestos-laborales", response_class=HTMLResponse)
def puestos_laborales_page(request: Request):
    from fastapi_modulo.main import render_backend_page
    initial_areas = get_departamentos_catalog()
    try:
        with open(PUESTOS_LABORALES_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        content = "<p>No se pudo cargar la vista de puestos laborales.</p>"
    content = content.replace("__INITIAL_AREAS__", json.dumps(initial_areas, ensure_ascii=False))
    return render_backend_page(
        request,
        title="Puestos laborales",
        description="Gestión de puestos laborales",
        content=content,
        hide_floating_actions=True,
        floating_actions_screen="personalization",
    )


@router.get("/inicio/departamentos/notebook-puesto", response_class=HTMLResponse)
def notebook_puesto_page(request: Request):
    return _render_empleados_placeholder(
        request,
        title="KPIs",
        description="Notebook del puesto laboral",
    )


@router.get("/inicio/departamentos/puestos-organizacionales", response_class=HTMLResponse)
def puestos_organizacionales_page(request: Request):
    return _render_empleados_placeholder(
        request,
        title="Puestos organizacionales",
        description="Gestión de puestos organizacionales",
    )


@router.get("/areas-organizacionales", response_class=HTMLResponse)
def areas_organizacionales_page(request: Request):
    return RedirectResponse(url="/inicio/departamentos", status_code=307)


@router.get("/api/inicio/departamentos")
def listar_departamentos():
    return list_departamentos_payload()

@router.post("/api/inicio/departamentos")
async def guardar_departamentos(request: Request, data: dict = Body(...)):
    _enforce_departamentos_write_permission(request)
    return save_departamentos_payload(data.get("data", []))


@router.delete("/api/inicio/departamentos/{code}")
def eliminar_departamento(request: Request, code: str):
    _enforce_departamentos_write_permission(request)
    return delete_departamento_payload(code)

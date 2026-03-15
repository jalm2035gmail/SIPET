from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from fastapi.responses import HTMLResponse, JSONResponse, Response

from fastapi_modulo.modulos.crm.modelos.crm_models import (
    ActividadCreate,
    ActividadUpdate,
    CampaniaCreate,
    CampaniaUpdate,
    ContactoCampaniaCreate,
    ContactoCreate,
    ContactoUpdate,
    NotaCreate,
    OportunidadCreate,
    OportunidadUpdate,
)
from fastapi_modulo.modulos.crm.modelos.crm_store import (
    add_contacto_campania,
    create_actividad,
    create_campania,
    create_contacto,
    create_nota,
    create_oportunidad,
    delete_actividad,
    delete_contacto,
    delete_nota,
    delete_oportunidad,
    get_contacto,
    get_crm_resumen,
    list_actividades,
    list_campanias,
    list_contactos,
    list_contactos_campania,
    list_notas,
    list_oportunidades,
    update_actividad,
    update_campania,
    update_contacto,
    update_oportunidad,
)

_MODULE_DIR = Path(__file__).resolve().parents[1]
_CRM_TEMPLATE_PATH = _MODULE_DIR / "vistas" / "crm.html"
_CRM_JS_PATH = _MODULE_DIR / "static" / "js" / "crm.js"


def _require_crm_access(request: Request) -> None:
    from fastapi_modulo.main import _get_user_app_access, is_admin_or_superadmin

    if is_admin_or_superadmin(request):
        return
    app_access = _get_user_app_access(request)
    if "CRM" not in app_access:
        raise HTTPException(status_code=403, detail="Acceso restringido al módulo CRM")


def _load_file(path: os.PathLike[str] | str, fallback: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return fallback


router = APIRouter(dependencies=[Depends(_require_crm_access)])


def _render_no_access_crm_page(
    request: Request,
    *,
    title: str,
    description: str,
) -> HTMLResponse:
    from fastapi_modulo.main import _render_no_access_module_page

    return _render_no_access_module_page(
        request,
        title=title,
        description=description,
        message="Sin acceso, consulte con el administrador",
    )


# ── Vista principal ────────────────────────────────────────────────────────────

@router.get("/crm", response_class=HTMLResponse)
def crm_page(request: Request):
    from fastapi_modulo.main import render_backend_page

    content = _load_file(_CRM_TEMPLATE_PATH, "<p>No se pudo cargar la vista CRM.</p>")
    return render_backend_page(
        request,
        title="CRM",
        description="Gestión de contactos, oportunidades, actividades y campañas.",
        content=content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/api/crm/assets/crm.js")
def crm_js_asset() -> Response:
    body = _load_file(_CRM_JS_PATH, "console.error('CRM JS no disponible');")
    return Response(body, media_type="application/javascript")


@router.get("/crm/contactos", response_class=HTMLResponse)
def crm_contactos_page(request: Request):
    return _render_no_access_crm_page(
        request,
        title="Contactos",
        description="Contactos de CRM.",
    )


@router.get("/crm/oportunidades", response_class=HTMLResponse)
def crm_oportunidades_page(request: Request):
    return _render_no_access_crm_page(
        request,
        title="Oportunidades",
        description="Oportunidades de CRM.",
    )


@router.get("/crm/actividades", response_class=HTMLResponse)
def crm_actividades_page(request: Request):
    return _render_no_access_crm_page(
        request,
        title="Actividades",
        description="Actividades de CRM.",
    )


@router.get("/crm/notas", response_class=HTMLResponse)
def crm_notas_page(request: Request):
    return _render_no_access_crm_page(
        request,
        title="Notas",
        description="Notas de CRM.",
    )


@router.get("/crm/campanias", response_class=HTMLResponse)
def crm_campanias_page(request: Request):
    return _render_no_access_crm_page(
        request,
        title="Campañas",
        description="Campañas de CRM.",
    )


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("/api/crm/resumen")
def crm_resumen():
    return JSONResponse(get_crm_resumen())


# ── Contactos ──────────────────────────────────────────────────────────────────

@router.get("/api/crm/contactos")
def api_list_contactos(tipo: str = ""):
    return JSONResponse(list_contactos(tipo or None))


@router.get("/api/crm/contactos/{contacto_id}")
def api_get_contacto(contacto_id: int):
    obj = get_contacto(contacto_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    return JSONResponse(obj)


@router.post("/api/crm/contactos")
def api_create_contacto(body: ContactoCreate):
    try:
        return JSONResponse(create_contacto(body.model_dump()), status_code=201)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Ya existe un contacto con ese email")


@router.put("/api/crm/contactos/{contacto_id}")
def api_update_contacto(contacto_id: int, body: ContactoUpdate):
    result = update_contacto(contacto_id, body.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    return JSONResponse(result)


@router.delete("/api/crm/contactos/{contacto_id}")
def api_delete_contacto(contacto_id: int):
    if not delete_contacto(contacto_id):
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    return JSONResponse({"ok": True})


# ── Oportunidades ─────────────────────────────────────────────────────────────

@router.get("/api/crm/oportunidades")
def api_list_oportunidades(contacto_id: int = 0, etapa: str = ""):
    return JSONResponse(
        list_oportunidades(contacto_id or None, etapa or None)
    )


@router.post("/api/crm/oportunidades")
def api_create_oportunidad(body: OportunidadCreate):
    data = body.model_dump()
    if data.get("fecha_cierre_est"):
        data["fecha_cierre_est"] = data["fecha_cierre_est"]
    return JSONResponse(create_oportunidad(data), status_code=201)


@router.put("/api/crm/oportunidades/{oportunidad_id}")
def api_update_oportunidad(oportunidad_id: int, body: OportunidadUpdate):
    result = update_oportunidad(oportunidad_id, body.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada")
    return JSONResponse(result)


@router.delete("/api/crm/oportunidades/{oportunidad_id}")
def api_delete_oportunidad(oportunidad_id: int):
    if not delete_oportunidad(oportunidad_id):
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada")
    return JSONResponse({"ok": True})


# ── Actividades ───────────────────────────────────────────────────────────────

@router.get("/api/crm/actividades")
def api_list_actividades(
    contacto_id: int = 0,
    oportunidad_id: int = 0,
    completada: str = "",
):
    completada_bool = None
    if completada == "true":
        completada_bool = True
    elif completada == "false":
        completada_bool = False
    return JSONResponse(
        list_actividades(contacto_id or None, oportunidad_id or None, completada_bool)
    )


@router.post("/api/crm/actividades")
def api_create_actividad(body: ActividadCreate):
    return JSONResponse(create_actividad(body.model_dump()), status_code=201)


@router.put("/api/crm/actividades/{actividad_id}")
def api_update_actividad(actividad_id: int, body: ActividadUpdate):
    result = update_actividad(actividad_id, body.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")
    return JSONResponse(result)


@router.delete("/api/crm/actividades/{actividad_id}")
def api_delete_actividad(actividad_id: int):
    if not delete_actividad(actividad_id):
        raise HTTPException(status_code=404, detail="Actividad no encontrada")
    return JSONResponse({"ok": True})


# ── Notas ─────────────────────────────────────────────────────────────────────

@router.get("/api/crm/notas")
def api_list_notas(contacto_id: int = 0, oportunidad_id: int = 0):
    return JSONResponse(
        list_notas(contacto_id or None, oportunidad_id or None)
    )


@router.post("/api/crm/notas")
def api_create_nota(body: NotaCreate):
    return JSONResponse(create_nota(body.model_dump()), status_code=201)


@router.delete("/api/crm/notas/{nota_id}")
def api_delete_nota(nota_id: int):
    if not delete_nota(nota_id):
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    return JSONResponse({"ok": True})


# ── Campañas ──────────────────────────────────────────────────────────────────

@router.get("/api/crm/campanias")
def api_list_campanias(estado: str = ""):
    return JSONResponse(list_campanias(estado or None))


@router.post("/api/crm/campanias")
def api_create_campania(body: CampaniaCreate):
    return JSONResponse(create_campania(body.model_dump()), status_code=201)


@router.put("/api/crm/campanias/{campania_id}")
def api_update_campania(campania_id: int, body: CampaniaUpdate):
    result = update_campania(campania_id, body.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    return JSONResponse(result)


# ── Contacto–Campaña ──────────────────────────────────────────────────────────

@router.get("/api/crm/campanias/{campania_id}/contactos")
def api_list_contactos_campania(campania_id: int):
    return JSONResponse(list_contactos_campania(campania_id))


@router.post("/api/crm/campanias/contactos")
def api_add_contacto_campania(body: ContactoCampaniaCreate):
    return JSONResponse(add_contacto_campania(body.model_dump()), status_code=201)

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from fastapi.responses import HTMLResponse, JSONResponse, Response

from fastapi_modulo.modulos.auditoria.aud_models import (
    AuditoriaCreate,
    AuditoriaUpdate,
    HallazgoCreate,
    HallazgoUpdate,
    RecomendacionCreate,
    RecomendacionUpdate,
    SeguimientoCreate,
)
from fastapi_modulo.modulos.auditoria.aud_store import (
    create_auditoria,
    create_hallazgo,
    create_recomendacion,
    create_seguimiento,
    delete_auditoria,
    delete_hallazgo,
    delete_recomendacion,
    delete_seguimiento,
    get_aud_resumen,
    get_auditoria,
    get_hallazgo,
    get_recomendacion,
    list_auditorias,
    list_hallazgos,
    list_recomendaciones,
    list_seguimiento,
    update_auditoria,
    update_hallazgo,
    update_recomendacion,
)

_MODULE_DIR = os.path.dirname(__file__)


def _require_auditoria_access(request: Request) -> None:
    from fastapi_modulo.main import is_admin_or_superadmin, _get_user_app_access
    if is_admin_or_superadmin(request):
        return
    if "Auditoria" in _get_user_app_access(request):
        return
    raise HTTPException(status_code=403, detail="Acceso restringido al módulo Auditoría")


router = APIRouter(dependencies=[Depends(_require_auditoria_access)])


# ── Vista HTML ────────────────────────────────────────────────────────────────

@router.get("/auditoria", response_class=HTMLResponse)
def auditoria_page(request: Request):
    from fastapi_modulo.main import render_backend_page
    html_path = os.path.join(_MODULE_DIR, "auditoria.html")
    with open(html_path, encoding="utf-8") as fh:
        content = fh.read()
    return render_backend_page(
        request,
        title="Auditoría",
        description="Gestión de auditorías, hallazgos, recomendaciones y seguimiento.",
        content=content,
        hide_floating_actions=True,
        show_page_header=False,
    )


# ── JS asset ──────────────────────────────────────────────────────────────────

@router.get("/api/auditoria/assets/auditoria.js")
def auditoria_js():
    js_path = os.path.join(_MODULE_DIR, "auditoria.js")
    with open(js_path, encoding="utf-8") as fh:
        return Response(content=fh.read(), media_type="application/javascript")


# ── Resumen ───────────────────────────────────────────────────────────────────

@router.get("/api/auditoria/resumen")
def api_resumen():
    return JSONResponse(get_aud_resumen())


# ── Auditorías ────────────────────────────────────────────────────────────────

@router.get("/api/auditoria/auditorias")
def api_list_auditorias(estado: str = "", tipo: str = ""):
    return JSONResponse(list_auditorias(estado or None, tipo or None))


@router.get("/api/auditoria/auditorias/{auditoria_id}")
def api_get_auditoria(auditoria_id: int):
    obj = get_auditoria(auditoria_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    return JSONResponse(obj)


@router.post("/api/auditoria/auditorias")
def api_create_auditoria(body: AuditoriaCreate):
    try:
        return JSONResponse(create_auditoria(body.model_dump()), status_code=201)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Ya existe una auditoría con ese código")


@router.put("/api/auditoria/auditorias/{auditoria_id}")
def api_update_auditoria(auditoria_id: int, body: AuditoriaUpdate):
    obj = update_auditoria(auditoria_id, body.model_dump(exclude_unset=True))
    if not obj:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    return JSONResponse(obj)


@router.delete("/api/auditoria/auditorias/{auditoria_id}")
def api_delete_auditoria(auditoria_id: int):
    if not delete_auditoria(auditoria_id):
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    return JSONResponse({"ok": True})


# ── Hallazgos ─────────────────────────────────────────────────────────────────

@router.get("/api/auditoria/hallazgos")
def api_list_hallazgos(auditoria_id: int = 0, nivel_riesgo: str = "", estado: str = ""):
    return JSONResponse(list_hallazgos(
        auditoria_id or None,
        nivel_riesgo or None,
        estado or None,
    ))


@router.get("/api/auditoria/hallazgos/{hallazgo_id}")
def api_get_hallazgo(hallazgo_id: int):
    obj = get_hallazgo(hallazgo_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado")
    return JSONResponse(obj)


@router.post("/api/auditoria/hallazgos")
def api_create_hallazgo(body: HallazgoCreate):
    return JSONResponse(create_hallazgo(body.model_dump()), status_code=201)


@router.put("/api/auditoria/hallazgos/{hallazgo_id}")
def api_update_hallazgo(hallazgo_id: int, body: HallazgoUpdate):
    obj = update_hallazgo(hallazgo_id, body.model_dump(exclude_unset=True))
    if not obj:
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado")
    return JSONResponse(obj)


@router.delete("/api/auditoria/hallazgos/{hallazgo_id}")
def api_delete_hallazgo(hallazgo_id: int):
    if not delete_hallazgo(hallazgo_id):
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado")
    return JSONResponse({"ok": True})


# ── Recomendaciones ───────────────────────────────────────────────────────────

@router.get("/api/auditoria/recomendaciones")
def api_list_recomendaciones(hallazgo_id: int = 0, estado: str = "", auditoria_id: int = 0):
    return JSONResponse(list_recomendaciones(
        hallazgo_id or None,
        estado or None,
        auditoria_id or None,
    ))


@router.get("/api/auditoria/recomendaciones/{rec_id}")
def api_get_recomendacion(rec_id: int):
    obj = get_recomendacion(rec_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Recomendación no encontrada")
    return JSONResponse(obj)


@router.post("/api/auditoria/recomendaciones")
def api_create_recomendacion(body: RecomendacionCreate):
    return JSONResponse(create_recomendacion(body.model_dump()), status_code=201)


@router.put("/api/auditoria/recomendaciones/{rec_id}")
def api_update_recomendacion(rec_id: int, body: RecomendacionUpdate):
    obj = update_recomendacion(rec_id, body.model_dump(exclude_unset=True))
    if not obj:
        raise HTTPException(status_code=404, detail="Recomendación no encontrada")
    return JSONResponse(obj)


@router.delete("/api/auditoria/recomendaciones/{rec_id}")
def api_delete_recomendacion(rec_id: int):
    if not delete_recomendacion(rec_id):
        raise HTTPException(status_code=404, detail="Recomendación no encontrada")
    return JSONResponse({"ok": True})


# ── Seguimiento ───────────────────────────────────────────────────────────────

@router.get("/api/auditoria/seguimiento")
def api_list_seguimiento(recomendacion_id: int = 0):
    return JSONResponse(list_seguimiento(recomendacion_id or None))


@router.post("/api/auditoria/seguimiento")
def api_create_seguimiento(body: SeguimientoCreate):
    data = body.model_dump()
    if data.get("fecha") is None:
        from datetime import date
        data["fecha"] = date.today()
    return JSONResponse(create_seguimiento(data), status_code=201)


@router.delete("/api/auditoria/seguimiento/{seg_id}")
def api_delete_seguimiento(seg_id: int):
    if not delete_seguimiento(seg_id):
        raise HTTPException(status_code=404, detail="Entrada de seguimiento no encontrada")
    return JSONResponse({"ok": True})

from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from fastapi_modulo.modulos.intelicoop.intelicoop_models import (
    CampaniaCreate,
    ContactoCampaniaCreate,
    CuentaCreate,
    CreditoCreate,
    HistorialPagoCreate,
    ProspectoCreate,
    ScoringEvaluateInput,
    SeguimientoCampaniaCreate,
    SocioCreate,
    TransaccionCreate,
)
from fastapi_modulo.modulos.intelicoop.intelicoop_scoring import evaluate_scoring, summarize_scoring
from fastapi_modulo.modulos.intelicoop.intelicoop_store import (
    create_campana,
    create_contacto_campania,
    create_cuenta,
    create_credito,
    create_historial_pago,
    create_prospecto,
    create_scoring_result,
    create_seguimiento_campania,
    create_socio,
    create_transaccion,
    ensure_intelicoop_schema,
    get_basic_catalogs,
    get_ahorros_resumen,
    get_credito,
    get_credito_detail,
    get_dashboard_resumen,
    list_campanas,
    list_contactos_campania,
    list_cuentas,
    list_creditos,
    list_historial_pagos,
    list_prospectos,
    list_scoring_results,
    list_seguimientos_campania,
    list_socios,
    list_transacciones,
)

def require_intelicoop_access(request: Request) -> None:
    from fastapi_modulo.main import _get_user_app_access, is_admin_or_superadmin

    if is_admin_or_superadmin(request):
        return
    app_access = _get_user_app_access(request)
    if "Intelicoop" not in app_access:
        raise HTTPException(status_code=403, detail="Acceso restringido a Intelicoop")


router = APIRouter(dependencies=[Depends(require_intelicoop_access)])
INTELICOOP_TEMPLATE_PATH = os.path.join("fastapi_modulo", "modulos", "intelicoop", "intelicoop.html")
INTELICOOP_JS_PATH = os.path.join("fastapi_modulo", "modulos", "intelicoop", "intelicoop.js")


def _load_file(path: str, fallback: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return fallback


@router.get("/intelicoop", response_class=HTMLResponse)
def intelicoop_redirect() -> RedirectResponse:
    return RedirectResponse(url="/inicio/intelicoop", status_code=307)


@router.get("/inicio/intelicoop", response_class=HTMLResponse)
def intelicoop_page(request: Request):
    from fastapi_modulo.main import render_backend_page

    ensure_intelicoop_schema()
    content = _load_file(INTELICOOP_TEMPLATE_PATH, "<p>No se pudo cargar la vista de Intelicoop.</p>")
    return render_backend_page(
        request,
        title="Intelicoop",
        description="Modulo SIPET para socios, creditos, ahorros, campanas y scoring.",
        content=content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/api/intelicoop/assets/intelicoop.js")
def intelicoop_js_asset() -> Response:
    body = _load_file(INTELICOOP_JS_PATH, "console.error('Intelicoop JS no disponible');")
    return Response(body, media_type="application/javascript")


@router.get("/api/intelicoop/socios")
def api_list_socios():
    return JSONResponse(list_socios())


@router.post("/api/intelicoop/socios")
def api_create_socio(payload: SocioCreate):
    try:
        return JSONResponse(create_socio(payload.model_dump()), status_code=201)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/api/intelicoop/creditos")
def api_list_creditos():
    return JSONResponse(list_creditos())


@router.get("/api/intelicoop/creditos/{credito_id}")
def api_get_credito(credito_id: int):
    credito = get_credito(credito_id)
    if not credito:
        raise HTTPException(status_code=404, detail="Credito no encontrado.")
    return JSONResponse(credito)


@router.get("/api/intelicoop/creditos/{credito_id}/detalle")
def api_get_credito_detail(credito_id: int):
    credito = get_credito_detail(credito_id)
    if not credito:
        raise HTTPException(status_code=404, detail="Credito no encontrado.")
    return JSONResponse(credito)


@router.post("/api/intelicoop/creditos")
def api_create_credito(payload: CreditoCreate):
    try:
        credito = create_credito(payload.model_dump())
        score, recomendacion, riesgo, model_version = evaluate_scoring(
            ingreso_mensual=payload.ingreso_mensual,
            deuda_actual=payload.deuda_actual,
            antiguedad_meses=payload.antiguedad_meses,
        )
        scoring = create_scoring_result(
            {
                "solicitud_id": f"cred-{credito['id']}",
                "socio_id": credito["socio_id"],
                "credito_id": credito["id"],
                "ingreso_mensual": payload.ingreso_mensual,
                "deuda_actual": payload.deuda_actual,
                "antiguedad_meses": payload.antiguedad_meses,
                "score": score,
                "recomendacion": recomendacion,
                "riesgo": riesgo,
                "model_version": model_version,
            }
        )
        return JSONResponse({"credito": credito, "scoring": scoring}, status_code=201)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/api/intelicoop/creditos/{credito_id}/pagos")
def api_list_credito_pagos(credito_id: int):
    return JSONResponse(list_historial_pagos(credito_id))


@router.post("/api/intelicoop/creditos/pagos")
def api_create_credito_pago(payload: HistorialPagoCreate):
    try:
        return JSONResponse(create_historial_pago(payload.model_dump()), status_code=201)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/api/intelicoop/ahorros/resumen")
def api_ahorros_resumen():
    return JSONResponse(get_ahorros_resumen())


@router.get("/api/intelicoop/ahorros/cuentas")
def api_list_cuentas():
    return JSONResponse(list_cuentas())


@router.post("/api/intelicoop/ahorros/cuentas")
def api_create_cuenta(payload: CuentaCreate):
    try:
        return JSONResponse(create_cuenta(payload.model_dump()), status_code=201)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/api/intelicoop/ahorros/transacciones")
def api_list_transacciones():
    return JSONResponse(list_transacciones())


@router.post("/api/intelicoop/ahorros/transacciones")
def api_create_transaccion(payload: TransaccionCreate):
    try:
        return JSONResponse(create_transaccion(payload.model_dump()), status_code=201)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/api/intelicoop/campanas")
def api_list_campanas():
    return JSONResponse(list_campanas())


@router.post("/api/intelicoop/campanas")
def api_create_campana(payload: CampaniaCreate):
    return JSONResponse(create_campana(payload.model_dump()), status_code=201)


@router.get("/api/intelicoop/campanas/contactos")
def api_list_contactos_campania():
    return JSONResponse(list_contactos_campania())


@router.post("/api/intelicoop/campanas/contactos")
def api_create_contacto_campania(payload: ContactoCampaniaCreate):
    try:
        return JSONResponse(create_contacto_campania(payload.model_dump()), status_code=201)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/api/intelicoop/campanas/seguimientos")
def api_list_seguimientos_campania():
    return JSONResponse(list_seguimientos_campania())


@router.post("/api/intelicoop/campanas/seguimientos")
def api_create_seguimiento_campania(payload: SeguimientoCampaniaCreate):
    try:
        return JSONResponse(create_seguimiento_campania(payload.model_dump()), status_code=201)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/api/intelicoop/prospectos")
def api_list_prospectos():
    return JSONResponse(list_prospectos())


@router.post("/api/intelicoop/prospectos")
def api_create_prospecto(payload: ProspectoCreate):
    return JSONResponse(create_prospecto(payload.model_dump()), status_code=201)


@router.post("/api/intelicoop/scoring/evaluar")
def api_scoring_evaluar(payload: ScoringEvaluateInput):
    score, recomendacion, riesgo, model_version = evaluate_scoring(
        ingreso_mensual=payload.ingreso_mensual,
        deuda_actual=payload.deuda_actual,
        antiguedad_meses=payload.antiguedad_meses,
    )
    result = create_scoring_result(
        {
            "solicitud_id": payload.solicitud_id or f"sol-{uuid.uuid4().hex[:10]}",
            "socio_id": payload.socio_id,
            "credito_id": payload.credito_id,
            "ingreso_mensual": payload.ingreso_mensual,
            "deuda_actual": payload.deuda_actual,
            "antiguedad_meses": payload.antiguedad_meses,
            "score": score,
            "recomendacion": recomendacion,
            "riesgo": riesgo,
            "model_version": model_version,
        }
    )
    return JSONResponse(result, status_code=201)


@router.get("/api/intelicoop/scoring/resumen")
def api_scoring_resumen():
    return JSONResponse(summarize_scoring(list_scoring_results()))


@router.get("/api/intelicoop/dashboard/resumen")
def api_dashboard_resumen():
    return JSONResponse(get_dashboard_resumen())


@router.get("/api/intelicoop/catalogos/basicos")
def api_basic_catalogs():
    return JSONResponse(get_basic_catalogs())

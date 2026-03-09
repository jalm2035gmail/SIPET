import os
import csv
import json
from io import StringIO

from fastapi import APIRouter, Body, File, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi_modulo.modulos.proyectando.data_store import (
    DEFAULT_DATOS_GENERALES,
    load_activo_fijo_compras_editor,
    load_activo_fijo_depreciacion_editor,
    load_activo_fijo_revaluaciones_editor,
    load_activo_fijo_saldos_editor,
    get_if_period_columns,
    load_activo_fijo_resumen,
    load_gastos_resumen,
    load_ifb_rows_for_template,
    load_informacion_financiera_catalogo,
    load_datos_preliminares_store,
    normalize_ifb_rows_json,
    sync_ifb_activo_total_from_crecimiento,
    sync_ifb_financiamiento_from_crecimiento,
    save_activo_fijo_compras_editor,
    save_datos_preliminares_store,
)

router = APIRouter()
DATOS_PRELIMINARES_TEMPLATE_PATH = os.path.join(
    "fastapi_modulo", "templates", "modulos", "proyectando", "datos_preliminares.html"
)
DATOS_PRELIMINARES_JS_PATH = os.path.join(
    "fastapi_modulo", "modulos", "proyectando", "datos_preliminares.js"
)
PROYECTANDO_CSS_PATH = os.path.join(
    "fastapi_modulo", "modulos", "proyectando", "proyectando.css"
)
ACTIVO_FIJO_TEMPLATE_PATH = os.path.join(
    "fastapi_modulo", "templates", "modulos", "proyectando", "activo_fijo.html"
)
ACTIVO_FIJO_JS_PATH = os.path.join(
    "fastapi_modulo", "modulos", "proyectando", "activo_fijo.js"
)
OTRAS_CUENTAS_ACTIVO_TEMPLATE_PATH = os.path.join(
    "fastapi_modulo", "templates", "modulos", "proyectando", "otras_cuentas_activo.html"
)
CARTERA_PRESTAMOS_TEMPLATE_PATH = os.path.join(
    "fastapi_modulo", "templates", "modulos", "proyectando", "cartera_prestamos.html"
)
RECURSOS_LIQUIDOS_TEMPLATE_PATH = os.path.join(
    "fastapi_modulo", "templates", "modulos", "proyectando", "recursos_liquidos.html"
)
GASTOS_TEMPLATE_PATH = os.path.join(
    "fastapi_modulo", "templates", "modulos", "proyectando", "gastos.html"
)
TASA_REFERENCIA_TEMPLATE_PATH = os.path.join(
    "fastapi_modulo", "templates", "modulos", "proyectando", "tasa_referencia.html"
)


def _get_colores_context() -> dict:
    from fastapi_modulo.main import get_colores_context
    return get_colores_context()


@router.get("/modulos/proyectando/datos_preliminares.js")
def proyectando_datos_preliminares_js():
    try:
        with open(DATOS_PRELIMINARES_JS_PATH, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        content = "console.error('No se pudo cargar datos_preliminares.js');"
    return Response(content, media_type="application/javascript")


@router.get("/modulos/proyectando/proyectando.css")
def proyectando_css():
    try:
        with open(PROYECTANDO_CSS_PATH, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        content = "/* No se pudo cargar proyectando.css */"
    return Response(content, media_type="text/css")


@router.get("/modulos/proyectando/activo_fijo.js")
def proyectando_activo_fijo_js():
    try:
        with open(ACTIVO_FIJO_JS_PATH, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        content = "console.error('No se pudo cargar activo_fijo.js');"
    return Response(content, media_type="application/javascript")


@router.post("/api/proyectando/datos-preliminares/datos-generales")
async def guardar_datos_preliminares_generales(data: dict = Body(...)):
    current = load_datos_preliminares_store()
    updated = dict(current)
    for key in DEFAULT_DATOS_GENERALES.keys():
        if key in data:
            if key == "ifb_rows_json":
                updated[key] = normalize_ifb_rows_json(str(data.get(key) or "").strip())
            else:
                updated[key] = str(data.get(key) or "").strip()
    save_datos_preliminares_store(updated)
    return {"success": True, "data": updated}


@router.get("/api/proyectando/datos-preliminares")
async def obtener_datos_preliminares():
    data = load_datos_preliminares_store()
    synced = sync_ifb_activo_total_from_crecimiento(data)
    synced = sync_ifb_financiamiento_from_crecimiento(synced)
    if synced.get("ifb_rows_json", "") != data.get("ifb_rows_json", ""):
        save_datos_preliminares_store(synced)
    return {"success": True, "data": synced}


@router.get("/api/proyectando/datos-preliminares/informacion-financiera")
async def obtener_catalogo_informacion_financiera():
    return {"success": True, "data": load_informacion_financiera_catalogo()}


@router.get("/api/proyectando/datos-preliminares/informacion-financiera/plantilla.csv")
async def descargar_plantilla_informacion_financiera_csv():
    store = load_datos_preliminares_store()
    periods = [period for period in get_if_period_columns(store) if str(period.get("key", "")).startswith("-")]
    rows = load_ifb_rows_for_template(store)
    headers = [
        "fila",
        "nivel",
        "cuenta",
        "descripcion",
    ] + [period["label"] for period in periods]
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    for idx, row in enumerate(rows, start=1):
        payload = {
            "fila": idx,
            "nivel": str(row.get("nivel") or "").strip(),
            "cuenta": str(row.get("cuenta") or "").strip(),
            "descripcion": str(row.get("descripcion") or "").strip(),
        }
        values = row.get("values") if isinstance(row.get("values"), dict) else {}
        for period in periods:
            payload[period["label"]] = str(values.get(period["key"]) or "").strip()
        writer.writerow(payload)
    headers_out = {"Content-Disposition": 'attachment; filename="informacion_financiera_plantilla.csv"'}
    return Response(output.getvalue(), media_type="text/csv; charset=utf-8", headers=headers_out)


@router.post("/api/proyectando/datos-preliminares/informacion-financiera/importar.csv")
async def importar_informacion_financiera_csv(file: UploadFile = File(...)):
    filename = (file.filename or "").lower()
    if not filename.endswith(".csv"):
        return JSONResponse({"success": False, "error": "El archivo debe ser CSV (.csv)."}, status_code=400)

    content = await file.read()
    raw_text = content.decode("utf-8-sig", errors="ignore").strip()
    if not raw_text:
        return JSONResponse({"success": False, "error": "El archivo CSV está vacío."}, status_code=400)

    store = load_datos_preliminares_store()
    periods = [period for period in get_if_period_columns(store) if str(period.get("key", "")).startswith("-")]
    expected_headers = [
        "fila",
        "nivel",
        "cuenta",
        "descripcion",
    ] + [period["label"] for period in periods]
    reader = csv.DictReader(StringIO(raw_text))
    if not reader.fieldnames or any(header not in reader.fieldnames for header in expected_headers):
        return JSONResponse({"success": False, "error": "Encabezados CSV no válidos."}, status_code=400)

    base_rows = load_ifb_rows_for_template(store)
    by_cuenta = {str(row.get("cuenta") or "").strip(): row for row in base_rows}
    updated_count = 0
    for raw_row in reader:
        cuenta = str((raw_row or {}).get("cuenta") or "").strip()
        target = by_cuenta.get(cuenta)
        if target is None:
            try:
                fila_idx = int(str((raw_row or {}).get("fila") or "").strip() or "0")
            except ValueError:
                fila_idx = 0
            if 1 <= fila_idx <= len(base_rows):
                target = base_rows[fila_idx - 1]
        if target is None:
            continue
        target_cuenta = str(target.get("cuenta") or "").strip()
        if target_cuenta == "__validacion__":
            continue
        values = target.get("values") if isinstance(target.get("values"), dict) else {}
        changed = False
        for period in periods:
            new_value = str((raw_row or {}).get(period["label"]) or "").strip()
            if values.get(period["key"], "") != new_value:
                changed = True
            values[period["key"]] = new_value
        target["values"] = values
        if changed:
            updated_count += 1

    if updated_count == 0:
        return JSONResponse(
            {"success": False, "error": "El CSV no contiene filas compatibles para actualizar."},
            status_code=400,
        )

    store["ifb_rows_json"] = normalize_ifb_rows_json(json.dumps(base_rows, ensure_ascii=False))
    save_datos_preliminares_store(store)
    return {"success": True, "data": {"rows": len(base_rows), "updated": updated_count}}


@router.get("/api/proyectando/datos-preliminares/activo-fijo")
async def obtener_activo_fijo_resumen():
    return {"success": True, "data": load_activo_fijo_resumen()}


@router.get("/api/proyectando/activo-fijo/compras")
async def obtener_activo_fijo_compras():
    return {"success": True, "data": load_activo_fijo_compras_editor()}


@router.post("/api/proyectando/activo-fijo/compras")
async def guardar_activo_fijo_compras(data: dict = Body(...)):
    rows = data.get("rows") if isinstance(data, dict) else []
    return {"success": True, "data": save_activo_fijo_compras_editor(rows)}


@router.get("/api/proyectando/activo-fijo/saldos")
async def obtener_activo_fijo_saldos():
    return {"success": True, "data": load_activo_fijo_saldos_editor()}


@router.get("/api/proyectando/activo-fijo/revaluaciones")
async def obtener_activo_fijo_revaluaciones():
    return {"success": True, "data": load_activo_fijo_revaluaciones_editor()}


@router.get("/api/proyectando/activo-fijo/depreciacion")
async def obtener_activo_fijo_depreciacion():
    return {"success": True, "data": load_activo_fijo_depreciacion_editor()}


@router.get("/api/proyectando/datos-preliminares/gastos")
async def obtener_gastos_resumen():
    return {"success": True, "data": load_gastos_resumen()}


@router.get("/proyectando/datos-preliminares", response_class=HTMLResponse)
def proyectando_datos_preliminares_page(request: Request):
    try:
        with open(DATOS_PRELIMINARES_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        content = "<p>No se pudo cargar la vista de datos preliminares.</p>"

    return request.app.state.templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "title": "Datos preliminares",
            "description": "",
            "page_title": "Datos preliminares",
            "page_description": "",
            "section_label": "",
            "section_title": "",
            "content": content,
            "hide_floating_actions": True,
            "show_page_header": False,
            "view_buttons_html": "",
            "colores": _get_colores_context(),
        },
    )


@router.get("/proyectando/activo-fijo", response_class=HTMLResponse)
def proyectando_activo_fijo_page(request: Request):
    try:
        with open(ACTIVO_FIJO_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        content = "<p>No se pudo cargar la vista de activo fijo.</p>"

    return request.app.state.templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "title": "Activo fijo",
            "description": "",
            "page_title": "Activo fijo",
            "page_description": "",
            "section_label": "",
            "section_title": "",
            "content": content,
            "hide_floating_actions": True,
            "show_page_header": False,
            "view_buttons_html": "",
            "colores": _get_colores_context(),
        },
    )


@router.get("/proyectando/otras-cuentas-activo", response_class=HTMLResponse)
def proyectando_otras_cuentas_activo_page(request: Request):
    try:
        with open(OTRAS_CUENTAS_ACTIVO_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        content = "<p>No se pudo cargar la vista de otras cuentas de activo.</p>"

    return request.app.state.templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "title": "Otras cuentas de activo",
            "description": "",
            "page_title": "Otras cuentas de activo",
            "page_description": "",
            "section_label": "",
            "section_title": "",
            "content": content,
            "hide_floating_actions": True,
            "show_page_header": False,
            "view_buttons_html": "",
            "colores": _get_colores_context(),
        },
    )


@router.get("/proyectando/cartera-prestamos", response_class=HTMLResponse)
def proyectando_cartera_prestamos_page(request: Request):
    try:
        with open(CARTERA_PRESTAMOS_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        content = "<p>No se pudo cargar la vista de cartera de préstamos.</p>"

    return request.app.state.templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "title": "Cartera de préstamos",
            "description": "",
            "page_title": "Cartera de préstamos",
            "page_description": "",
            "section_label": "",
            "section_title": "",
            "content": content,
            "hide_floating_actions": True,
            "show_page_header": False,
            "view_buttons_html": "",
            "colores": _get_colores_context(),
        },
    )


@router.get("/proyectando/recursos-liquidos", response_class=HTMLResponse)
def proyectando_recursos_liquidos_page(request: Request):
    try:
        with open(RECURSOS_LIQUIDOS_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        content = "<p>No se pudo cargar la vista de liquidez.</p>"

    return request.app.state.templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "title": "Liquidez",
            "description": "",
            "page_title": "Liquidez",
            "page_description": "",
            "section_label": "",
            "section_title": "",
            "content": content,
            "hide_floating_actions": True,
            "show_page_header": False,
            "view_buttons_html": "",
            "colores": _get_colores_context(),
        },
    )


@router.get("/proyectando/gastos", response_class=HTMLResponse)
def proyectando_gastos_page(request: Request):
    try:
        with open(GASTOS_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        content = "<p>No se pudo cargar la vista de gastos.</p>"

    return request.app.state.templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "title": "Gastos",
            "description": "",
            "page_title": "Gastos",
            "page_description": "",
            "section_label": "",
            "section_title": "",
            "content": content,
            "hide_floating_actions": True,
            "show_page_header": False,
            "view_buttons_html": "",
            "colores": _get_colores_context(),
        },
    )


@router.get("/proyectando/tasa-referencia", response_class=HTMLResponse)
def proyectando_tasa_referencia_page(request: Request):
    try:
        with open(TASA_REFERENCIA_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        content = "<p>No se pudo cargar la vista de tasa de referencia.</p>"

    return request.app.state.templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "title": "Tasa de referencia",
            "description": "",
            "page_title": "Tasa de referencia",
            "page_description": "",
            "section_label": "",
            "section_title": "",
            "content": content,
            "hide_floating_actions": True,
            "show_page_header": False,
            "view_buttons_html": "",
            "colores": _get_colores_context(),
        },
    )

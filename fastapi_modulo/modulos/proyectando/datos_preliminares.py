import os
import csv
import json
from io import StringIO

from fastapi import APIRouter, Body, File, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi_modulo.modulos.proyectando.data_store import (
    DEFAULT_DATOS_GENERALES,
    get_if_period_columns,
    load_activo_fijo_resumen,
    load_gastos_resumen,
    load_ifb_rows_for_template,
    load_informacion_financiera_catalogo,
    load_datos_preliminares_store,
    normalize_ifb_rows_json,
    sync_ifb_activo_total_from_crecimiento,
    save_datos_preliminares_store,
)

router = APIRouter()
DATOS_PRELIMINARES_TEMPLATE_PATH = os.path.join(
    "fastapi_modulo", "templates", "modulos", "proyectando", "datos_preliminares.html"
)


def _get_colores_context() -> dict:
    from fastapi_modulo.main import get_colores_context
    return get_colores_context()


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

from fastapi import APIRouter, Body, File, Request, UploadFile
from pathlib import Path

from fastapi.responses import HTMLResponse, JSONResponse, Response

from fastapi_modulo.modulos.proyectando import presupuesto_service

router = APIRouter()
PRESUPUESTO_JS_PATH = Path(__file__).with_name("presupuesto.js")


@router.get("/presupuesto.js")
def proyectando_presupuesto_js():
    try:
        content = PRESUPUESTO_JS_PATH.read_text(encoding="utf-8")
    except OSError:
        content = "console.error('No se pudo cargar presupuesto.js');"
    return Response(content, media_type="application/javascript")


@router.get("/descargar-csv-presupuesto", tags=["presupuesto"])
async def descargar_csv_presupuesto():
    return await presupuesto_service.descargar_csv_presupuesto()


@router.get("/presupuesto-reportes-filtros", tags=["presupuesto"])
async def obtener_presupuesto_reportes_filtros(nivel: str = "consolidado"):
    return await presupuesto_service.obtener_presupuesto_reportes_filtros(nivel=nivel)


@router.get("/descargar-plantilla-presupuesto", tags=["presupuesto"])
async def descargar_plantilla_presupuesto():
    return await presupuesto_service.descargar_plantilla_presupuesto()


@router.post("/importar-control-mensual", tags=["presupuesto"])
async def importar_control_mensual(file: UploadFile = File(...)):
    return await presupuesto_service.importar_control_mensual(file=file)


@router.get("/control-mensual-datos", tags=["presupuesto"])
async def obtener_control_mensual_datos():
    return await presupuesto_service.obtener_control_mensual_datos()


@router.post("/guardar-control-mensual", tags=["presupuesto"])
async def guardar_control_mensual(data: dict = Body(default={})):
    return await presupuesto_service.guardar_control_mensual(data=data)


@router.get("/presupuesto", response_class=HTMLResponse)
def proyectando_presupuesto_page(request: Request):
    return presupuesto_service.proyectando_presupuesto_page(request)


@router.get("/presupuesto/base-ia", response_class=HTMLResponse)
def presupuesto_base_ia_page(request: Request):
    return presupuesto_service.presupuesto_base_ia_page(request)


@router.get("/presupuesto/base-ia/datos", response_class=JSONResponse)
def presupuesto_base_ia_api(request: Request):
    return presupuesto_service.presupuesto_base_ia_api(request)


@router.get("/presupuesto/base-ia/contenido", response_class=JSONResponse)
def presupuesto_base_ia_contenido_get(request: Request):
    return presupuesto_service.presupuesto_base_ia_contenido_get(request)


@router.put("/presupuesto/base-ia/contenido", response_class=JSONResponse)
def presupuesto_base_ia_contenido_put(request: Request, data: dict = Body(...)):
    return presupuesto_service.presupuesto_base_ia_contenido_put(request, data=data)


@router.post("/presupuesto/base-ia/refresh", response_class=JSONResponse)
def presupuesto_base_ia_refresh(request: Request, data: dict = Body(default={})):
    return presupuesto_service.presupuesto_base_ia_refresh(request, data=data)

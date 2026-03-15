from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from fastapi_modulo.modulos.cartera_prestamos.servicios.export_service import (
    exportar_aging_cartera_excel,
    exportar_cartera_vencida_excel,
    exportar_promesas_pago_excel,
    exportar_resumen_ejecutivo_pdf,
    exportar_seguimiento_por_gestor_excel,
)
from fastapi_modulo.modulos.cartera_prestamos.servicios.gestion_service import obtener_snapshot_gestion
from fastapi_modulo.modulos.cartera_prestamos.servicios.indicadores_service import construir_indicadores, guardar_indicadores
from fastapi_modulo.modulos.cartera_prestamos.servicios.mesa_control_service import obtener_snapshot_mesa_control
from fastapi_modulo.modulos.cartera_prestamos.servicios.recuperacion_service import obtener_snapshot_recuperacion
from .dependencies import get_role_permissions, require_section_access


router = APIRouter(prefix="/api/cartera-prestamos", tags=["cartera-prestamos"])


@router.get("/mesa-control")
def cartera_prestamos_mesa_control_api(request: Request):
    require_section_access(request, "resumen")
    return obtener_snapshot_mesa_control()


@router.get("/gestion")
def cartera_prestamos_gestion_api(request: Request):
    require_section_access(request, "gestion")
    return obtener_snapshot_gestion()


@router.get("/recuperacion")
def cartera_prestamos_recuperacion_api(request: Request, meta_periodo: Decimal = Query(default=Decimal("0"))):
    require_section_access(request, "recuperacion")
    return obtener_snapshot_recuperacion(meta_periodo=meta_periodo)


@router.get("/indicadores")
def cartera_prestamos_indicadores_api(request: Request):
    require_section_access(request, "indicadores")
    return [item.model_dump(mode="json") for item in construir_indicadores()]


@router.post("/indicadores/refresh")
def cartera_prestamos_refresh_indicadores_api(request: Request):
    require_section_access(request, "indicadores")
    return [item.model_dump(mode="json") for item in guardar_indicadores()]


@router.get("/permissions")
def cartera_prestamos_permissions_api(request: Request):
    return get_role_permissions(request)


@router.get("/export/cartera-vencida.xls")
def exportar_cartera_vencida_api(request: Request):
    require_section_access(request, "cobranza")
    return _excel_response(exportar_cartera_vencida_excel(), "cartera_vencida")


@router.get("/export/promesas-pago.xls")
def exportar_promesas_pago_api(request: Request):
    require_section_access(request, "cobranza")
    return _excel_response(exportar_promesas_pago_excel(), "promesas_pago")


@router.get("/export/seguimiento-gestor.xls")
def exportar_seguimiento_gestor_api(request: Request):
    require_section_access(request, "cobranza")
    return _excel_response(exportar_seguimiento_por_gestor_excel(), "seguimiento_gestor")


@router.get("/export/aging-cartera.xls")
def exportar_aging_cartera_api(request: Request):
    require_section_access(request, "resumen")
    return _excel_response(exportar_aging_cartera_excel(), "aging_cartera")


@router.get("/export/resumen-ejecutivo.pdf")
def exportar_resumen_ejecutivo_api(request: Request):
    require_section_access(request, "resumen")
    return Response(
        content=exportar_resumen_ejecutivo_pdf(),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="resumen_ejecutivo.pdf"'},
    )


def _excel_response(content: bytes, filename: str) -> Response:
    return Response(
        content=content,
        media_type="application/vnd.ms-excel",
        headers={"Content-Disposition": f'attachment; filename="{filename}.xls"'},
    )

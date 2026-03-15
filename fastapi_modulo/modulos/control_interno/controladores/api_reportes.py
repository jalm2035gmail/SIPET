from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Response
from fastapi.responses import HTMLResponse, JSONResponse

from fastapi_modulo.modulos.control_interno.servicios.reporte_service import (
    datos_reporte_service,
    exportar_excel_service,
    exportar_html_service,
    exportar_pdf_service,
)

router = APIRouter()


def _report_data(
    *,
    tipo: Optional[str] = "completo",
    anio: Optional[int] = None,
    componente_coso: Optional[str] = None,
    nivel_riesgo: Optional[str] = None,
    estado_hallazgo: Optional[str] = None,
    estado_actividad: Optional[str] = None,
    estado_control: Optional[str] = None,
    resultado_ev: Optional[str] = None,
    control_id: Optional[int] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    q: Optional[str] = None,
    version: Optional[str] = "detallada",
):
    return datos_reporte_service(
        tipo=tipo or "completo",
        anio=anio,
        componente_coso=componente_coso,
        nivel_riesgo=nivel_riesgo,
        estado_hallazgo=estado_hallazgo,
        estado_actividad=estado_actividad,
        estado_control=estado_control,
        resultado_ev=resultado_ev,
        control_id=control_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        q=q,
        version=version or "detallada",
    )


@router.get("/api/ci-reporte/datos")
def api_datos(
    tipo: Optional[str] = "completo",
    anio: Optional[int] = None,
    componente_coso: Optional[str] = None,
    nivel_riesgo: Optional[str] = None,
    estado_hallazgo: Optional[str] = None,
    estado_actividad: Optional[str] = None,
    estado_control: Optional[str] = None,
    resultado_ev: Optional[str] = None,
    control_id: Optional[int] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    q: Optional[str] = None,
    version: Optional[str] = "detallada",
):
    return JSONResponse(_report_data(
        tipo=tipo,
        anio=anio,
        componente_coso=componente_coso,
        nivel_riesgo=nivel_riesgo,
        estado_hallazgo=estado_hallazgo,
        estado_actividad=estado_actividad,
        estado_control=estado_control,
        resultado_ev=resultado_ev,
        control_id=control_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        q=q,
        version=version,
    ))


@router.get("/api/ci-reporte/excel")
def api_excel(
    tipo: Optional[str] = "completo",
    anio: Optional[int] = None,
    componente_coso: Optional[str] = None,
    nivel_riesgo: Optional[str] = None,
    estado_hallazgo: Optional[str] = None,
    estado_actividad: Optional[str] = None,
    estado_control: Optional[str] = None,
    resultado_ev: Optional[str] = None,
    control_id: Optional[int] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    q: Optional[str] = None,
    version: Optional[str] = "detallada",
):
    payload = _report_data(
        tipo=tipo,
        anio=anio,
        componente_coso=componente_coso,
        nivel_riesgo=nivel_riesgo,
        estado_hallazgo=estado_hallazgo,
        estado_actividad=estado_actividad,
        estado_control=estado_control,
        resultado_ev=resultado_ev,
        control_id=control_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        q=q,
        version=version,
    )
    content, media_type, filename = exportar_excel_service(payload)
    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/api/ci-reporte/html", response_class=HTMLResponse)
def api_html(
    tipo: Optional[str] = "completo",
    anio: Optional[int] = None,
    componente_coso: Optional[str] = None,
    nivel_riesgo: Optional[str] = None,
    estado_hallazgo: Optional[str] = None,
    estado_actividad: Optional[str] = None,
    estado_control: Optional[str] = None,
    resultado_ev: Optional[str] = None,
    control_id: Optional[int] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    q: Optional[str] = None,
    version: Optional[str] = "detallada",
):
    return HTMLResponse(content=exportar_html_service(_report_data(
        tipo=tipo,
        anio=anio,
        componente_coso=componente_coso,
        nivel_riesgo=nivel_riesgo,
        estado_hallazgo=estado_hallazgo,
        estado_actividad=estado_actividad,
        estado_control=estado_control,
        resultado_ev=resultado_ev,
        control_id=control_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        q=q,
        version=version,
    )))


@router.get("/api/ci-reporte/pdf")
def api_pdf(
    tipo: Optional[str] = "completo",
    anio: Optional[int] = None,
    componente_coso: Optional[str] = None,
    nivel_riesgo: Optional[str] = None,
    estado_hallazgo: Optional[str] = None,
    estado_actividad: Optional[str] = None,
    estado_control: Optional[str] = None,
    resultado_ev: Optional[str] = None,
    control_id: Optional[int] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    q: Optional[str] = None,
    version: Optional[str] = "resumida",
):
    payload = _report_data(
        tipo=tipo,
        anio=anio,
        componente_coso=componente_coso,
        nivel_riesgo=nivel_riesgo,
        estado_hallazgo=estado_hallazgo,
        estado_actividad=estado_actividad,
        estado_control=estado_control,
        resultado_ev=resultado_ev,
        control_id=control_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        q=q,
        version=version,
    )
    content, media_type, filename = exportar_pdf_service(payload)
    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


__all__ = ["router"]

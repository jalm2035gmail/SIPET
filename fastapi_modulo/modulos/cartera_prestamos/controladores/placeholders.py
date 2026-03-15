from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from .dependencies import render_section_page


router = APIRouter()


@router.get("/cartera-prestamos/indicadores-financieros", response_class=HTMLResponse)
def cartera_prestamos_indicadores_financieros_page(request: Request):
    return render_section_page(request, "indicadores_financieros")


@router.get("/cartera-prestamos/dashboard-general", response_class=HTMLResponse)
def cartera_prestamos_dashboard_general_page(request: Request):
    return render_section_page(request, "dashboard_general")


@router.get("/cartera-prestamos/alertas-riesgos", response_class=HTMLResponse)
def cartera_prestamos_alertas_riesgos_page(request: Request):
    return render_section_page(request, "alertas_riesgos")


@router.get("/cartera-prestamos/listado-creditos", response_class=HTMLResponse)
def cartera_prestamos_listado_creditos_page(request: Request):
    return render_section_page(request, "listado_creditos")


@router.get("/cartera-prestamos/operacion-comercial", response_class=HTMLResponse)
def cartera_prestamos_operacion_comercial_page(request: Request):
    return render_section_page(request, "operacion_comercial")


@router.get("/cartera-prestamos/castigos", response_class=HTMLResponse)
def cartera_prestamos_castigos_page(request: Request):
    return render_section_page(request, "castigos")


@router.get("/cartera-prestamos/reestructuracion", response_class=HTMLResponse)
def cartera_prestamos_reestructuracion_page(request: Request):
    return render_section_page(request, "reestructuracion")


@router.get("/cartera-prestamos/indicadores", response_class=HTMLResponse)
def cartera_prestamos_indicadores_page(request: Request):
    return render_section_page(request, "indicadores")


@router.get("/cartera-prestamos/planeacion-estrategica", response_class=HTMLResponse)
def cartera_prestamos_planeacion_estrategica_page(request: Request):
    return render_section_page(request, "planeacion_estrategica")


@router.get("/cartera-prestamos/gobernanza", response_class=HTMLResponse)
def cartera_prestamos_gobernanza_page(request: Request):
    return render_section_page(request, "gobernanza")


@router.get("/cartera-prestamos/gestion-cobranza", response_class=HTMLResponse)
def cartera_prestamos_gestion_cobranza_page(request: Request):
    return render_section_page(request, "gestion_cobranza")


@router.get("/cartera-prestamos/cartera-vencida", response_class=HTMLResponse)
def cartera_prestamos_cartera_vencida_page(request: Request):
    return render_section_page(request, "cartera_vencida")


@router.get("/cartera-prestamos/promesas-pago", response_class=HTMLResponse)
def cartera_prestamos_promesas_pago_page(request: Request):
    return render_section_page(request, "promesas_pago")


@router.get("/cartera-prestamos/visitas-gestiones", response_class=HTMLResponse)
def cartera_prestamos_visitas_gestiones_page(request: Request):
    return render_section_page(request, "visitas_gestiones")


@router.get("/cartera-prestamos/configuracion", response_class=HTMLResponse)
def cartera_prestamos_configuracion_page(request: Request):
    return render_section_page(request, "configuracion")

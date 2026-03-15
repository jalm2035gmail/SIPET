from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from .dependencies import render_section_page


router = APIRouter()


@router.get("/resumen_ejecutivo", response_class=HTMLResponse)
@router.get("/resumen_ejecutivo/", response_class=HTMLResponse)
@router.get("/resumen-ejecutivo", response_class=HTMLResponse)
def cartera_prestamos_resumen_ejecutivo_page(request: Request):
    return render_section_page(request, "resumen")


@router.get("/cartera-prestamos/mesa-control", response_class=HTMLResponse)
def cartera_prestamos_mesa_control_page(request: Request):
    return render_section_page(request, "mesa_control")


@router.get("/cartera-prestamos/gestion", response_class=HTMLResponse)
def cartera_prestamos_gestion_page(request: Request):
    return render_section_page(request, "gestion")


@router.get("/cartera-prestamos/recuperacion", response_class=HTMLResponse)
def cartera_prestamos_recuperacion_page(request: Request):
    return render_section_page(request, "recuperacion")

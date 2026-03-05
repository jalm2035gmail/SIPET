"""
Router para el módulo IA de SIPET (fase 0)
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="fastsipet_modulo/modulos/ia")

@router.get("/ia", response_class=HTMLResponse)
def ia_home(request: Request):
    """
    Página principal del módulo IA (Fase 0).
    """
    return templates.TemplateResponse("ia.html", {"request": request})

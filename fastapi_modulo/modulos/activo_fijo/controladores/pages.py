from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

router = APIRouter()

MODULE_DIR = Path(__file__).resolve().parents[1]
VIEWS_DIR = MODULE_DIR / "vistas"
STATIC_CSS_DIR = MODULE_DIR / "static" / "css"
STATIC_JS_DIR = MODULE_DIR / "static" / "js"
LEGACY_TEMPLATES_DIR = Path("fastapi_modulo") / "templates" / "modulos" / "activo_fijo"


def _render_legacy_template_page(
    request: Request,
    *,
    filename: str,
    title: str,
    description: str,
) -> HTMLResponse:
    from fastapi_modulo.main import _render_no_access_module_page, render_backend_page

    template_path = LEGACY_TEMPLATES_DIR / filename
    try:
        with open(template_path, encoding="utf-8") as file:
            content = file.read()
    except OSError:
        return _render_no_access_module_page(
            request,
            title=title,
            description=description,
        )
    return render_backend_page(
        request,
        title=title,
        description=description,
        content=content,
        hide_floating_actions=True,
        show_page_header=True,
    )


@router.get("/activo-fijo", response_class=HTMLResponse)
def activo_fijo_page(request: Request):
    from fastapi_modulo.main import render_backend_page

    html_path = VIEWS_DIR / "activo_fijo.html"
    menus_path = VIEWS_DIR / "activo_fijo_menus.html"
    with open(html_path, encoding="utf-8") as file:
        content = file.read()
    with open(menus_path, encoding="utf-8") as file:
        menus_content = file.read()
    content = content.replace("<!-- AF_MODULE_MENUS -->", menus_content)
    return render_backend_page(
        request,
        title="Gestión de Activo Fijo",
        description="Depreciaciones, asignaciones, mantenimiento y bajas de activos.",
        content=content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/api/activo-fijo/assets/activo_fijo.css")
def activo_fijo_css():
    css_path = STATIC_CSS_DIR / "activo_fijo.css"
    with open(css_path, encoding="utf-8") as file:
        content = file.read()
    return Response(content=content, media_type="text/css")


@router.get("/api/activo-fijo/assets/activo_fijo/{asset_name}.js")
def activo_fijo_js_asset(asset_name: str):
    js_path = STATIC_JS_DIR / "activo_fijo" / f"{asset_name}.js"
    with open(js_path, encoding="utf-8") as file:
        content = file.read()
    return Response(content=content, media_type="application/javascript")


@router.get("/api/activo-fijo/assets/activo_fijo.js")
def activo_fijo_js_legacy_asset():
    content = (
        "import '/api/activo-fijo/assets/activo_fijo/index.js';\n"
    )
    return Response(content=content, media_type="application/javascript")


@router.get("/activo-fijo/custodia", response_class=HTMLResponse)
def activo_fijo_custodia_page(request: Request):
    return _render_legacy_template_page(
        request,
        filename="custodia.html",
        title="Custodia",
        description="Préstamo y resguardo de activos fijos.",
    )


@router.get("/activo-fijo/flotilla", response_class=HTMLResponse)
def activo_fijo_flotilla_page(request: Request):
    return _render_legacy_template_page(
        request,
        filename="flotilla.html",
        title="Flotilla",
        description="Gestión de flotilla vehicular.",
    )


@router.get("/activo-fijo/salones", response_class=HTMLResponse)
def activo_fijo_salones_page(request: Request):
    return _render_legacy_template_page(
        request,
        filename="salones.html",
        title="Salones",
        description="Solicitud y gestión de salas de capacitación.",
    )

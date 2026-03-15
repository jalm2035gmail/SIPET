from __future__ import annotations

import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

_MKT_DIGITAL_TEMPLATE_PATH = os.path.join(
    "fastapi_modulo",
    "modulos",
    "mkt",
    "vistas",
    "mkt_digital.html",
)
_MKT_WHATSAPP_TEMPLATE_PATH = os.path.join(
    "fastapi_modulo",
    "modulos",
    "mkt",
    "vistas",
    "whatsapp_business.html",
)
_MKT_REDES_TEMPLATE_PATH = os.path.join(
    "fastapi_modulo",
    "modulos",
    "mkt",
    "vistas",
    "redes_sociales.html",
)


def _load_template(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


@router.get("/mkt/digital", response_class=HTMLResponse)
def mkt_digital_page(request: Request):
    from fastapi_modulo.main import _render_no_access_module_page, render_backend_page

    content = _load_template(_MKT_DIGITAL_TEMPLATE_PATH)
    if content is None:
        return _render_no_access_module_page(
            request,
            title="Mkt digital",
            description="Emailing y automatización de campañas digitales.",
        )
    return render_backend_page(
        request,
        title="Mkt digital",
        description="Emailing y automatización de campañas digitales.",
        content=content,
        hide_floating_actions=True,
        show_page_header=True,
    )


@router.get("/mkt/whatsapp-business", response_class=HTMLResponse)
def mkt_whatsapp_business_page(request: Request):
    from fastapi_modulo.main import _render_no_access_module_page, render_backend_page

    content = _load_template(_MKT_WHATSAPP_TEMPLATE_PATH)
    if content is None:
        return _render_no_access_module_page(
            request,
            title="WhatsApp Business",
            description="Gestión de atención y campañas conversacionales.",
        )
    return render_backend_page(
        request,
        title="WhatsApp Business",
        description="Gestión de atención y campañas conversacionales.",
        content=content,
        hide_floating_actions=True,
        show_page_header=True,
    )


@router.get("/mkt/redes-sociales", response_class=HTMLResponse)
def mkt_redes_sociales_page(request: Request):
    from fastapi_modulo.main import _render_no_access_module_page, render_backend_page

    content = _load_template(_MKT_REDES_TEMPLATE_PATH)
    if content is None:
        return _render_no_access_module_page(
            request,
            title="Gestión de redes sociales",
            description="Contenido, comunidad y campañas de redes sociales.",
        )
    return render_backend_page(
        request,
        title="Gestión de redes sociales",
        description="Contenido, comunidad y campañas de redes sociales.",
        content=content,
        hide_floating_actions=True,
        show_page_header=True,
    )

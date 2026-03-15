"""Utilidades compartidas del router de capacitacion."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response

from fastapi_modulo.modulos.capacitacion.controladores.capacitacion_menu import build_menu_html
from fastapi_modulo.modulos.capacitacion.controladores.dependencies import render_backend_page_safe

MODULE_DIR = Path(__file__).resolve().parents[1]
VIEWS_DIR = MODULE_DIR / "vistas"
STATIC_DIR = MODULE_DIR / "static"
STATIC_JS_DIR = STATIC_DIR / "js"
STATIC_CSS_DIR = STATIC_DIR / "css"
IMAGE_DIR = MODULE_DIR / "imagenes"
PARTIAL_RE = re.compile(r"\{\{\>\s*([^\}]+?)\s*\}\}")

def _load_view_file(file_path: Path, seen: Optional[set[Path]] = None) -> str:
    resolved = file_path.resolve()
    chain = seen or set()
    if resolved in chain:
        raise RuntimeError(f"Referencia circular de vista: {resolved}")
    with open(resolved, encoding="utf-8") as fh:
        content = fh.read()
    next_seen = set(chain)
    next_seen.add(resolved)

    def _replace(match: re.Match[str]) -> str:
        include_name = match.group(1).strip()
        include_path = (VIEWS_DIR / include_name).resolve()
        if not str(include_path).startswith(str(VIEWS_DIR.resolve())):
            raise RuntimeError(f"Include fuera de vistas: {include_name}")
        return _load_view_file(include_path, seen=next_seen)

    return PARTIAL_RE.sub(_replace, content)


def load_module_page(filename: str, replacements: Optional[dict[str, str]] = None) -> str:
    file_path = VIEWS_DIR / filename
    content = _load_view_file(file_path)
    for old, new in (replacements or {}).items():
        content = content.replace(old, new)
    return content


def asset_response(path: Path, media_type: str) -> Response:
    with open(path, encoding="utf-8") as fh:
        return Response(content=fh.read(), media_type=media_type)


def render_module_page(
    *,
    title: str,
    request: Request,
    filename: str,
    menu_key: str | None = None,
    replacements: Optional[dict[str, str]] = None,
) -> HTMLResponse:
    html_content = load_module_page(filename, replacements=replacements)
    menu_html = build_menu_html(menu_key)
    return render_backend_page_safe(
        request,
        title=title,
        description="Capacitación y formación para colaboradores",
        content=menu_html + html_content,
        hide_floating_actions=True,
        show_page_header=False,
        section_label="Capacitación",
    )


def render_editor_page(*, pres_id: int, request: Request, menu_key: str | None = None) -> HTMLResponse:
    sidebar_scroll_css = """
    <style>
        .ui-sidebar-left, .ui-sidebar-nav {
            overflow-y: auto !important;
            max-height: calc(100vh - 60px) !important;
            scrollbar-width: thin;
        }
        .ui-sidebar-left::-backendkit-scrollbar, .ui-sidebar-nav::-backendkit-scrollbar {
            width: 4px;
        }
        .ui-sidebar-left::-backendkit-scrollbar-thumb, .ui-sidebar-nav::-backendkit-scrollbar-thumb {
            background-color: rgba(255, 255, 255, 0.2);
            border-radius: 4px;
        }
    </style>
    """
    html_content = load_module_page("capacitacion_editor.html", replacements={"__PRES_ID__": str(pres_id)})
    menu_html = build_menu_html(menu_key)
    return render_backend_page_safe(
        request,
        title="Editor de Presentación",
        description="Capacitación y formación para colaboradores",
        content=menu_html + sidebar_scroll_css + html_content,
        hide_floating_actions=True,
        show_page_header=False,
        section_label="Capacitación",
    )


def image_response(filename: str) -> FileResponse:
    safe_name = os.path.basename(str(filename or "").strip())
    file_path = IMAGE_DIR / safe_name
    if not safe_name or not file_path.exists():
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    return FileResponse(file_path)


__all__ = [
    "STATIC_CSS_DIR",
    "STATIC_DIR",
    "STATIC_JS_DIR",
    "asset_response",
    "image_response",
    "load_module_page",
    "render_editor_page",
    "render_module_page",
]

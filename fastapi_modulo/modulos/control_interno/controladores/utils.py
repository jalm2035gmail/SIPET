from __future__ import annotations

from pathlib import Path
import re

_MODULE_DIR = Path(__file__).resolve().parents[1]
_VISTAS_DIR = _MODULE_DIR / "vistas"
_STATIC_DIR = _MODULE_DIR / "static"
_CORE_BOUND = False


def module_dir() -> Path:
    return _MODULE_DIR


def main_template_path() -> Path:
    return _VISTAS_DIR


def static_dir() -> Path:
    return _STATIC_DIR


def load_template(filename: str) -> str:
    path = _VISTAS_DIR / filename
    try:
        return _render_template_file(path)
    except OSError:
        return "<p>No se pudo cargar la vista.</p>"


def _render_template_file(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    pattern = re.compile(r"\{\{\s*include:\s*([^\}]+)\s*\}\}")

    def replace(match: re.Match[str]) -> str:
        include_name = match.group(1).strip()
        include_path = _VISTAS_DIR / include_name
        if not include_path.exists():
            return ""
        return _render_template_file(include_path)

    return pattern.sub(replace, content)


def bind_core_symbols() -> None:
    global _CORE_BOUND
    if _CORE_BOUND:
        return
    from fastapi_modulo import main as core
    globals()["render_backend_page"] = getattr(core, "render_backend_page")
    _CORE_BOUND = True


def render_module_page(request, *, title: str, description: str, template_name: str):
    bind_core_symbols()
    return render_backend_page(
        request,
        title=title,
        description=description,
        content=load_template(template_name),
        hide_floating_actions=True,
        show_page_header=False,
    )


__all__ = [
    "bind_core_symbols",
    "load_template",
    "main_template_path",
    "module_dir",
    "render_module_page",
    "static_dir",
]

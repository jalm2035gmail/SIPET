from pathlib import Path
from typing import Optional
import re
import shutil

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="fastapi_modulo/templates")

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ASSET_FIELDS = ["favicon", "logo_empresa", "logo_usuario", "svg_fondo", "svg_defecto"]


def _safe_ext(filename: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    if not suffix:
        return ".bin"
    cleaned = re.sub(r"[^a-z0-9.]", "", suffix)
    if not cleaned.startswith("."):
        cleaned = f".{cleaned}"
    return cleaned or ".bin"


def _asset_candidates(field: str) -> list[Path]:
    return sorted(UPLOAD_DIR.glob(f"{field}.*"), key=lambda path: path.stat().st_mtime, reverse=True)


def _asset_default_candidates(field: str) -> list[Path]:
    return sorted(UPLOAD_DIR.glob(f"default_{field}.*"), key=lambda path: path.stat().st_mtime, reverse=True)


def _asset_path(field: str) -> Optional[Path]:
    candidates = _asset_candidates(field)
    return candidates[0] if candidates else None


def _asset_default_path(field: str) -> Optional[Path]:
    candidates = _asset_default_candidates(field)
    return candidates[0] if candidates else None


def _clear_asset(field: str) -> bool:
    removed = False
    for path in _asset_candidates(field):
        path.unlink(missing_ok=True)
        removed = True
    return removed


def _clear_asset_default(field: str) -> bool:
    removed = False
    for path in _asset_default_candidates(field):
        path.unlink(missing_ok=True)
        removed = True
    return removed


def _save_default_from_path(field: str, source_path: Path) -> Optional[str]:
    if not source_path.exists():
        return None
    _clear_asset_default(field)
    filename = f"default_{field}{source_path.suffix.lower()}"
    target = UPLOAD_DIR / filename
    shutil.copy2(source_path, target)
    return filename


def _restore_active_from_default(field: str) -> Optional[str]:
    default_path = _asset_default_path(field)
    if not default_path:
        return None
    _clear_asset(field)
    filename = f"{field}{default_path.suffix.lower()}"
    target = UPLOAD_DIR / filename
    shutil.copy2(default_path, target)
    return filename


def _bootstrap_defaults_from_active() -> None:
    for field in ASSET_FIELDS:
        if _asset_default_path(field):
            continue
        active = _asset_path(field)
        if active:
            _save_default_from_path(field, active)


async def _store_asset(field: str, file_obj: UploadFile) -> Optional[str]:
    if not file_obj or not (file_obj.filename or "").strip():
        return None
    _clear_asset(field)
    ext = _safe_ext(file_obj.filename)
    contents = await file_obj.read()
    # Optimizar imagen antes de guardar
    try:
        from fastapi_modulo.image_utils import optimize_image, profile_for_prefix
        contents, ext = optimize_image(contents, ext, profile=profile_for_prefix(field))
    except Exception:
        pass
    filename = f"{field}{ext}"
    target = UPLOAD_DIR / filename
    target.write_bytes(contents)
    _save_default_from_path(field, target)
    return filename


def _asset_url(filename: str) -> str:
    return f"/personalizar/uploads/{filename}"


def _assets_state() -> dict:
    _bootstrap_defaults_from_active()
    state = {}
    for field in ASSET_FIELDS:
        path = _asset_path(field)
        filename = path.name if path else ""
        default_path = _asset_default_path(field)
        default_filename = default_path.name if default_path else ""
        state[field] = {
            "filename": filename,
            "url": _asset_url(filename) if filename else "",
            "exists": bool(filename),
            "default_filename": default_filename,
            "has_default": bool(default_filename),
        }
    return state


@router.get("/personalizar/estado")
def personalizar_estado() -> JSONResponse:
    return JSONResponse({"ok": True, "assets": _assets_state()})


@router.get("/personalizar/uploads/{filename}")
def personalizar_upload(filename: str):
    safe_name = Path(filename).name
    if safe_name != filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo invalido")
    file_path = UPLOAD_DIR / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(file_path)


@router.post("/personalizar/restablecer-assets")
def restablecer_assets(request: Request) -> JSONResponse:
    from fastapi_modulo.main import require_superadmin
    require_superadmin(request)
    restored = []
    for field in ASSET_FIELDS:
        if _restore_active_from_default(field):
            restored.append(field)
    return JSONResponse({"ok": True, "restored": restored, "assets": _assets_state()})


@router.post("/personalizar/guardar")
async def guardar_personalizacion(
    request: Request,
    global_bg: Optional[str] = Form(None),
    section_bg: Optional[str] = Form(None),
    navbar_bg: Optional[str] = Form(None),
    navbar_text: Optional[str] = Form(None),
    sidebar_top: Optional[str] = Form(None),
    sidebar_bottom: Optional[str] = Form(None),
    sidebar_text: Optional[str] = Form(None),
    sidebar_icon: Optional[str] = Form(None),
    sidebar_hover: Optional[str] = Form(None),
    field_color: Optional[str] = Form(None),
    text_title: Optional[str] = Form(None),
    text_description: Optional[str] = Form(None),
    text_section_title: Optional[str] = Form(None),
    text_body: Optional[str] = Form(None),
    favicon: Optional[UploadFile] = File(None),
    logo_empresa: Optional[UploadFile] = File(None),
    logo_usuario: Optional[UploadFile] = File(None),
    svg_fondo: Optional[UploadFile] = File(None),
    svg_defecto: Optional[UploadFile] = File(None),
    remove_favicon: str = Form("0"),
    remove_logo_empresa: str = Form("0"),
    remove_logo_usuario: str = Form("0"),
    remove_svg_fondo: str = Form("0"),
    remove_svg_defecto: str = Form("0"),
):
    from fastapi_modulo.main import require_superadmin
    require_superadmin(request)
    del global_bg, section_bg, navbar_bg, navbar_text, sidebar_top, sidebar_bottom
    del sidebar_text, sidebar_icon, sidebar_hover, field_color
    del text_title, text_description, text_section_title, text_body

    file_map = {
        "favicon": favicon,
        "logo_empresa": logo_empresa,
        "logo_usuario": logo_usuario,
        "svg_fondo": svg_fondo,
        "svg_defecto": svg_defecto,
    }
    remove_map = {
        "favicon": remove_favicon,
        "logo_empresa": remove_logo_empresa,
        "logo_usuario": remove_logo_usuario,
        "svg_fondo": remove_svg_fondo,
        "svg_defecto": remove_svg_defecto,
    }

    updated = []
    removed = []

    for field in ASSET_FIELDS:
        if str(remove_map.get(field, "0")).strip() == "1":
            if _clear_asset(field):
                removed.append(field)

    for field, upload in file_map.items():
        saved = await _store_asset(field, upload) if upload else None
        if saved:
            updated.append(field)

    return JSONResponse(
        {
            "ok": True,
            "updated": updated,
            "removed": removed,
            "assets": _assets_state(),
        }
    )


@router.get("/personalizar", response_class=HTMLResponse)
def personalizar_page(request: Request):
    from fastapi_modulo.main import require_superadmin
    require_superadmin(request)
    with open(Path(__file__).resolve().parent / "personalizar.html", encoding="utf-8") as f:
        panel_html = f.read()
    section_label = ""
    section_title = ""
    from fastapi_modulo.main import get_colores_context
    return templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "title": "Personalización visual",
            "description": "Ajusta la paleta visual del sistema.",
            "page_title": "Personalización visual",
            "page_description": "Ajusta la paleta visual del sistema.",
            "section_label": section_label,
            "section_title": section_title,
            "content": panel_html,
            "floating_actions_html": "",
            "floating_actions_screen": "personalization",
            "hide_floating_actions": True,
            "show_page_header": True,
            "colores": get_colores_context(),
        },
    )

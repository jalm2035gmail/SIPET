from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse

from .dependencies import STATIC_DIR


router = APIRouter()


@router.get("/modulos/cartera_prestamos/static/{asset_path:path}")
def cartera_prestamos_static(asset_path: str):
    relative_path = Path(asset_path)
    target = (STATIC_DIR / relative_path).resolve()
    if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.is_file():
        return HTMLResponse(status_code=404)
    return FileResponse(target)

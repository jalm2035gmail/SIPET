from __future__ import annotations

import os
import secrets
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse

router = APIRouter()

BASE_TEMPLATE_PATH = os.path.join("fastapi_modulo", "templates", "modulos", "control_interno")
UPLOAD_DIR = "fastapi_modulo/uploads/documentos"
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


def _bind_core_symbols() -> None:
    if globals().get("_CORE_BOUND"):
        return
    from fastapi_modulo import main as core
    globals()["render_backend_page"] = getattr(core, "render_backend_page")
    globals()["_CORE_BOUND"] = True


def _load_template(filename: str) -> str:
    path = os.path.join(BASE_TEMPLATE_PATH, filename)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return "<p>No se pudo cargar la vista.</p>"


def _sanitize_name(name: str) -> str:
    import re
    name = os.path.splitext(name)[0]
    name = re.sub(r"[^\w\-]", "_", name)
    return name[:80]


async def _guardar_archivo(upload: UploadFile) -> dict:
    """Guarda el archivo subido y devuelve metadata."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    data = await upload.read()
    if not data:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="El archivo supera los 25 MB permitidos.")
    from datetime import datetime
    ext = os.path.splitext(upload.filename or "")[1].lower()
    base = _sanitize_name(os.path.splitext(upload.filename or "evidencia")[0])
    filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{base}_{secrets.token_hex(4)}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(data)
    return {
        "archivo_nombre":  upload.filename,
        "archivo_ruta":    path,
        "archivo_mime":    (upload.content_type or "application/octet-stream").strip(),
        "archivo_tamanio": len(data),
    }


# ── Página ────────────────────────────────────────────────────────────────────

@router.get("/control-interno/evidencias", response_class=HTMLResponse)
def evidencias_page(request: Request):
    _bind_core_symbols()
    return render_backend_page(
        request,
        title="Evidencias de control",
        description="Registro documental de la ejecución y evaluación de controles internos",
        content=_load_template("evidencia.html"),
        hide_floating_actions=True,
        show_page_header=False,
    )


# ── API: Listar ───────────────────────────────────────────────────────────────

@router.get("/api/ci-evidencia")
def api_listar(
    actividad_id:         Optional[int] = None,
    control_id:           Optional[int] = None,
    tipo:                 Optional[str] = None,
    resultado_evaluacion: Optional[str] = None,
    q:                    Optional[str] = None,
):
    from fastapi_modulo.modulos.control_interno.evidencia_store import (
        listar_evidencias, resumen_por_resultado
    )
    lista   = listar_evidencias(actividad_id=actividad_id, control_id=control_id,
                                tipo=tipo, resultado_evaluacion=resultado_evaluacion, q=q)
    resumen_bruto = resumen_por_resultado()
    resumen = {
        "total":  sum(resumen_bruto.values()),
        "conteo": resumen_bruto,
    }
    return JSONResponse({"evidencias": lista, "resumen": resumen})


@router.get("/api/ci-evidencia/{evidencia_id}")
def api_obtener(evidencia_id: int):
    from fastapi_modulo.modulos.control_interno.evidencia_store import obtener_evidencia
    ev = obtener_evidencia(evidencia_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidencia no encontrada.")
    return JSONResponse(ev)


# ── API: Crear (multipart) ────────────────────────────────────────────────────

@router.post("/api/ci-evidencia")
async def api_crear(
    titulo:               str = Form(...),
    tipo:                 str = Form("Documento"),
    fecha_evidencia:      str = Form(""),
    control_id:           str = Form(""),
    actividad_id:         str = Form(""),
    resultado_evaluacion: str = Form("Por evaluar"),
    descripcion:          str = Form(""),
    observaciones:        str = Form(""),
    archivo:              Optional[UploadFile] = File(None),
):
    from fastapi_modulo.modulos.control_interno.evidencia_store import crear_evidencia
    if not titulo.strip():
        raise HTTPException(status_code=422, detail="El título es obligatorio.")
    data = {
        "titulo":               titulo,
        "tipo":                 tipo,
        "fecha_evidencia":      fecha_evidencia or None,
        "control_id":           control_id or None,
        "actividad_id":         actividad_id or None,
        "resultado_evaluacion": resultado_evaluacion,
        "descripcion":          descripcion,
        "observaciones":        observaciones,
    }
    meta: dict = {}
    if archivo and archivo.filename:
        meta = await _guardar_archivo(archivo)
    try:
        ev = crear_evidencia(data, **meta)
        return JSONResponse(ev, status_code=201)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── API: Actualizar (multipart) ───────────────────────────────────────────────

@router.put("/api/ci-evidencia/{evidencia_id}")
async def api_actualizar(
    evidencia_id:         int,
    titulo:               str = Form(...),
    tipo:                 str = Form("Documento"),
    fecha_evidencia:      str = Form(""),
    control_id:           str = Form(""),
    actividad_id:         str = Form(""),
    resultado_evaluacion: str = Form("Por evaluar"),
    descripcion:          str = Form(""),
    observaciones:        str = Form(""),
    archivo:              Optional[UploadFile] = File(None),
):
    from fastapi_modulo.modulos.control_interno.evidencia_store import actualizar_evidencia
    data = {
        "titulo":               titulo,
        "tipo":                 tipo,
        "fecha_evidencia":      fecha_evidencia or None,
        "control_id":           control_id or None,
        "actividad_id":         actividad_id or None,
        "resultado_evaluacion": resultado_evaluacion,
        "descripcion":          descripcion,
        "observaciones":        observaciones,
    }
    meta: dict = {}
    if archivo and archivo.filename:
        meta = await _guardar_archivo(archivo)
    updated = actualizar_evidencia(evidencia_id, data, **meta)
    if not updated:
        raise HTTPException(status_code=404, detail="Evidencia no encontrada.")
    return JSONResponse(updated)


# ── API: Eliminar ─────────────────────────────────────────────────────────────

@router.delete("/api/ci-evidencia/{evidencia_id}")
def api_eliminar(evidencia_id: int):
    from fastapi_modulo.modulos.control_interno.evidencia_store import eliminar_evidencia
    if not eliminar_evidencia(evidencia_id):
        raise HTTPException(status_code=404, detail="Evidencia no encontrada.")
    return JSONResponse({"ok": True})


# ── API: Descargar archivo ────────────────────────────────────────────────────

@router.get("/api/ci-evidencia/{evidencia_id}/descargar")
def api_descargar(evidencia_id: int):
    from fastapi_modulo.modulos.control_interno.evidencia_store import (
        obtener_evidencia, obtener_ruta_archivo
    )
    ev   = obtener_evidencia(evidencia_id)
    ruta = obtener_ruta_archivo(evidencia_id)
    if not ruta or not os.path.exists(ruta):
        raise HTTPException(status_code=404, detail="Archivo no disponible.")
    # Validate path is within upload dir (prevent path traversal)
    safe_root = os.path.abspath(UPLOAD_DIR)
    target    = os.path.abspath(ruta)
    if not target.startswith(safe_root):
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    nombre = (ev or {}).get("archivo_nombre") or os.path.basename(ruta)
    mime   = (ev or {}).get("archivo_mime") or "application/octet-stream"
    return FileResponse(
        path=ruta,
        media_type=mime,
        filename=nombre,
    )

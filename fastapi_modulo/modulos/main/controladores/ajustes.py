from __future__ import annotations

import os
import sqlite3

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse

router = APIRouter()


@router.get("/ajustes/configuracion", response_class=HTMLResponse)
def ajustes_configuracion_page(request: Request):
    from fastapi_modulo import main as core

    core.require_admin_or_superadmin(request)
    return core._render_ajustes_configuracion_page(request)


@router.get("/api/ajustes/actualizacion")
def ajustes_actualizacion_estado(request: Request):
    from fastapi_modulo import main as core

    core.require_admin_or_superadmin(request)
    context = core._get_update_context(request)
    return {"success": True, **core._snapshot_update_state(context)}


@router.post("/api/ajustes/actualizacion/verificar")
def ajustes_actualizacion_verificar(request: Request):
    from datetime import datetime

    from fastapi_modulo import main as core

    core.require_admin_or_superadmin(request)
    context = core._get_update_context(request)
    try:
        manifest = core._fetch_update_manifest(context["manifest_url"])
        manifest_info = core._validate_update_manifest(context, manifest)
        snapshot = {
            "checked_at": datetime.utcnow().isoformat(),
            "version": manifest_info["version"],
            "strategy": manifest_info["strategy"],
            "branch": manifest_info["branch"],
            "channel": context["channel"],
            "notes": manifest_info["notes"],
            "manifest_url": context["manifest_url"],
        }
        core._write_json_file(context["files"]["manifest"], snapshot)
        core._append_update_history(
            context["host"],
            {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "checked",
                "target_version": manifest_info["version"],
            },
        )
        context = core._get_update_context(request)
        return {"success": True, **core._snapshot_update_state(context, manifest_info)}
    except Exception as exc:
        core._append_update_history(
            context["host"],
            {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "check_error",
                "target_version": "",
                "error": str(exc),
            },
        )
        return JSONResponse({"success": False, "error": str(exc)}, status_code=400)


@router.post("/api/ajustes/actualizacion/aplicar")
def ajustes_actualizacion_aplicar(request: Request):
    from datetime import datetime

    from fastapi_modulo import main as core

    core.require_admin_or_superadmin(request)
    context = core._get_update_context(request)
    try:
        manifest = core._fetch_update_manifest(context["manifest_url"])
        manifest_info = core._validate_update_manifest(context, manifest)
        if not manifest_info["update_available"]:
            return {"success": True, **core._snapshot_update_state(context, manifest_info)}
        job_payload = core._start_update_job(context, manifest_info)
        context = core._get_update_context(request)
        state = core._snapshot_update_state(context, manifest_info)
        state["last_job"] = job_payload
        return {"success": True, **state}
    except Exception as exc:
        core._append_update_history(
            context["host"],
            {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "start_error",
                "target_version": "",
                "error": str(exc),
            },
        )
        return JSONResponse({"success": False, "error": str(exc)}, status_code=400)


@router.get("/empresa/base-datos", response_class=HTMLResponse)
def empresa_base_datos_page(request: Request):
    from fastapi_modulo import main as core

    core.require_admin_or_superadmin(request)
    return core._render_database_tools_page(request)


@router.get("/empresa/base-datos/exportar")
def empresa_base_datos_exportar(request: Request):
    from datetime import datetime

    from fastapi_modulo import main as core

    core.require_admin_or_superadmin(request)
    db_info = core._get_request_database_info(request)
    if db_info["engine"] != "sqlite" or not db_info["path"]:
        raise HTTPException(status_code=400, detail="Exportación por archivo disponible solo en SQLite")
    db_path = os.path.abspath(db_info["path"])
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="No se encontró el archivo de base de datos")
    filename = f"sipet_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.db"
    return FileResponse(db_path, media_type="application/octet-stream", filename=filename)


@router.post("/empresa/base-datos/importar", response_class=HTMLResponse)
async def empresa_base_datos_importar(request: Request, db_file: UploadFile = File(...)):
    from urllib.parse import quote_plus

    from fastapi_modulo import main as core
    from fastapi_modulo import db as core_db

    core.require_admin_or_superadmin(request)
    db_info = core._get_request_database_info(request)
    if db_info["engine"] != "sqlite" or not db_info["path"]:
        return RedirectResponse(
            url="/empresa/base-datos?status=error&msg=Importación%20por%20archivo%20solo%20disponible%20en%20SQLite",
            status_code=303,
        )
    db_path = os.path.abspath(db_info["path"])
    ext = os.path.splitext((db_file.filename or "").lower())[1]
    if ext not in {".db", ".sqlite", ".sqlite3"}:
        return RedirectResponse(
            url="/empresa/base-datos?status=error&msg=Archivo%20inválido.%20Usa%20.db%2C%20.sqlite%20o%20.sqlite3",
            status_code=303,
        )
    raw = await db_file.read()
    if not raw:
        return RedirectResponse(
            url="/empresa/base-datos?status=error&msg=Archivo%20vacío",
            status_code=303,
        )
    tmp_path = f"{db_path}.upload.tmp"
    backup_path = f"{db_path}.bak"
    try:
        with open(tmp_path, "wb") as fh:
            fh.write(raw)
        with sqlite3.connect(tmp_path) as conn:
            conn.execute("PRAGMA schema_version;").fetchone()

        core_db.dispose_engine_for_host(db_info["host"])

        if os.path.exists(db_path):
            import shutil

            shutil.copy2(db_path, backup_path)
        os.replace(tmp_path, db_path)
        return RedirectResponse(
            url="/empresa/base-datos?status=ok&msg=Base%20de%20datos%20importada%20correctamente",
            status_code=303,
        )
    except Exception as exc:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return RedirectResponse(
            url=f"/empresa/base-datos?status=error&msg={quote_plus(str(exc) or 'Error al importar base de datos')}",
            status_code=303,
        )

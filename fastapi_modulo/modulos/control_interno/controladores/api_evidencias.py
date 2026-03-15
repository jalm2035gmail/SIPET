from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from fastapi_modulo.modulos.control_interno.controladores.dependencies import save_uploaded_evidence
from fastapi_modulo.modulos.control_interno.modelos.schemas import EvidenciaCreate, EvidenciaUpdate, dump_schema, validate_schema
from fastapi_modulo.modulos.control_interno.servicios import evidencia_service

router = APIRouter()


def _build_evidencia_payload(schema_cls, *, titulo: str, tipo: str, fecha_evidencia: str, control_id: str, actividad_id: str, resultado_evaluacion: str, descripcion: str, observaciones: str) -> dict:
    model = validate_schema(
        schema_cls,
        {
            "titulo": titulo or None,
            "tipo": tipo or None,
            "fecha_evidencia": fecha_evidencia or None,
            "control_id": control_id or None,
            "actividad_id": actividad_id or None,
            "resultado_evaluacion": resultado_evaluacion or None,
            "descripcion": descripcion or None,
            "observaciones": observaciones or None,
        },
    )
    return dump_schema(model, exclude_unset=schema_cls is EvidenciaUpdate)


@router.get("/api/ci-evidencia")
def api_listar(
    actividad_id: Optional[int] = None,
    control_id: Optional[int] = None,
    tipo: Optional[str] = None,
    resultado_evaluacion: Optional[str] = None,
    q: Optional[str] = None,
):
    resumen = evidencia_service.resumen_por_resultado_service()
    return JSONResponse({
        "evidencias": evidencia_service.listar_service(
            actividad_id=actividad_id,
            control_id=control_id,
            tipo=tipo,
            resultado_evaluacion=resultado_evaluacion,
            q=q,
        ),
        "resumen": {"total": sum(resumen.values()), "conteo": resumen},
    })


@router.get("/api/ci-evidencia/{evidencia_id}")
def api_obtener(evidencia_id: int):
    item = evidencia_service.obtener_service(evidencia_id)
    if not item:
        raise HTTPException(status_code=404, detail="Evidencia no encontrada.")
    return JSONResponse(item)


@router.post("/api/ci-evidencia")
async def api_crear(
    titulo: str = Form(...),
    tipo: str = Form("Documento"),
    fecha_evidencia: str = Form(""),
    control_id: str = Form(""),
    actividad_id: str = Form(""),
    resultado_evaluacion: str = Form("Por evaluar"),
    descripcion: str = Form(""),
    observaciones: str = Form(""),
    archivo: Optional[UploadFile] = File(None),
):
    meta = await save_uploaded_evidence(archivo) if archivo and archivo.filename else {}
    data = _build_evidencia_payload(
        EvidenciaCreate,
        titulo=titulo,
        tipo=tipo,
        fecha_evidencia=fecha_evidencia,
        control_id=control_id,
        actividad_id=actividad_id,
        resultado_evaluacion=resultado_evaluacion,
        descripcion=descripcion,
        observaciones=observaciones,
    )
    return JSONResponse(evidencia_service.crear_service(data, **meta), status_code=201)


@router.put("/api/ci-evidencia/{evidencia_id}")
async def api_actualizar(
    evidencia_id: int,
    titulo: str = Form(...),
    tipo: str = Form("Documento"),
    fecha_evidencia: str = Form(""),
    control_id: str = Form(""),
    actividad_id: str = Form(""),
    resultado_evaluacion: str = Form("Por evaluar"),
    descripcion: str = Form(""),
    observaciones: str = Form(""),
    archivo: Optional[UploadFile] = File(None),
):
    meta = await save_uploaded_evidence(archivo) if archivo and archivo.filename else {}
    item = evidencia_service.actualizar_service(
        evidencia_id,
        _build_evidencia_payload(
            EvidenciaUpdate,
            titulo=titulo,
            tipo=tipo,
            fecha_evidencia=fecha_evidencia,
            control_id=control_id,
            actividad_id=actividad_id,
            resultado_evaluacion=resultado_evaluacion,
            descripcion=descripcion,
            observaciones=observaciones,
        ),
        **meta,
    )
    if not item:
        raise HTTPException(status_code=404, detail="Evidencia no encontrada.")
    return JSONResponse(item)


@router.delete("/api/ci-evidencia/{evidencia_id}")
def api_eliminar(evidencia_id: int):
    if not evidencia_service.eliminar_service(evidencia_id):
        raise HTTPException(status_code=404, detail="Evidencia no encontrada.")
    return JSONResponse({"ok": True})


@router.get("/api/ci-evidencia/{evidencia_id}/descargar")
def api_descargar(evidencia_id: int):
    item = evidencia_service.obtener_service(evidencia_id)
    ruta = evidencia_service.obtener_ruta_archivo_service(evidencia_id)
    if not item or not ruta or not os.path.exists(ruta):
        raise HTTPException(status_code=404, detail="Archivo no disponible.")
    nombre = item.get("archivo_nombre_original") or item.get("archivo_nombre") or os.path.basename(ruta)
    mime = item.get("archivo_mime") or "application/octet-stream"
    return FileResponse(path=ruta, media_type=mime, filename=nombre)


__all__ = ["router"]

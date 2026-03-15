"""API de inscripciones, progreso, stats y exportacion CSV."""
from __future__ import annotations

import csv
import io
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from fastapi_modulo.modulos.capacitacion.controladores.dependencies import current_user_key, get_current_tenant
from fastapi_modulo.modulos.capacitacion.modelos.cap_inscripcion_service import (
    asignar_por_reglas,
    ejecutar_operacion_cursos,
    get_dashboard_stats,
    get_inscripcion,
    get_progreso_curso,
    inscribir_colaborador,
    inscribir_masivo,
    list_inscripciones,
    marcar_leccion_completada,
    registrar_encuesta_satisfaccion,
)
from fastapi_modulo.modulos.capacitacion.servicios.archivos_service import list_archivos, save_upload

router = APIRouter()


class InscripcionIn(BaseModel):
    colaborador_key: Optional[str] = Field(None, max_length=100)
    colaborador_nombre: Optional[str] = Field(None, max_length=200)
    departamento: Optional[str] = Field(None, max_length=150)
    rol: Optional[str] = Field(None, max_length=100)
    puesto: Optional[str] = Field(None, max_length=150)
    curso_id: int


class InscripcionMasivaIn(BaseModel):
    curso_id: int
    colaboradores: List[Dict[str, Any]]


class ProgresoIn(BaseModel):
    inscripcion_id: int
    leccion_id: int
    tiempo_seg: Optional[int] = None


class SatisfaccionIn(BaseModel):
    calificacion: int = Field(..., ge=1, le=5)
    comentario: Optional[str] = None


@router.get("/api/capacitacion/inscripciones")
def api_list_inscripciones(
    request: Request,
    curso_id: int = 0,
    colaborador_key: str = "",
    estado: str = "",
    departamento: str = "",
    fecha_desde: str = "",
    fecha_hasta: str = "",
):
    return JSONResponse(
        list_inscripciones(
            curso_id=curso_id or None,
            colaborador_key=colaborador_key or None,
            estado=estado or None,
            departamento=departamento or None,
            fecha_desde=fecha_desde or None,
            fecha_hasta=fecha_hasta or None,
        )
    )


@router.get("/api/capacitacion/mis-inscripciones")
def api_mis_inscripciones(request: Request):
    return JSONResponse(list_inscripciones(colaborador_key=current_user_key(request)))


@router.get("/api/capacitacion/inscripciones/{insc_id}")
def api_get_inscripcion(insc_id: int, request: Request):
    obj = get_inscripcion(insc_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")
    return JSONResponse(obj)


@router.post("/api/capacitacion/inscribir", status_code=201)
def api_inscribir(request: Request, body: InscripcionIn):
    data = body.model_dump()
    if not data.get("colaborador_key"):
        data["colaborador_key"] = current_user_key(request)
    obj, created = inscribir_colaborador(data)
    return JSONResponse(obj, status_code=201 if created else 200)


@router.post("/api/capacitacion/inscribir-masivo")
def api_inscribir_masivo(request: Request, body: InscripcionMasivaIn):
    return JSONResponse(inscribir_masivo(body.curso_id, body.colaboradores))


@router.post("/api/capacitacion/cursos/{curso_id}/asignar-por-reglas")
def api_asignar_por_reglas(curso_id: int):
    return JSONResponse(asignar_por_reglas(curso_id))


@router.post("/api/capacitacion/progreso")
def api_marcar_progreso(request: Request, body: ProgresoIn):
    try:
        result = marcar_leccion_completada(body.inscripcion_id, body.leccion_id, body.tiempo_seg)
        return JSONResponse(result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/capacitacion/inscripciones/{insc_id}/progreso")
def api_get_progreso(insc_id: int, request: Request):
    return JSONResponse(get_progreso_curso(insc_id))


@router.get("/api/capacitacion/stats")
def api_dashboard_stats():
    return JSONResponse(get_dashboard_stats())


@router.post("/api/capacitacion/operacion/ejecutar")
def api_operacion_ejecutar():
    return JSONResponse(ejecutar_operacion_cursos())


@router.post("/api/capacitacion/inscripciones/{insc_id}/satisfaccion")
def api_satisfaccion(insc_id: int, body: SatisfaccionIn):
    obj = registrar_encuesta_satisfaccion(insc_id, body.calificacion, body.comentario)
    if not obj:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")
    return JSONResponse(obj)


@router.post("/api/capacitacion/inscripciones/{insc_id}/evidencias", status_code=201)
async def api_subir_evidencia(insc_id: int, request: Request, archivo: UploadFile = File(...)):
    try:
        saved = save_upload(archivo, categoria="evidencia", tenant_id=get_current_tenant(request), entidad_tipo="inscripcion", entidad_id=insc_id, actor_key=current_user_key(request))
        return JSONResponse(saved, status_code=201)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/capacitacion/inscripciones/{insc_id}/evidencias")
def api_listar_evidencias(insc_id: int):
    return JSONResponse(list_archivos(entidad_tipo="inscripcion", entidad_id=insc_id, categoria="evidencia"))


@router.get("/api/capacitacion/inscripciones-csv")
def api_inscripciones_csv(
    request: Request,
    curso_id: int = 0,
    estado: str = "",
    departamento: str = "",
    fecha_desde: str = "",
    fecha_hasta: str = "",
):
    rows = list_inscripciones(
        curso_id=curso_id or None,
        estado=estado or None,
        departamento=departamento or None,
        fecha_desde=fecha_desde or None,
        fecha_hasta=fecha_hasta or None,
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id",
            "tenant_id",
            "colaborador_key",
            "colaborador_nombre",
            "departamento",
            "curso_id",
            "curso_nombre",
            "estado",
            "pct_avance",
            "puntaje_final",
            "aprobado",
            "fecha_inscripcion",
            "fecha_completado",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.get("id"),
                row.get("tenant_id"),
                row.get("colaborador_key"),
                row.get("colaborador_nombre"),
                row.get("departamento"),
                row.get("curso_id"),
                row.get("curso_nombre"),
                row.get("estado"),
                row.get("pct_avance"),
                row.get("puntaje_final"),
                row.get("aprobado"),
                row.get("fecha_inscripcion"),
                row.get("fecha_completado"),
            ]
        )
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=inscripciones.csv"},
    )


__all__ = ["router"]

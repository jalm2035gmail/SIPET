"""API de evaluaciones, preguntas e intentos."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator

from fastapi_modulo.modulos.capacitacion.controladores.dependencies import current_session_name, current_user_key, get_current_tenant, list_live_course_surveys_safe
from fastapi_modulo.modulos.capacitacion.modelos.cap_evaluacion_service import (
    create_evaluacion,
    create_pregunta,
    delete_pregunta,
    enviar_respuestas,
    get_evaluacion,
    iniciar_intento,
    list_evaluaciones,
    list_preguntas,
)
from fastapi_modulo.modulos.capacitacion.modelos.cap_presentacion_service import get_presentacion
from fastapi_modulo.modulos.capacitacion.modelos.enums import TipoPregunta
from fastapi_modulo.modulos.capacitacion.servicios.archivos_service import list_archivos, save_upload

router = APIRouter()


def _actor_meta(request: Request) -> tuple[str | None, str | None]:
    try:
        return current_user_key(request), current_session_name(request) or None
    except HTTPException:
        return None, current_session_name(request) or None


class EvalIn(BaseModel):
    titulo: str = Field(..., max_length=200)
    instrucciones: Optional[str] = None
    puntaje_minimo: float = Field(70.0, ge=0, le=100)
    max_intentos: int = Field(3, ge=1)
    preguntas_por_intento: Optional[int] = Field(None, ge=1)
    tiempo_limite_min: Optional[int] = None
    preguntas: List[Dict[str, Any]] = []


class PreguntaIn(BaseModel):
    evaluacion_id: int
    enunciado: str
    tipo: TipoPregunta = TipoPregunta.OPCION_MULTIPLE
    explicacion: Optional[str] = None
    puntaje: float = Field(1.0, ge=0)
    orden: int = 0
    opciones: List[Dict[str, Any]] = []

    @model_validator(mode="after")
    def validate_opciones(self):
        if self.tipo in {TipoPregunta.OPCION_MULTIPLE, TipoPregunta.VERDADERO_FALSO}:
            opciones_validas = [op for op in self.opciones if isinstance(op, dict) and str(op.get("texto") or "").strip()]
            if len(opciones_validas) < 2:
                raise ValueError("Las preguntas cerradas requieren al menos dos opciones válidas")
            if not any(bool(op.get("es_correcta")) for op in opciones_validas):
                raise ValueError("Las preguntas cerradas requieren al menos una opción correcta")
            if self.tipo == TipoPregunta.VERDADERO_FALSO and len(opciones_validas) != 2:
                raise ValueError("Las preguntas verdadero_falso deben tener exactamente dos opciones")
        elif self.opciones:
            raise ValueError("Las preguntas de texto libre no deben incluir opciones")
        return self


class IntentoIniciarIn(BaseModel):
    inscripcion_id: int
    evaluacion_id: int


class RespuestasIn(BaseModel):
    intento_id: int
    respuestas: Dict[str, Any]


@router.get("/api/capacitacion/cursos/{curso_id}/evaluaciones")
def api_list_evaluaciones(curso_id: int, request: Request):
    return JSONResponse(list_evaluaciones(curso_id, tenant_id=get_current_tenant(request)))


@router.get("/api/capacitacion/cursos/{curso_id}/encuestas-live")
def api_list_live_surveys(curso_id: int, request: Request):
    tenant_id = get_current_tenant(request)
    rows = list_live_course_surveys_safe(curso_id, tenant_id)
    return JSONResponse([row for row in rows if row.get("is_live")])


@router.get("/api/capacitacion/presentaciones/{pres_id}/encuestas-live")
def api_list_live_surveys_by_presentation(pres_id: int, request: Request):
    tenant_id = get_current_tenant(request)
    pres = get_presentacion(pres_id, tenant_id=tenant_id)
    if not pres:
        raise HTTPException(status_code=404, detail="Presentación no encontrada")
    curso_id = pres.get("curso_id")
    if not curso_id:
        return JSONResponse([])
    rows = list_live_course_surveys_safe(int(curso_id), tenant_id)
    return JSONResponse([row for row in rows if row.get("is_live")])


@router.get("/api/capacitacion/evaluaciones/{eval_id}")
def api_get_evaluacion(eval_id: int, request: Request):
    obj = get_evaluacion(eval_id, tenant_id=get_current_tenant(request))
    if not obj:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    return JSONResponse(obj)


@router.post("/api/capacitacion/evaluaciones", status_code=201)
def api_create_evaluacion(request: Request, body: EvalIn):
    try:
        actor_key, actor_name = _actor_meta(request)
        return JSONResponse(create_evaluacion(body.model_dump(), tenant_id=get_current_tenant(request), actor_key=actor_key, actor_name=actor_name), status_code=201)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/capacitacion/evaluaciones/{eval_id}/preguntas")
def api_list_preguntas(eval_id: int, request: Request, admin: bool = False):
    return JSONResponse(list_preguntas(eval_id, tenant_id=get_current_tenant(request), incluir_correctas=admin))


@router.post("/api/capacitacion/evaluaciones/{eval_id}/preguntas", status_code=201)
def api_create_pregunta(eval_id: int, request: Request, body: PreguntaIn):
    data = body.model_dump()
    data["evaluacion_id"] = eval_id
    try:
        actor_key, actor_name = _actor_meta(request)
        return JSONResponse(create_pregunta(data, tenant_id=get_current_tenant(request), actor_key=actor_key, actor_name=actor_name), status_code=201)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/api/capacitacion/preguntas/{pregunta_id}")
def api_delete_pregunta(pregunta_id: int, request: Request):
    actor_key, actor_name = _actor_meta(request)
    if not delete_pregunta(pregunta_id, tenant_id=get_current_tenant(request), actor_key=actor_key, actor_name=actor_name):
        raise HTTPException(status_code=404, detail="Pregunta no encontrada")
    return JSONResponse({"ok": True})


@router.post("/api/capacitacion/evaluacion/iniciar")
def api_iniciar_intento(request: Request, body: IntentoIniciarIn):
    try:
        return JSONResponse(iniciar_intento(body.inscripcion_id, body.evaluacion_id, tenant_id=get_current_tenant(request)))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/api/capacitacion/evaluacion/enviar")
def api_enviar_respuestas(request: Request, body: RespuestasIn):
    try:
        actor_key, actor_name = _actor_meta(request)
        return JSONResponse(enviar_respuestas(body.intento_id, get_current_tenant(request), body.respuestas, actor_key=actor_key, actor_name=actor_name))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/api/capacitacion/evaluaciones/{eval_id}/adjuntos", status_code=201)
async def api_upload_eval_attachment(eval_id: int, request: Request, archivo: UploadFile = File(...)):
    actor_key, _actor_name = _actor_meta(request)
    try:
        saved = save_upload(archivo, categoria="adjunto_evaluacion", tenant_id=get_current_tenant(request), entidad_tipo="evaluacion", entidad_id=eval_id, actor_key=actor_key)
        return JSONResponse(saved, status_code=201)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/capacitacion/evaluaciones/{eval_id}/adjuntos")
def api_list_eval_attachments(eval_id: int):
    return JSONResponse(list_archivos(entidad_tipo="evaluacion", entidad_id=eval_id, categoria="adjunto_evaluacion"))


__all__ = ["router"]

"""API de categorias, cursos y lecciones."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.exc import IntegrityError

from fastapi_modulo.modulos.capacitacion.controladores.dependencies import current_session_name, current_user_key, get_current_tenant
from fastapi_modulo.modulos.capacitacion.modelos.cap_service import (
    create_ruta,
    create_categoria,
    create_curso,
    create_leccion,
    delete_categoria,
    delete_curso,
    duplicate_as_new_version,
    delete_leccion,
    get_categoria,
    get_curso,
    list_categorias,
    list_cursos,
    list_lecciones,
    list_rutas,
    reordenar_lecciones,
    update_categoria,
    update_curso,
    update_leccion,
)
from fastapi_modulo.modulos.capacitacion.modelos.enums import EstadoCurso, NivelCurso, TipoLeccion
from fastapi_modulo.modulos.capacitacion.servicios.archivos_service import list_archivos, save_upload

router = APIRouter()


def _actor_meta(request: Request) -> tuple[str | None, str | None]:
    try:
        return current_user_key(request), current_session_name(request) or None
    except HTTPException:
        return None, current_session_name(request) or None


class CatIn(BaseModel):
    nombre: str = Field(..., max_length=100)
    descripcion: Optional[str] = None
    color: Optional[str] = Field(None, max_length=30)


class CursoIn(BaseModel):
    nombre: str = Field(..., max_length=200)
    descripcion: Optional[str] = None
    objetivo: Optional[str] = None
    categoria_id: Optional[int] = None
    nivel: NivelCurso = NivelCurso.BASICO
    estado: EstadoCurso = EstadoCurso.BORRADOR
    responsable: Optional[str] = Field(None, max_length=150)
    duracion_horas: Optional[float] = Field(None, ge=0)
    puntaje_aprobacion: float = Field(70.0, ge=0, le=100)
    imagen_url: Optional[str] = Field(None, max_length=400)
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    es_obligatorio: bool = False
    vence_dias: Optional[int] = Field(None, ge=1)
    recordatorio_dias: Optional[int] = Field(7, ge=1)
    reinscripcion_automatica: bool = False
    prerrequisitos: list[int] = []
    departamentos: list[str] = []
    rol_objetivo: Optional[str] = Field(None, max_length=100)
    puesto_objetivo: Optional[str] = Field(None, max_length=150)
    bloquear_certificado_encuesta: bool = False
    requiere_encuesta_satisfaccion: bool = False

    @model_validator(mode="after")
    def validate_dates(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser menor que fecha_inicio")
        return self


class LeccionIn(BaseModel):
    titulo: str = Field(..., max_length=200)
    tipo: TipoLeccion = TipoLeccion.TEXTO
    contenido: Optional[str] = None
    url_archivo: Optional[str] = Field(None, max_length=400)
    duracion_min: Optional[int] = None
    orden: int = 0
    es_obligatoria: bool = True


class ReordenarIn(BaseModel):
    orden_ids: list[int]


class RutaIn(BaseModel):
    nombre: str = Field(..., max_length=200)
    descripcion: Optional[str] = None
    rol_objetivo: Optional[str] = Field(None, max_length=100)
    puesto_objetivo: Optional[str] = Field(None, max_length=150)
    departamentos: list[str] = []
    cursos: list[dict] = []


@router.get("/api/capacitacion/categorias")
def api_list_categorias(request: Request):
    return JSONResponse(list_categorias(tenant_id=get_current_tenant(request)))


@router.get("/api/capacitacion/categorias/{cat_id}")
def api_get_categoria(cat_id: int, request: Request):
    obj = get_categoria(cat_id, tenant_id=get_current_tenant(request))
    if not obj:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return JSONResponse(obj)


@router.post("/api/capacitacion/categorias", status_code=201)
def api_create_categoria(request: Request, body: CatIn):
    try:
        actor_key, actor_name = _actor_meta(request)
        return JSONResponse(create_categoria(body.model_dump(), tenant_id=get_current_tenant(request), actor_key=actor_key, actor_name=actor_name), status_code=201)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Ya existe una categoría con ese nombre")


@router.put("/api/capacitacion/categorias/{cat_id}")
def api_update_categoria(cat_id: int, request: Request, body: CatIn):
    actor_key, actor_name = _actor_meta(request)
    obj = update_categoria(cat_id, body.model_dump(exclude_unset=True), tenant_id=get_current_tenant(request), actor_key=actor_key, actor_name=actor_name)
    if not obj:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return JSONResponse(obj)


@router.delete("/api/capacitacion/categorias/{cat_id}")
def api_delete_categoria(cat_id: int, request: Request):
    actor_key, actor_name = _actor_meta(request)
    if not delete_categoria(cat_id, tenant_id=get_current_tenant(request), actor_key=actor_key, actor_name=actor_name):
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return JSONResponse({"ok": True})


@router.get("/api/capacitacion/cursos")
def api_list_cursos(request: Request, estado: str = "", categoria_id: int = 0, nivel: str = ""):
    return JSONResponse(list_cursos(get_current_tenant(request), estado or None, categoria_id or None, nivel or None))


@router.get("/api/capacitacion/cursos/{curso_id}")
def api_get_curso(curso_id: int, request: Request, con_lecciones: bool = False):
    obj = get_curso(curso_id, tenant_id=get_current_tenant(request), with_lecciones=con_lecciones)
    if not obj:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return JSONResponse(obj)


@router.post("/api/capacitacion/cursos", status_code=201)
def api_create_curso(request: Request, body: CursoIn):
    try:
        actor_key, actor_name = _actor_meta(request)
        return JSONResponse(create_curso(body.model_dump(), tenant_id=get_current_tenant(request), actor_key=actor_key, actor_name=actor_name), status_code=201)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/api/capacitacion/cursos/{curso_id}")
def api_update_curso(curso_id: int, request: Request, body: CursoIn):
    try:
        actor_key, actor_name = _actor_meta(request)
        obj = update_curso(curso_id, body.model_dump(exclude_unset=True), tenant_id=get_current_tenant(request), actor_key=actor_key, actor_name=actor_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not obj:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return JSONResponse(obj)


@router.delete("/api/capacitacion/cursos/{curso_id}")
def api_delete_curso(curso_id: int, request: Request):
    actor_key, actor_name = _actor_meta(request)
    if not delete_curso(curso_id, tenant_id=get_current_tenant(request), actor_key=actor_key, actor_name=actor_name):
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return JSONResponse({"ok": True})


@router.post("/api/capacitacion/cursos/{curso_id}/versionar", status_code=201)
def api_versionar_curso(curso_id: int, request: Request):
    actor_key, actor_name = _actor_meta(request)
    obj = duplicate_as_new_version(curso_id, tenant_id=get_current_tenant(request), actor_key=actor_key, actor_name=actor_name)
    if not obj:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return JSONResponse(obj, status_code=201)


@router.get("/api/capacitacion/cursos/{curso_id}/lecciones")
def api_list_lecciones(curso_id: int, request: Request):
    return JSONResponse(list_lecciones(curso_id, tenant_id=get_current_tenant(request)))


@router.post("/api/capacitacion/cursos/{curso_id}/lecciones", status_code=201)
def api_create_leccion(curso_id: int, request: Request, body: LeccionIn):
    data = body.model_dump()
    data["curso_id"] = curso_id
    actor_key, actor_name = _actor_meta(request)
    return JSONResponse(create_leccion(data, tenant_id=get_current_tenant(request), actor_key=actor_key, actor_name=actor_name), status_code=201)


@router.put("/api/capacitacion/lecciones/{leccion_id}")
def api_update_leccion(leccion_id: int, request: Request, body: LeccionIn):
    actor_key, actor_name = _actor_meta(request)
    obj = update_leccion(leccion_id, body.model_dump(exclude_unset=True), tenant_id=get_current_tenant(request), actor_key=actor_key, actor_name=actor_name)
    if not obj:
        raise HTTPException(status_code=404, detail="Lección no encontrada")
    return JSONResponse(obj)


@router.delete("/api/capacitacion/lecciones/{leccion_id}")
def api_delete_leccion(leccion_id: int, request: Request):
    actor_key, actor_name = _actor_meta(request)
    if not delete_leccion(leccion_id, tenant_id=get_current_tenant(request), actor_key=actor_key, actor_name=actor_name):
        raise HTTPException(status_code=404, detail="Lección no encontrada")
    return JSONResponse({"ok": True})


@router.post("/api/capacitacion/lecciones/{leccion_id}/archivo", status_code=201)
async def api_upload_leccion_file(leccion_id: int, request: Request, archivo: UploadFile = File(...)):
    actor_key, actor_name = _actor_meta(request)
    try:
        categoria = "video" if (archivo.content_type or "").startswith("video/") else "audio" if (archivo.content_type or "").startswith("audio/") else "imagen" if (archivo.content_type or "").startswith("image/") else "documento"
        saved = save_upload(archivo, categoria=categoria, tenant_id=get_current_tenant(request), entidad_tipo="leccion", entidad_id=leccion_id, actor_key=actor_key, metadata={"actor_name": actor_name})
        update_leccion(leccion_id, {"url_archivo": saved["public_url"]}, tenant_id=get_current_tenant(request), actor_key=actor_key, actor_name=actor_name)
        return JSONResponse(saved, status_code=201)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/capacitacion/lecciones/{leccion_id}/archivos")
def api_list_leccion_files(leccion_id: int):
    return JSONResponse(list_archivos(entidad_tipo="leccion", entidad_id=leccion_id))


@router.put("/api/capacitacion/cursos/{curso_id}/lecciones/reordenar")
def api_reordenar_lecciones(curso_id: int, request: Request, body: ReordenarIn):
    actor_key, actor_name = _actor_meta(request)
    return JSONResponse(reordenar_lecciones(curso_id, body.orden_ids, tenant_id=get_current_tenant(request), actor_key=actor_key, actor_name=actor_name))


@router.get("/api/capacitacion/rutas")
def api_list_rutas():
    return JSONResponse(list_rutas())


@router.post("/api/capacitacion/rutas", status_code=201)
def api_create_ruta(request: Request, body: RutaIn):
    return JSONResponse(create_ruta(body.model_dump(), tenant_id=get_current_tenant(request)), status_code=201)


__all__ = ["router"]

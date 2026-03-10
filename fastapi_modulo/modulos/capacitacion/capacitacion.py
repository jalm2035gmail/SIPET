"""Router FastAPI — Módulo de Capacitación."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from fastapi_modulo.modulos.capacitacion.cap_service import (
    create_categoria,
    create_curso,
    create_leccion,
    delete_categoria,
    delete_curso,
    delete_leccion,
    get_categoria,
    get_curso,
    list_categorias,
    list_cursos,
    list_lecciones,
    reordenar_lecciones,
    update_categoria,
    update_curso,
    update_leccion,
)
from fastapi_modulo.modulos.capacitacion.cap_inscripcion_service import (
    get_dashboard_stats,
    get_inscripcion,
    get_progreso_curso,
    inscribir_colaborador,
    inscribir_masivo,
    list_inscripciones,
    marcar_leccion_completada,
)
from fastapi_modulo.modulos.capacitacion.cap_evaluacion_service import (
    create_evaluacion,
    create_pregunta,
    delete_pregunta,
    enviar_respuestas,
    get_certificado,
    get_certificado_por_folio,
    get_certificados_colaborador,
    get_evaluacion,
    iniciar_intento,
    list_evaluaciones,
    list_preguntas,
)
from fastapi_modulo.modulos.capacitacion.cap_gamificacion_service import (
    check_y_otorgar_insignias,
    get_insignias_disponibles,
    get_mis_insignias,
    get_perfil_gamificacion,
    get_ranking,
)
from fastapi_modulo.modulos.capacitacion.cap_presentacion_service import (
    create_diapositiva,
    create_presentacion,
    delete_diapositiva,
    delete_presentacion,
    duplicate_diapositiva,
    get_presentacion,
    list_diapositivas,
    list_elementos,
    list_presentaciones,
    reordenar_diapositivas,
    save_elementos,
    update_diapositiva,
    update_presentacion,
)

_MODULE_DIR = os.path.dirname(__file__)


# ── Control de acceso ──────────────────────────────────────────────────────────

def _require_access(request: Request) -> None:
    from fastapi_modulo.main import is_admin_or_superadmin, _get_user_app_access
    if is_admin_or_superadmin(request):
        return
    if "Capacitacion" in _get_user_app_access(request):
        return
    raise HTTPException(status_code=403, detail="Acceso restringido al módulo Capacitación")


router = APIRouter(dependencies=[Depends(_require_access)])


# ── Utilidad: clave del usuario actual ─────────────────────────────────────────

def _current_user_key(request: Request) -> str:
    """Devuelve str(user.id) del usuario en sesión."""
    from fastapi_modulo.main import _sensitive_lookup_hash
    from fastapi_modulo.db import SessionLocal
    from fastapi_modulo.main import Usuario  # type: ignore[attr-defined]

    username = (
        getattr(request.state, "user_name", None)
        or request.cookies.get("user_name")
        or ""
    ).strip()
    if not username:
        raise HTTPException(status_code=401, detail="No autenticado")
    h = _sensitive_lookup_hash(username)
    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.usuario_hash == h).first()
        if not user:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
        return str(user.id)
    finally:
        db.close()


# ── Schemas inline ─────────────────────────────────────────────────────────────

class _CatIn(BaseModel):
    nombre: str = Field(..., max_length=100)
    descripcion: Optional[str] = None
    color: Optional[str] = Field(None, max_length=30)


class _CursoIn(BaseModel):
    nombre: str = Field(..., max_length=200)
    descripcion: Optional[str] = None
    objetivo: Optional[str] = None
    categoria_id: Optional[int] = None
    nivel: str = Field("basico", pattern="^(basico|intermedio|avanzado)$")
    estado: str = Field("borrador", pattern="^(borrador|publicado|archivado)$")
    responsable: Optional[str] = Field(None, max_length=150)
    duracion_horas: Optional[float] = None
    puntaje_aprobacion: float = Field(70.0, ge=0, le=100)
    imagen_url: Optional[str] = Field(None, max_length=400)
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    es_obligatorio: bool = False


class _LeccionIn(BaseModel):
    titulo: str = Field(..., max_length=200)
    tipo: str = Field("texto", pattern="^(texto|video|documento|enlace)$")
    contenido: Optional[str] = None
    url_archivo: Optional[str] = Field(None, max_length=400)
    duracion_min: Optional[int] = None
    orden: int = 0
    es_obligatoria: bool = True


class _InscripcionIn(BaseModel):
    colaborador_key: Optional[str] = Field(None, max_length=100)
    colaborador_nombre: Optional[str] = Field(None, max_length=200)
    departamento: Optional[str] = Field(None, max_length=150)
    curso_id: int


class _InscripcionMasivaIn(BaseModel):
    curso_id: int
    colaboradores: List[Dict[str, Any]]


class _ProgresoIn(BaseModel):
    inscripcion_id: int
    leccion_id: int
    tiempo_seg: Optional[int] = None


class _EvalIn(BaseModel):
    titulo: str = Field(..., max_length=200)
    instrucciones: Optional[str] = None
    puntaje_minimo: float = Field(70.0, ge=0, le=100)
    max_intentos: int = Field(3, ge=1)
    preguntas_por_intento: Optional[int] = None
    tiempo_limite_min: Optional[int] = None
    preguntas: List[Dict[str, Any]] = []


class _PreguntaIn(BaseModel):
    evaluacion_id: int
    enunciado: str
    tipo: str = Field("opcion_multiple", pattern="^(opcion_multiple|verdadero_falso|texto_libre)$")
    explicacion: Optional[str] = None
    puntaje: float = Field(1.0, ge=0)
    orden: int = 0
    opciones: List[Dict[str, Any]] = []


class _IntentoIniciarIn(BaseModel):
    inscripcion_id: int
    evaluacion_id: int


class _RespuestasIn(BaseModel):
    intento_id: int
    respuestas: Dict[str, Any]


class _ReordenarIn(BaseModel):
    orden_ids: List[int]


# ── Páginas HTML ───────────────────────────────────────────────────────────────

@router.get("/capacitacion", response_class=HTMLResponse)
def cap_page(request: Request):
    from fastapi_modulo.main import render_backend_page
    html_path = os.path.join(_MODULE_DIR, "capacitacion.html")
    with open(html_path, encoding="utf-8") as fh:
        content = fh.read()
    return render_backend_page(
        request,
        title="Capacitación",
        description="Gestión de cursos, evaluaciones y certificados.",
        content=content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/api/capacitacion/assets/capacitacion.js")
def cap_js():
    js_path = os.path.join(_MODULE_DIR, "capacitacion.js")
    with open(js_path, encoding="utf-8") as fh:
        return Response(content=fh.read(), media_type="application/javascript")


@router.get("/capacitacion/curso/{curso_id}", response_class=HTMLResponse)
def cap_curso_page(curso_id: int, request: Request):
    from fastapi_modulo.main import render_backend_page
    html_path = os.path.join(_MODULE_DIR, "capacitacion_player.html")
    with open(html_path, encoding="utf-8") as fh:
        content = fh.read()
    return render_backend_page(
        request,
        title="Curso",
        content=content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/api/capacitacion/assets/capacitacion_player.js")
def cap_player_js():
    js_path = os.path.join(_MODULE_DIR, "capacitacion_player.js")
    with open(js_path, encoding="utf-8") as fh:
        return Response(content=fh.read(), media_type="application/javascript")


@router.get("/capacitacion/evaluacion/{eval_id}", response_class=HTMLResponse)
def cap_eval_page(eval_id: int, request: Request):
    from fastapi_modulo.main import render_backend_page
    html_path = os.path.join(_MODULE_DIR, "capacitacion_eval.html")
    with open(html_path, encoding="utf-8") as fh:
        content = fh.read()
    return render_backend_page(
        request,
        title="Evaluación",
        content=content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/api/capacitacion/assets/capacitacion_eval.js")
def cap_eval_js():
    js_path = os.path.join(_MODULE_DIR, "capacitacion_eval.js")
    with open(js_path, encoding="utf-8") as fh:
        return Response(content=fh.read(), media_type="application/javascript")


# ── API: Categorías ────────────────────────────────────────────────────────────

@router.get("/api/capacitacion/categorias")
def api_list_categorias():
    return JSONResponse(list_categorias())


@router.get("/api/capacitacion/categorias/{cat_id}")
def api_get_categoria(cat_id: int):
    obj = get_categoria(cat_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return JSONResponse(obj)


@router.post("/api/capacitacion/categorias", status_code=201)
def api_create_categoria(body: _CatIn):
    try:
        return JSONResponse(create_categoria(body.model_dump()), status_code=201)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Ya existe una categoría con ese nombre")


@router.put("/api/capacitacion/categorias/{cat_id}")
def api_update_categoria(cat_id: int, body: _CatIn):
    obj = update_categoria(cat_id, body.model_dump(exclude_unset=True))
    if not obj:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return JSONResponse(obj)


@router.delete("/api/capacitacion/categorias/{cat_id}")
def api_delete_categoria(cat_id: int):
    if not delete_categoria(cat_id):
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return JSONResponse({"ok": True})


# ── API: Cursos ────────────────────────────────────────────────────────────────

@router.get("/api/capacitacion/cursos")
def api_list_cursos(estado: str = "", categoria_id: int = 0, nivel: str = ""):
    return JSONResponse(
        list_cursos(estado or None, categoria_id or None, nivel or None)
    )


@router.get("/api/capacitacion/cursos/{curso_id}")
def api_get_curso(curso_id: int, con_lecciones: bool = False):
    obj = get_curso(curso_id, with_lecciones=con_lecciones)
    if not obj:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return JSONResponse(obj)


@router.post("/api/capacitacion/cursos", status_code=201)
def api_create_curso(body: _CursoIn):
    return JSONResponse(create_curso(body.model_dump()), status_code=201)


@router.put("/api/capacitacion/cursos/{curso_id}")
def api_update_curso(curso_id: int, body: _CursoIn):
    obj = update_curso(curso_id, body.model_dump(exclude_unset=True))
    if not obj:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return JSONResponse(obj)


@router.delete("/api/capacitacion/cursos/{curso_id}")
def api_delete_curso(curso_id: int):
    if not delete_curso(curso_id):
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return JSONResponse({"ok": True})


# ── API: Lecciones ─────────────────────────────────────────────────────────────

@router.get("/api/capacitacion/cursos/{curso_id}/lecciones")
def api_list_lecciones(curso_id: int):
    return JSONResponse(list_lecciones(curso_id))


@router.post("/api/capacitacion/cursos/{curso_id}/lecciones", status_code=201)
def api_create_leccion(curso_id: int, body: _LeccionIn):
    data = body.model_dump()
    data["curso_id"] = curso_id
    return JSONResponse(create_leccion(data), status_code=201)


@router.put("/api/capacitacion/lecciones/{leccion_id}")
def api_update_leccion(leccion_id: int, body: _LeccionIn):
    obj = update_leccion(leccion_id, body.model_dump(exclude_unset=True))
    if not obj:
        raise HTTPException(status_code=404, detail="Lección no encontrada")
    return JSONResponse(obj)


@router.delete("/api/capacitacion/lecciones/{leccion_id}")
def api_delete_leccion(leccion_id: int):
    if not delete_leccion(leccion_id):
        raise HTTPException(status_code=404, detail="Lección no encontrada")
    return JSONResponse({"ok": True})


@router.put("/api/capacitacion/cursos/{curso_id}/lecciones/reordenar")
def api_reordenar_lecciones(curso_id: int, body: _ReordenarIn):
    return JSONResponse(reordenar_lecciones(curso_id, body.orden_ids))


# ── API: Inscripciones ─────────────────────────────────────────────────────────

@router.get("/api/capacitacion/inscripciones")
def api_list_inscripciones(
    curso_id: int = 0,
    colaborador_key: str = "",
    estado: str = "",
    departamento: str = "",
    fecha_desde: str = "",
    fecha_hasta: str = "",
):
    return JSONResponse(
        list_inscripciones(
            curso_id or None,
            colaborador_key or None,
            estado or None,
            departamento or None,
            fecha_desde or None,
            fecha_hasta or None,
        )
    )


@router.get("/api/capacitacion/mis-inscripciones")
def api_mis_inscripciones(request: Request):
    key = _current_user_key(request)
    return JSONResponse(list_inscripciones(colaborador_key=key))


@router.get("/api/capacitacion/inscripciones/{insc_id}")
def api_get_inscripcion(insc_id: int):
    obj = get_inscripcion(insc_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")
    return JSONResponse(obj)


@router.post("/api/capacitacion/inscribir", status_code=201)
def api_inscribir(request: Request, body: _InscripcionIn):
    data = body.model_dump()
    if not data.get("colaborador_key"):
        data["colaborador_key"] = _current_user_key(request)
    obj, created = inscribir_colaborador(data)
    return JSONResponse(obj, status_code=201 if created else 200)


@router.post("/api/capacitacion/inscribir-masivo")
def api_inscribir_masivo(body: _InscripcionMasivaIn):
    return JSONResponse(inscribir_masivo(body.curso_id, body.colaboradores))


# ── API: Progreso ──────────────────────────────────────────────────────────────

@router.post("/api/capacitacion/progreso")
def api_marcar_progreso(body: _ProgresoIn):
    result = marcar_leccion_completada(
        body.inscripcion_id, body.leccion_id, body.tiempo_seg
    )
    if not result:
        raise HTTPException(status_code=404, detail="Inscripción o lección no encontrada")
    return JSONResponse(result)


@router.get("/api/capacitacion/inscripciones/{insc_id}/progreso")
def api_get_progreso(insc_id: int):
    return JSONResponse(get_progreso_curso(insc_id))


@router.get("/api/capacitacion/stats")
def api_dashboard_stats():
    return JSONResponse(get_dashboard_stats())


@router.get("/api/capacitacion/inscripciones-csv")
def api_inscripciones_csv(
    curso_id: int = 0,
    estado: str = "",
    departamento: str = "",
    fecha_desde: str = "",
    fecha_hasta: str = "",
):
    import csv, io
    rows = list_inscripciones(
        curso_id or None, None, estado or None,
        departamento or None, fecha_desde or None, fecha_hasta or None,
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "id", "colaborador_key", "colaborador_nombre", "departamento",
        "curso_id", "curso_nombre", "estado", "pct_avance",
        "puntaje_final", "aprobado", "fecha_inscripcion", "fecha_completado",
    ])
    for r in rows:
        writer.writerow([
            r.get("id"), r.get("colaborador_key"), r.get("colaborador_nombre"),
            r.get("departamento"), r.get("curso_id"), r.get("curso_nombre"),
            r.get("estado"), r.get("pct_avance"), r.get("puntaje_final"),
            r.get("aprobado"), r.get("fecha_inscripcion"), r.get("fecha_completado"),
        ])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=inscripciones.csv"},
    )


# ── API: Evaluaciones ──────────────────────────────────────────────────────────

@router.get("/api/capacitacion/cursos/{curso_id}/evaluaciones")
def api_list_evaluaciones(curso_id: int):
    return JSONResponse(list_evaluaciones(curso_id))


@router.get("/api/capacitacion/evaluaciones/{eval_id}")
def api_get_evaluacion(eval_id: int):
    obj = get_evaluacion(eval_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    return JSONResponse(obj)


@router.post("/api/capacitacion/evaluaciones", status_code=201)
def api_create_evaluacion(body: _EvalIn):
    return JSONResponse(create_evaluacion(body.model_dump()), status_code=201)


@router.get("/api/capacitacion/evaluaciones/{eval_id}/preguntas")
def api_list_preguntas(eval_id: int, admin: bool = False):
    return JSONResponse(list_preguntas(eval_id, incluir_correctas=admin))


@router.post("/api/capacitacion/evaluaciones/{eval_id}/preguntas", status_code=201)
def api_create_pregunta(eval_id: int, body: _PreguntaIn):
    data = body.model_dump()
    data["evaluacion_id"] = eval_id
    return JSONResponse(create_pregunta(data), status_code=201)


@router.delete("/api/capacitacion/preguntas/{pregunta_id}")
def api_delete_pregunta(pregunta_id: int):
    if not delete_pregunta(pregunta_id):
        raise HTTPException(status_code=404, detail="Pregunta no encontrada")
    return JSONResponse({"ok": True})


# ── API: Intentos ──────────────────────────────────────────────────────────────

@router.post("/api/capacitacion/evaluacion/iniciar")
def api_iniciar_intento(body: _IntentoIniciarIn):
    try:
        return JSONResponse(iniciar_intento(body.inscripcion_id, body.evaluacion_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/api/capacitacion/evaluacion/enviar")
def api_enviar_respuestas(body: _RespuestasIn):
    try:
        return JSONResponse(enviar_respuestas(body.intento_id, body.respuestas))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── API: Certificados ──────────────────────────────────────────────────────────

@router.get("/api/capacitacion/certificados/{cert_id}")
def api_get_certificado(cert_id: int):
    obj = get_certificado(cert_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Certificado no encontrado")
    return JSONResponse(obj)


@router.get("/api/capacitacion/verificar/{folio}")
def api_verificar_certificado(folio: str):
    obj = get_certificado_por_folio(folio)
    if not obj:
        raise HTTPException(status_code=404, detail="Certificado no encontrado")
    return JSONResponse(obj)


@router.get("/api/capacitacion/mis-certificados")
def api_mis_certificados(request: Request):
    key = _current_user_key(request)
    return JSONResponse(get_certificados_colaborador(key))


# ── Páginas HTML — Certificados ────────────────────────────────────────────────

@router.get("/capacitacion/mis-certificados", response_class=HTMLResponse)
def cap_mis_certificados_page(request: Request):
    from fastapi_modulo.main import render_backend_page
    html_path = os.path.join(_MODULE_DIR, "capacitacion_certificados.html")
    with open(html_path, encoding="utf-8") as fh:
        content = fh.read()
    return render_backend_page(
        request,
        title="Mis Certificados",
        content=content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/api/capacitacion/assets/capacitacion_certificados.js")
def cap_certificados_js():
    js_path = os.path.join(_MODULE_DIR, "capacitacion_certificados.js")
    with open(js_path, encoding="utf-8") as fh:
        return Response(content=fh.read(), media_type="application/javascript")


@router.get("/capacitacion/certificado/{cert_id}", response_class=HTMLResponse)
def cap_cert_view_page(cert_id: int, request: Request):
    from fastapi_modulo.main import render_backend_page
    html_path = os.path.join(_MODULE_DIR, "capacitacion_cert_view.html")
    with open(html_path, encoding="utf-8") as fh:
        content = fh.read()
    return render_backend_page(
        request,
        title="Certificado",
        content=content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/capacitacion/verificar/{folio}", response_class=HTMLResponse)
def cap_verificar_page(folio: str, request: Request):
    from fastapi_modulo.main import render_backend_page
    html_path = os.path.join(_MODULE_DIR, "capacitacion_verificar.html")
    with open(html_path, encoding="utf-8") as fh:
        content = fh.read()
    return render_backend_page(
        request,
        title="Verificar Certificado",
        content=content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/api/capacitacion/assets/capacitacion_verificar.js")
def cap_verificar_js():
    js_path = os.path.join(_MODULE_DIR, "capacitacion_verificar.js")
    with open(js_path, encoding="utf-8") as fh:
        return Response(content=fh.read(), media_type="application/javascript")


@router.get("/capacitacion/dashboard", response_class=HTMLResponse)
def cap_dashboard_page(request: Request):
    from fastapi_modulo.main import render_backend_page, is_admin_or_superadmin
    if not is_admin_or_superadmin(request):
        raise HTTPException(status_code=403, detail="Solo administradores pueden acceder al dashboard")
    html_path = os.path.join(_MODULE_DIR, "capacitacion_dashboard.html")
    with open(html_path, encoding="utf-8") as fh:
        content = fh.read()
    return render_backend_page(
        request,
        title="Dashboard Capacitación",
        description="Indicadores de cobertura, progreso y desempeño organizacional.",
        content=content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/api/capacitacion/assets/capacitacion_dashboard.js")
def cap_dashboard_js():
    js_path = os.path.join(_MODULE_DIR, "capacitacion_dashboard.js")
    with open(js_path, encoding="utf-8") as fh:
        return Response(content=fh.read(), media_type="application/javascript")


@router.get("/capacitacion/mi-progreso", response_class=HTMLResponse)
def cap_progreso_page(request: Request):
    from fastapi_modulo.main import render_backend_page
    html_path = os.path.join(_MODULE_DIR, "capacitacion_progreso.html")
    with open(html_path, encoding="utf-8") as fh:
        content = fh.read()
    return render_backend_page(
        request,
        title="Mi Progreso — Capacitación",
        description="Tus cursos, avances y certificados obtenidos.",
        content=content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/api/capacitacion/assets/capacitacion_progreso.js")
def cap_progreso_js():
    js_path = os.path.join(_MODULE_DIR, "capacitacion_progreso.js")
    with open(js_path, encoding="utf-8") as fh:
        return Response(content=fh.read(), media_type="application/javascript")


# ── Gamificación — API ─────────────────────────────────────────────────────────

@router.get("/api/capacitacion/gamificacion/perfil")
def api_gam_perfil(request: Request):
    colab_key = _current_user_key(request)
    return JSONResponse(get_perfil_gamificacion(colab_key))


@router.get("/api/capacitacion/gamificacion/ranking")
def api_gam_ranking(limit: int = 10):
    return JSONResponse(get_ranking(min(limit, 50)))


@router.get("/api/capacitacion/gamificacion/insignias")
def api_gam_insignias():
    return JSONResponse(get_insignias_disponibles())


@router.get("/api/capacitacion/gamificacion/mis-insignias")
def api_gam_mis_insignias(request: Request):
    colab_key = _current_user_key(request)
    return JSONResponse(get_mis_insignias(colab_key))


# ── Gamificación — Página ──────────────────────────────────────────────────────

@router.get("/capacitacion/gamificacion", response_class=HTMLResponse)
def cap_gamificacion_page(request: Request):
    from fastapi_modulo.main import render_backend_page
    html_path = os.path.join(_MODULE_DIR, "capacitacion_gamificacion.html")
    with open(html_path, encoding="utf-8") as fh:
        content = fh.read()
    return render_backend_page(
        request,
        title="Gamificación — Capacitación",
        description="Puntos, insignias y ranking de aprendizaje.",
        content=content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/api/capacitacion/assets/capacitacion_gamificacion.js")
def cap_gamificacion_js():
    js_path = os.path.join(_MODULE_DIR, "capacitacion_gamificacion.js")
    with open(js_path, encoding="utf-8") as fh:
        return Response(content=fh.read(), media_type="application/javascript")


# ── Presentaciones — API ──────────────────────────────────────────────────────

@router.get("/api/capacitacion/presentaciones")
def api_pres_list(request: Request, estado: str = None, curso_id: int = None):
    autor_key = _current_user_key(request)
    return JSONResponse(list_presentaciones(autor_key=autor_key, estado=estado, curso_id=curso_id))


@router.post("/api/capacitacion/presentaciones")
async def api_pres_create(request: Request):
    data = await request.json()
    autor_key = _current_user_key(request)
    data["autor_key"] = autor_key
    pres = create_presentacion(data)
    return JSONResponse(pres, status_code=201)


@router.get("/api/capacitacion/presentaciones/{pres_id}")
def api_pres_get(pres_id: int):
    pres = get_presentacion(pres_id)
    if not pres:
        return JSONResponse({"error": "No encontrado"}, status_code=404)
    return JSONResponse(pres)


@router.put("/api/capacitacion/presentaciones/{pres_id}")
async def api_pres_update(pres_id: int, request: Request):
    data = await request.json()
    pres = update_presentacion(pres_id, data)
    if not pres:
        return JSONResponse({"error": "No encontrado"}, status_code=404)
    return JSONResponse(pres)


@router.delete("/api/capacitacion/presentaciones/{pres_id}")
def api_pres_delete(pres_id: int):
    delete_presentacion(pres_id)
    return JSONResponse({"ok": True})


@router.get("/api/capacitacion/presentaciones/{pres_id}/diapositivas")
def api_diap_list(pres_id: int):
    return JSONResponse(list_diapositivas(pres_id))


@router.post("/api/capacitacion/presentaciones/{pres_id}/diapositivas")
async def api_diap_create(pres_id: int, request: Request):
    data = await request.json()
    diap = create_diapositiva(pres_id, data)
    return JSONResponse(diap, status_code=201)


@router.put("/api/capacitacion/presentaciones/{pres_id}/reordenar")
async def api_pres_reordenar(pres_id: int, request: Request):
    data = await request.json()
    orden_ids = data.get("orden_ids", [])
    reordenar_diapositivas(pres_id, orden_ids)
    return JSONResponse({"ok": True})


@router.put("/api/capacitacion/diapositivas/{diap_id}")
async def api_diap_update(diap_id: int, request: Request):
    data = await request.json()
    diap = update_diapositiva(diap_id, data)
    if not diap:
        return JSONResponse({"error": "No encontrado"}, status_code=404)
    return JSONResponse(diap)


@router.delete("/api/capacitacion/diapositivas/{diap_id}")
def api_diap_delete(diap_id: int):
    delete_diapositiva(diap_id)
    return JSONResponse({"ok": True})


@router.post("/api/capacitacion/diapositivas/{diap_id}/duplicar")
def api_diap_duplicar(diap_id: int):
    diap = duplicate_diapositiva(diap_id)
    if not diap:
        return JSONResponse({"error": "No encontrado"}, status_code=404)
    return JSONResponse(diap, status_code=201)


@router.get("/api/capacitacion/diapositivas/{diap_id}/elementos")
def api_el_list(diap_id: int):
    return JSONResponse(list_elementos(diap_id))


@router.put("/api/capacitacion/diapositivas/{diap_id}/elementos")
async def api_el_save(diap_id: int, request: Request):
    data = await request.json()
    elementos = data.get("elementos", [])
    save_elementos(diap_id, elementos)
    return JSONResponse({"ok": True})


# ── Presentaciones — Páginas ──────────────────────────────────────────────────

@router.get("/capacitacion/presentaciones", response_class=HTMLResponse)
def cap_presentaciones_page(request: Request):
    from fastapi_modulo.main import render_backend_page
    html_path = os.path.join(_MODULE_DIR, "capacitacion_presentaciones.html")
    with open(html_path, encoding="utf-8") as fh:
        content = fh.read()
    return render_backend_page(
        request,
        title="Presentaciones — Capacitación",
        description="Crea y gestiona presentaciones interactivas.",
        content=content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/capacitacion/presentacion/{pres_id}/editor", response_class=HTMLResponse)
def cap_editor_page(pres_id: int, request: Request):
    from fastapi_modulo.main import render_backend_page
    html_path = os.path.join(_MODULE_DIR, "capacitacion_editor.html")
    with open(html_path, encoding="utf-8") as fh:
        content = fh.read().replace("__PRES_ID__", str(pres_id))
    return render_backend_page(
        request,
        title="Editor de Presentación",
        description="Edita tu presentación interactiva.",
        content=content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/capacitacion/presentacion/{pres_id}/ver", response_class=HTMLResponse)
def cap_visor_page(pres_id: int, request: Request):
    from fastapi_modulo.main import render_backend_page
    html_path = os.path.join(_MODULE_DIR, "capacitacion_visor.html")
    with open(html_path, encoding="utf-8") as fh:
        content = fh.read().replace("__PRES_ID__", str(pres_id))
    return render_backend_page(
        request,
        title="Ver Presentación",
        description="Visualiza la presentación interactiva.",
        content=content,
        hide_floating_actions=True,
        show_page_header=False,
    )


# ── Presentaciones — Assets JS ────────────────────────────────────────────────

@router.get("/api/capacitacion/assets/capacitacion_presentaciones.js")
def cap_presentaciones_js():
    js_path = os.path.join(_MODULE_DIR, "capacitacion_presentaciones.js")
    with open(js_path, encoding="utf-8") as fh:
        return Response(content=fh.read(), media_type="application/javascript")


@router.get("/api/capacitacion/assets/capacitacion_editor.js")
def cap_editor_js():
    js_path = os.path.join(_MODULE_DIR, "capacitacion_editor.js")
    with open(js_path, encoding="utf-8") as fh:
        return Response(content=fh.read(), media_type="application/javascript")


@router.get("/api/capacitacion/assets/capacitacion_visor.js")
def cap_visor_js():
    js_path = os.path.join(_MODULE_DIR, "capacitacion_visor.js")
    with open(js_path, encoding="utf-8") as fh:
        return Response(content=fh.read(), media_type="application/javascript")

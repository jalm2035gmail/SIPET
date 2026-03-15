from __future__ import annotations

import os
import sys
import tempfile
import types
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


os.environ.setdefault("APP_ENV", "test")

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DB_FILE = Path(tempfile.gettempdir()) / "capacitacion_module_tests.sqlite3"
ENGINE = create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False}, future=True)
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, future=True)

fake_db = types.ModuleType("fastapi_modulo.db")
fake_db.engine = ENGINE
fake_db.SessionLocal = SessionLocal
fake_db.MAIN = declarative_base()
sys.modules["fastapi_modulo.db"] = fake_db

from fastapi_modulo.modulos.capacitacion.controladores.api_evaluaciones import PreguntaIn  # noqa: E402
from fastapi_modulo.modulos.capacitacion.controladores.capacitacion import router as module_router  # noqa: E402
from fastapi_modulo.modulos.capacitacion.controladores.pages import router as pages_router  # noqa: E402
from fastapi_modulo.modulos.capacitacion.modelos.cap_db_models import MAIN  # noqa: E402
from fastapi_modulo.modulos.capacitacion.servicios.audit_service import list_eventos  # noqa: E402
from fastapi_modulo.modulos.capacitacion.servicios import certificados_service  # noqa: E402
from fastapi_modulo.modulos.capacitacion.servicios import cursos_service  # noqa: E402
from fastapi_modulo.modulos.capacitacion.servicios import evaluaciones_service  # noqa: E402
from fastapi_modulo.modulos.capacitacion.servicios import gamificacion_service  # noqa: E402
from fastapi_modulo.modulos.capacitacion.servicios import presentaciones_service  # noqa: E402
from fastapi_modulo.modulos.capacitacion.servicios import progreso_service  # noqa: E402


def setup_function() -> None:
    MAIN.metadata.drop_all(bind=ENGINE)
    MAIN.metadata.create_all(bind=ENGINE)


def _build_client() -> TestClient:
    app = FastAPI()

    @app.middleware("http")
    async def inject_context(request: Request, call_next):
        request.state.user_name = "capacitacion.test"
        request.state.user_role = "administrador"
        request.state.tenant_id = "default"
        return await call_next(request)

    app.include_router(module_router)
    return TestClient(app)


def _create_course_graph():
    categoria = cursos_service.create_categoria(
        {"nombre": "Liderazgo", "descripcion": "Ruta de liderazgo", "color": "#123456"}
    )
    curso = cursos_service.create_curso(
        {
            "nombre": "Curso Demo",
            "descripcion": "Curso de prueba",
            "categoria_id": categoria["id"],
            "estado": "publicado",
            "puntaje_aprobacion": 70,
        }
    )
    leccion_1 = cursos_service.create_leccion(
        {"curso_id": curso["id"], "titulo": "Lección 1", "tipo": "texto", "orden": 0, "es_obligatoria": True}
    )
    leccion_2 = cursos_service.create_leccion(
        {"curso_id": curso["id"], "titulo": "Lección 2", "tipo": "texto", "orden": 1, "es_obligatoria": True}
    )
    return categoria, curso, leccion_1, leccion_2


def test_categoria_curso_y_lecciones_crud():
    categoria, curso, leccion_1, leccion_2 = _create_course_graph()

    categoria_actualizada = cursos_service.update_categoria(
        categoria["id"], {"nombre": "Liderazgo actualizado", "descripcion": "Ruta editada"}
    )
    assert categoria_actualizada["nombre"] == "Liderazgo actualizado"

    curso_actualizado = cursos_service.update_curso(curso["id"], {"nombre": "Curso Demo Editado"})
    assert curso_actualizado["nombre"] == "Curso Demo Editado"
    assert curso_actualizado["creado_por"] is None

    leccion_actualizada = cursos_service.update_leccion(leccion_1["id"], {"titulo": "Lección Inicial"})
    assert leccion_actualizada["titulo"] == "Lección Inicial"

    reordenadas = cursos_service.reordenar_lecciones(curso["id"], [leccion_2["id"], leccion_1["id"]])
    assert [item["id"] for item in reordenadas] == [leccion_2["id"], leccion_1["id"]]
    assert [item["orden"] for item in reordenadas] == [0, 1]

    assert cursos_service.delete_leccion(leccion_2["id"]) is True
    assert cursos_service.delete_curso(curso["id"]) is True
    assert cursos_service.delete_categoria(categoria["id"]) is True


def test_inscripcion_duplicada_y_progreso_no_supera_cien():
    _, curso, leccion_1, leccion_2 = _create_course_graph()

    inscripcion_1, created_1 = progreso_service.inscribir_colaborador(
        {"colaborador_key": "colab-1", "colaborador_nombre": "Colaborador Uno", "curso_id": curso["id"]}
    )
    inscripcion_2, created_2 = progreso_service.inscribir_colaborador(
        {"colaborador_key": "colab-1", "colaborador_nombre": "Colaborador Uno", "curso_id": curso["id"]}
    )

    assert created_1 is True
    assert created_2 is False
    assert inscripcion_1["id"] == inscripcion_2["id"]

    progreso_service.marcar_leccion_completada(inscripcion_1["id"], leccion_1["id"], 120)
    progreso_service.marcar_leccion_completada(inscripcion_1["id"], leccion_1["id"], 30)
    estado_parcial = progreso_service.get_inscripcion(inscripcion_1["id"])
    assert estado_parcial["pct_avance"] == 50.0
    assert estado_parcial["estado"] == "en_progreso"

    progreso_service.marcar_leccion_completada(inscripcion_1["id"], leccion_2["id"], 60)
    estado_final = progreso_service.get_inscripcion(inscripcion_1["id"])
    assert estado_final["pct_avance"] == 100.0
    assert estado_final["pct_avance"] <= 100.0


def test_evaluacion_y_certificado_solo_al_aprobar():
    _, curso, leccion_1, leccion_2 = _create_course_graph()
    inscripcion, _ = progreso_service.inscribir_colaborador(
        {"colaborador_key": "colab-2", "colaborador_nombre": "Colaborador Dos", "curso_id": curso["id"]}
    )

    progreso_service.marcar_leccion_completada(inscripcion["id"], leccion_1["id"])
    progreso_service.marcar_leccion_completada(inscripcion["id"], leccion_2["id"])

    evaluacion = evaluaciones_service.create_evaluacion(
        {
            "curso_id": curso["id"],
            "titulo": "Evaluación final",
            "puntaje_minimo": 70,
            "max_intentos": 2,
        },
        actor_key="admin-1",
        actor_name="Administrador",
    )
    pregunta = evaluaciones_service.create_pregunta(
        {
            "evaluacion_id": evaluacion["id"],
            "enunciado": "¿Cuál es la respuesta correcta?",
            "tipo": "opcion_multiple",
            "puntaje": 10,
            "opciones": [
                {"texto": "Correcta", "es_correcta": True, "orden": 0},
                {"texto": "Incorrecta", "es_correcta": False, "orden": 1},
            ],
        },
        actor_key="admin-1",
        actor_name="Administrador",
    )

    intento_fallido = evaluaciones_service.iniciar_intento(inscripcion["id"], evaluacion["id"])
    respuesta_fallida = evaluaciones_service.enviar_respuestas(
        intento_fallido["intento_id"], None, {str(pregunta["id"]): pregunta["opciones"][1]["id"]}
    )
    assert respuesta_fallida["aprobado"] is False
    assert respuesta_fallida["certificado"] is None

    intento_exitoso = evaluaciones_service.iniciar_intento(inscripcion["id"], evaluacion["id"])
    respuesta_exitosa = evaluaciones_service.enviar_respuestas(
        intento_exitoso["intento_id"], None, {str(pregunta["id"]): pregunta["opciones"][0]["id"]}, actor_key="admin-1", actor_name="Administrador"
    )
    assert respuesta_exitosa["aprobado"] is True
    assert respuesta_exitosa["certificado"] is not None
    assert respuesta_exitosa["certificado"]["curso_id"] == curso["id"]
    assert respuesta_exitosa["certificado"]["creado_por"] == "admin-1"

    eventos_eval = list_eventos("evaluacion", evaluacion["id"])
    assert [item["accion"] for item in eventos_eval[:2]] == ["question_created", "created"]


def test_trazabilidad_en_presentacion_y_curso():
    curso = cursos_service.create_curso(
        {"nombre": "Curso auditado", "descripcion": "Con auditoría", "estado": "borrador"},
        actor_key="user-creator",
        actor_name="Creador",
    )
    assert curso["creado_por"] == "user-creator"

    publicado = cursos_service.update_curso(
        curso["id"],
        {"estado": "publicado"},
        actor_key="user-publisher",
        actor_name="Publicador",
    )
    assert publicado["publicado_por"] == "user-publisher"
    assert publicado["publicado_en"] is not None

    presentacion = presentaciones_service.create_presentacion(
        {"titulo": "Presentación auditada", "autor_key": "autor-1"},
        actor_key="autor-1",
        actor_name="Autor",
    )
    presentacion_actualizada = presentaciones_service.update_presentacion(
        presentacion["id"],
        {"titulo": "Presentación editada"},
        actor_key="editor-1",
        actor_name="Editor",
    )
    assert presentacion_actualizada["actualizado_por"] == "editor-1"

    eventos_presentacion = list_eventos("presentacion", presentacion["id"])
    assert {item["accion"] for item in eventos_presentacion} >= {"created", "updated"}


def test_emitir_certificado_exige_aprobacion_y_curso_completo():
    db = SessionLocal()
    try:
        _, curso, _, _ = _create_course_graph()
        inscripcion_obj, _ = progreso_service.inscribir_colaborador(
            {"colaborador_key": "colab-3", "colaborador_nombre": "Colaborador Tres", "curso_id": curso["id"]}
        )
        from fastapi_modulo.modulos.capacitacion.repositorios.evaluaciones_repository import get_inscripcion

        insc = get_inscripcion(db, inscripcion_obj["id"])
        assert insc is not None
        with pytest.raises(ValueError, match="aprobada"):
            certificados_service.emitir_certificado(db, insc, 80)

        insc.aprobado = True
        insc.pct_avance = 80
        with pytest.raises(ValueError, match="100%"):
            certificados_service.emitir_certificado(db, insc, 80)
    finally:
        db.close()


def test_pregunta_cerrada_requiere_respuesta_correcta():
    with pytest.raises(ValidationError):
        PreguntaIn(
            evaluacion_id=1,
            enunciado="Pregunta inválida",
            tipo="opcion_multiple",
            opciones=[
                {"texto": "A", "es_correcta": False},
                {"texto": "B", "es_correcta": False},
            ],
        )


def test_presentaciones_diapositivas_y_elementos():
    templates = presentaciones_service.get_templates()
    assert templates
    presentacion = presentaciones_service.create_presentacion({"titulo": "Presentación Demo", "autor_key": "autor-1", "template_key": templates[0]["key"]})
    diapositivas_iniciales = presentaciones_service.list_diapositivas(presentacion["id"])
    assert len(diapositivas_iniciales) >= 1

    slide_1 = diapositivas_iniciales[0]
    slide_2 = presentaciones_service.create_diapositiva(presentacion["id"], {"titulo": "Segunda"})
    asset = presentaciones_service.create_asset({"nombre": "Logo", "tipo": "imagen", "url": "https://example.com/logo.png"}, pres_id=presentacion["id"])
    elementos = presentaciones_service.save_elementos(
        slide_1["id"],
        [
            {
                "tipo": "texto",
                "contenido_json": {"texto": "Hola"},
                "asset_id": asset["id"],
                "animation_json": {"preset": "fade-in"},
                "pos_x": 10,
                "pos_y": 15,
                "width": 50,
                "height": 20,
                "z_index": 2,
            }
        ],
    )
    assert len(elementos) == 1
    assert elementos[0]["contenido_json"]["texto"] == "Hola"
    assert elementos[0]["asset_id"] == asset["id"]

    versiones = presentaciones_service.list_versiones(presentacion["id"])
    assert versiones
    manual = presentaciones_service.create_version_snapshot(presentacion["id"], actor_key="autor-1")
    assert manual is not None

    duplicado_elemento = presentaciones_service.duplicate_elemento(slide_1["id"], elementos[0]["id"], actor_key="autor-1")
    assert duplicado_elemento is not None
    assert duplicado_elemento["id"] != elementos[0]["id"]

    copia = presentaciones_service.duplicate_diapositiva(slide_1["id"])
    assert copia is not None
    assert copia["titulo"].endswith("(copia)")
    assert len(copia["elementos"]) >= 1

    presentaciones_service.reordenar_diapositivas(presentacion["id"], [slide_2["id"], copia["id"], slide_1["id"]])
    diapositivas_reordenadas = presentaciones_service.list_diapositivas(presentacion["id"])
    assert [item["id"] for item in diapositivas_reordenadas[:3]] == [slide_2["id"], copia["id"], slide_1["id"]]


def test_no_guarda_elementos_si_la_diapositiva_no_existe():
    with pytest.raises(ValueError, match="no existe"):
        presentaciones_service.save_elementos(
            99999,
            [{"tipo": "texto", "contenido_json": {"texto": "Inválido"}}],
        )


def test_editor_y_visor_cargan_hooks_principales():
    client = _build_client()

    editor = client.get("/capacitacion/presentacion/7/editor")
    assert editor.status_code == 200
    assert 'id="ped-root"' in editor.text
    assert 'data-pres-id="7"' in editor.text
    assert "/capacitacion/assets/js/capacitacion_editor.js" in editor.text

    visor = client.get("/capacitacion/presentacion/7/ver")
    assert visor.status_code == 200
    assert 'id="visor-root"' in visor.text
    assert 'data-pres-id="7"' in visor.text
    assert "/capacitacion/assets/js/capacitacion_visor.js" in visor.text


def test_api_expone_auditoria_por_entidad():
    curso = cursos_service.create_curso(
        {"nombre": "Curso visible", "descripcion": "Con eventos", "estado": "publicado"},
        actor_key="api-user",
        actor_name="API User",
    )
    client = _build_client()
    response = client.get(f"/api/capacitacion/auditoria/curso/{curso['id']}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["entidad_tipo"] == "curso"
    assert payload["entidad_id"] == curso["id"]
    assert payload["total"] >= 2
    assert {item["accion"] for item in payload["items"]} >= {"created", "published"}


def test_gamificacion_calcula_racha_retos_y_ranking_por_departamento():
    _, curso, leccion_1, leccion_2 = _create_course_graph()
    inscripcion, _ = progreso_service.inscribir_colaborador(
        {
            "colaborador_key": "colab-gam",
            "colaborador_nombre": "Colaborador Gam",
            "departamento": "Ventas",
            "curso_id": curso["id"],
        }
    )

    progreso_service.marcar_leccion_completada(inscripcion["id"], leccion_1["id"])
    progreso_service.marcar_leccion_completada(inscripcion["id"], leccion_2["id"])

    evaluacion = evaluaciones_service.create_evaluacion(
        {"curso_id": curso["id"], "titulo": "Gam Eval", "puntaje_minimo": 70, "max_intentos": 2},
        actor_key="admin-1",
        actor_name="Administrador",
    )
    pregunta = evaluaciones_service.create_pregunta(
        {
            "evaluacion_id": evaluacion["id"],
            "enunciado": "Pregunta",
            "tipo": "opcion_multiple",
            "puntaje": 10,
            "opciones": [
                {"texto": "Correcta", "es_correcta": True, "orden": 0},
                {"texto": "Incorrecta", "es_correcta": False, "orden": 1},
            ],
        },
        actor_key="admin-1",
        actor_name="Administrador",
    )
    intento = evaluaciones_service.iniciar_intento(inscripcion["id"], evaluacion["id"])
    evaluaciones_service.enviar_respuestas(
        intento["intento_id"],
        None,
        {str(pregunta["id"]): pregunta["opciones"][0]["id"]},
        actor_key="admin-1",
        actor_name="Administrador",
    )

    perfil = gamificacion_service.get_perfil_gamificacion("colab-gam")
    assert perfil["streak_actual"] >= 1
    assert any(item["motivo"] == "constancia_diaria" for item in perfil["actividad_reciente"])
    assert any(item["motivo"] == "aprobado_primer_intento" for item in perfil["actividad_reciente"])
    assert any(item["codigo"] == "reto_primer_intento" for item in perfil["retos_mensuales"])

    ranking = gamificacion_service.get_ranking(scope="departamento", value="Ventas")
    assert ranking
    assert ranking[0]["scope_label"] == "Ventas"


def test_api_gamificacion_administra_insignias_y_metas():
    client = _build_client()

    crear = client.post(
        "/api/capacitacion/gamificacion/insignias",
        json={
            "nombre": "Meta sprint",
            "descripcion": "Nueva insignia",
            "icono_emoji": "🚀",
            "condicion_tipo": "racha_dias",
            "condicion_valor": 4,
            "color": "#ff6600",
            "orden": 90,
        },
    )
    assert crear.status_code == 201
    insignia_id = crear.json()["id"]

    actualizar = client.put(
        f"/api/capacitacion/gamificacion/insignias/{insignia_id}",
        json={"nombre": "Meta sprint editada", "condicion_valor": 5},
    )
    assert actualizar.status_code == 200
    assert actualizar.json()["nombre"] == "Meta sprint editada"

    metas = client.get("/api/capacitacion/gamificacion/metas-departamento")
    assert metas.status_code == 200
    assert isinstance(metas.json(), list)

    eliminar = client.delete(f"/api/capacitacion/gamificacion/insignias/{insignia_id}")
    assert eliminar.status_code == 200
    assert eliminar.json()["ok"] is True


def test_upload_archivos_en_leccion_presentacion_y_evidencia():
    client = _build_client()
    _, curso, leccion_1, _ = _create_course_graph()
    presentacion = presentaciones_service.create_presentacion({"titulo": "Archivos", "autor_key": "autor-1"})
    inscripcion, _ = progreso_service.inscribir_colaborador({"colaborador_key": "upload-1", "colaborador_nombre": "Uploader", "curso_id": curso["id"]})

    lesson_upload = client.post(
        f"/api/capacitacion/lecciones/{leccion_1['id']}/archivo",
        files={"archivo": ("manual.pdf", BytesIO(b"%PDF-1.4 test"), "application/pdf")},
    )
    assert lesson_upload.status_code == 201
    assert lesson_upload.json()["public_url"].endswith(".pdf")

    asset_upload = client.post(
        f"/api/capacitacion/presentaciones/{presentacion['id']}/assets/upload?tipo=imagen",
        files={"archivo": ("imagen.png", BytesIO(b"fakepng"), "image/png")},
    )
    assert asset_upload.status_code == 201
    assert asset_upload.json()["url"].endswith(".png")

    evidencia_upload = client.post(
        f"/api/capacitacion/inscripciones/{inscripcion['id']}/evidencias",
        files={"archivo": ("evidencia.mp3", BytesIO(b"fakeaudio"), "audio/mpeg")},
    )
    assert evidencia_upload.status_code == 201
    evidencias = client.get(f"/api/capacitacion/inscripciones/{inscripcion['id']}/evidencias")
    assert evidencias.status_code == 200
    assert len(evidencias.json()) == 1


def test_dashboard_stats_incluye_indicadores_de_control():
    categoria = cursos_service.create_categoria({"nombre": "Cumplimiento", "descripcion": "Control", "color": "#334455"})
    curso_activo = cursos_service.create_curso(
        {
            "nombre": "Curso activo",
            "descripcion": "Publicado",
            "categoria_id": categoria["id"],
            "estado": "publicado",
            "es_obligatorio": True,
            "fecha_fin": date(2025, 1, 10),
        }
    )
    curso_archivado = cursos_service.create_curso(
        {
            "nombre": "Curso archivado",
            "descripcion": "Archivado",
            "categoria_id": categoria["id"],
            "estado": "archivado",
        }
    )
    leccion = cursos_service.create_leccion({"curso_id": curso_activo["id"], "titulo": "Modulo 1", "tipo": "texto", "orden": 0, "es_obligatoria": True})
    insc_1, _ = progreso_service.inscribir_colaborador(
        {"colaborador_key": "dash-1", "colaborador_nombre": "Dash Uno", "departamento": "RRHH", "curso_id": curso_activo["id"]}
    )
    insc_2, _ = progreso_service.inscribir_colaborador(
        {"colaborador_key": "dash-2", "colaborador_nombre": "Dash Dos", "departamento": "RRHH", "curso_id": curso_activo["id"]}
    )
    progreso_service.marcar_leccion_completada(insc_1["id"], leccion["id"])
    evaluacion = evaluaciones_service.create_evaluacion({"curso_id": curso_activo["id"], "titulo": "Eval", "puntaje_minimo": 70, "max_intentos": 1})
    pregunta = evaluaciones_service.create_pregunta(
        {
            "evaluacion_id": evaluacion["id"],
            "enunciado": "Pregunta",
            "tipo": "opcion_multiple",
            "puntaje": 10,
            "opciones": [
                {"texto": "Correcta", "es_correcta": True, "orden": 0},
                {"texto": "Incorrecta", "es_correcta": False, "orden": 1},
            ],
        }
    )
    intento = evaluaciones_service.iniciar_intento(insc_1["id"], evaluacion["id"])
    evaluaciones_service.enviar_respuestas(intento["intento_id"], None, {str(pregunta["id"]): pregunta["opciones"][0]["id"]})

    stats = progreso_service.get_dashboard_stats()
    assert stats["cursos_publicados"] >= 1
    assert stats["cursos_archivados"] >= 1
    assert "tasa_aprobacion" in stats
    assert "promedio_finalizacion_dias" in stats
    assert isinstance(stats["avance_departamento"], list)
    assert isinstance(stats["top_cursos_abandonados"], list)
    assert isinstance(stats["sin_avance"], list)
    assert isinstance(stats["certificados_por_periodo"], list)
    assert isinstance(stats["cursos_peor_aprobacion"], list)
    assert stats["obligatorios_vencidos_total"] >= 1


def test_operacion_prerrequisitos_versionado_y_encuesta_satisfaccion():
    categoria = cursos_service.create_categoria({"nombre": "Rutas", "descripcion": "Operativa", "color": "#112233"})
    curso_base = cursos_service.create_curso(
        {
            "nombre": "Base",
            "categoria_id": categoria["id"],
            "estado": "publicado",
            "es_obligatorio": True,
            "vence_dias": 1,
            "recordatorio_dias": 10,
            "reinscripcion_automatica": True,
        }
    )
    cursos_service.create_leccion({"curso_id": curso_base["id"], "titulo": "L1", "tipo": "texto", "orden": 0, "es_obligatoria": True})
    curso_avanzado = cursos_service.create_curso(
        {
            "nombre": "Avanzado",
            "categoria_id": categoria["id"],
            "estado": "publicado",
            "prerrequisitos": [curso_base["id"]],
            "bloquear_certificado_encuesta": True,
            "requiere_encuesta_satisfaccion": True,
        }
    )
    cursos_service.create_leccion({"curso_id": curso_avanzado["id"], "titulo": "L2", "tipo": "texto", "orden": 0, "es_obligatoria": True})

    with pytest.raises(ValueError, match="prerrequisitos"):
        progreso_service.inscribir_colaborador({"colaborador_key": "ops-1", "colaborador_nombre": "Ops Uno", "curso_id": curso_avanzado["id"]})

    insc_base, _ = progreso_service.inscribir_colaborador({"colaborador_key": "ops-1", "colaborador_nombre": "Ops Uno", "curso_id": curso_base["id"]})
    db = SessionLocal()
    try:
        from fastapi_modulo.modulos.capacitacion.repositorios.inscripciones_repository import get_inscripcion
        base_obj = get_inscripcion(db, insc_base["id"])
        base_obj.estado = "completado"
        base_obj.aprobado = True
        base_obj.pct_avance = 100.0
        db.commit()
    finally:
        db.close()
    insc_avanzado, _ = progreso_service.inscribir_colaborador({"colaborador_key": "ops-1", "colaborador_nombre": "Ops Uno", "curso_id": curso_avanzado["id"]})

    curso_recert = cursos_service.create_curso(
        {
            "nombre": "Recertificacion",
            "categoria_id": categoria["id"],
            "estado": "publicado",
            "es_obligatorio": True,
            "vence_dias": 1,
            "recordatorio_dias": 10,
            "reinscripcion_automatica": True,
        }
    )
    cursos_service.create_leccion({"curso_id": curso_recert["id"], "titulo": "L3", "tipo": "texto", "orden": 0, "es_obligatoria": True})
    insc_recert, _ = progreso_service.inscribir_colaborador({"colaborador_key": "ops-1", "colaborador_nombre": "Ops Uno", "curso_id": curso_recert["id"]})
    db = SessionLocal()
    try:
        base_obj = get_inscripcion(db, insc_base["id"])
        recert_obj = get_inscripcion(db, insc_recert["id"])
        recert_obj.estado = "completado"
        recert_obj.aprobado = True
        recert_obj.pct_avance = 100.0
        recert_obj.fecha_vencimiento = datetime.utcnow() - timedelta(days=1)
        db.commit()
    finally:
        db.close()

    resultado_operacion = progreso_service.ejecutar_operacion_cursos()
    assert resultado_operacion["reinscripciones"] >= 1
    db = SessionLocal()
    try:
        from fastapi_modulo.modulos.capacitacion.repositorios.evaluaciones_repository import get_inscripcion
        insc_obj = get_inscripcion(db, insc_avanzado["id"])
        insc_obj.aprobado = True
        insc_obj.pct_avance = 100.0
        with pytest.raises(ValueError, match="encuesta de satisfaccion"):
            certificados_service.emitir_certificado(db, insc_obj, 95)
        db.rollback()
    finally:
        db.close()

    satisfaccion = progreso_service.registrar_encuesta_satisfaccion(insc_avanzado["id"], 5, "Excelente")
    assert satisfaccion["calificacion"] == 5

    ruta = cursos_service.create_ruta(
        {
            "nombre": "Ruta onboarding",
            "descripcion": "Ruta inicial",
            "departamentos": ["RRHH"],
            "cursos": [{"curso_id": curso_base["id"], "orden": 0}, {"curso_id": curso_avanzado["id"], "orden": 1}],
        }
    )
    assert len(ruta["cursos"]) == 2

    nueva_version = cursos_service.duplicate_as_new_version(curso_base["id"])
    assert nueva_version["version_numero"] == 2
    assert nueva_version["version_padre_id"] == curso_base["id"]

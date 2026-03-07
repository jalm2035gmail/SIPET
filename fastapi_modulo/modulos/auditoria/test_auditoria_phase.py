from __future__ import annotations

import os
import sys
import types

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SQLITE_DB_PATH", "/tmp/sipet_auditoria_phase.sqlite3")
pytestmark = pytest.mark.filterwarnings("ignore:The 'app' shortcut is now deprecated.*:DeprecationWarning")

# ── Stub fastapi_modulo.main ─────────────────────────────────────────────────

fake_main = types.ModuleType("fastapi_modulo.main")


def _fake_render_backend_page(request, title, description="", content="", **_):
    html = f"<html><head><title>{title}</title></head><body>{content}</body></html>"
    return HTMLResponse(content=html)


def _fake_get_user_app_access(request):
    raw = request.headers.get("x-app-access", "")
    return [x.strip() for x in raw.split(",") if x.strip()]


def _fake_is_admin_or_superadmin(request):
    return getattr(request.state, "user_role", "").lower() in {
        "administrador", "admin", "superadministrador", "superadmin",
    }


fake_main.render_backend_page = _fake_render_backend_page
fake_main._get_user_app_access = _fake_get_user_app_access
fake_main.is_admin_or_superadmin = _fake_is_admin_or_superadmin
sys.modules["fastapi_modulo.main"] = fake_main

# ── Imports del módulo ───────────────────────────────────────────────────────

from fastapi_modulo.db import Base, engine  # noqa: E402
from fastapi_modulo.modulos.auditoria.auditoria import router  # noqa: E402
from fastapi_modulo.modulos.auditoria.aud_db_models import (  # noqa: E402
    AudAuditoria,
    AudHallazgo,
    AudRecomendacion,
    AudSeguimiento,
)

AUD_TABLES = [
    AudAuditoria.__table__,
    AudHallazgo.__table__,
    AudRecomendacion.__table__,
    AudSeguimiento.__table__,
]


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _build_client() -> TestClient:
    app = FastAPI()

    @app.middleware("http")
    async def inject_session(request: Request, call_next):
        request.state.user_name = request.headers.get("x-user", "tester")
        request.state.user_role = request.headers.get("x-role", "usuario")
        request.state.tenant_id = "test"
        return await call_next(request)

    app.include_router(router)
    return TestClient(app)


def _auth(role: str = "usuario", *access: str) -> dict:
    h = {"x-role": role, "x-user": "aud.test"}
    if access:
        h["x-app-access"] = ",".join(access)
    return h


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine, tables=AUD_TABLES, checkfirst=True)
    Base.metadata.create_all(bind=engine, tables=AUD_TABLES, checkfirst=True)


# ── Permisos ─────────────────────────────────────────────────────────────────

def test_html_requires_access():
    client = _build_client()
    r = client.get("/auditoria")
    assert r.status_code == 403
    assert "Auditoría" in r.json()["detail"]


def test_admin_bypasses_permission():
    client = _build_client()
    r = client.get("/auditoria", headers=_auth("administrador"))
    assert r.status_code == 200
    assert "aud-root" in r.text


def test_html_renders_with_access():
    client = _build_client()
    r = client.get("/auditoria", headers=_auth("usuario", "Auditoria"))
    assert r.status_code == 200
    assert "aud-root" in r.text


def test_api_blocks_without_access():
    client = _build_client()
    r = client.get("/api/auditoria/auditorias")
    assert r.status_code == 403


def test_js_asset_served():
    client = _build_client()
    r = client.get("/api/auditoria/assets/auditoria.js", headers=_auth("usuario", "Auditoria"))
    assert r.status_code == 200
    assert "application/javascript" in r.headers["content-type"]


# ── Auditorías CRUD ───────────────────────────────────────────────────────────

def test_create_and_list_auditoria():
    client = _build_client()
    h = _auth("usuario", "Auditoria")

    r = client.post("/api/auditoria/auditorias", headers=h, json={
        "codigo": "AUD-2026-001",
        "nombre": "Auditoría Operativa Q1",
        "tipo": "interna",
        "area_auditada": "Finanzas",
        "estado": "planificada",
        "responsable": "Ana López",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["codigo"] == "AUD-2026-001"
    aud_id = data["id"]

    listing = client.get("/api/auditoria/auditorias", headers=h)
    assert any(a["id"] == aud_id for a in listing.json())


def test_get_auditoria_detail():
    client = _build_client()
    h = _auth("usuario", "Auditoria")
    r = client.post("/api/auditoria/auditorias", headers=h, json={"codigo": "AUD-DET", "nombre": "Detalle"})
    aud_id = r.json()["id"]
    detail = client.get(f"/api/auditoria/auditorias/{aud_id}", headers=h)
    assert detail.status_code == 200
    assert detail.json()["nombre"] == "Detalle"


def test_get_auditoria_not_found():
    client = _build_client()
    r = client.get("/api/auditoria/auditorias/99999", headers=_auth("usuario", "Auditoria"))
    assert r.status_code == 404


def test_update_auditoria_estado():
    client = _build_client()
    h = _auth("usuario", "Auditoria")
    r = client.post("/api/auditoria/auditorias", headers=h, json={"codigo": "AUD-UPD", "nombre": "Actualizar"})
    aud_id = r.json()["id"]
    upd = client.put(f"/api/auditoria/auditorias/{aud_id}", headers=h, json={"estado": "en_proceso"})
    assert upd.status_code == 200
    assert upd.json()["estado"] == "en_proceso"


def test_delete_auditoria():
    client = _build_client()
    h = _auth("usuario", "Auditoria")
    r = client.post("/api/auditoria/auditorias", headers=h, json={"codigo": "AUD-DEL", "nombre": "Borrar"})
    aud_id = r.json()["id"]
    d = client.delete(f"/api/auditoria/auditorias/{aud_id}", headers=h)
    assert d.status_code == 200
    assert d.json()["ok"] is True
    listing = client.get("/api/auditoria/auditorias", headers=h)
    assert not any(a["id"] == aud_id for a in listing.json())


def test_duplicate_codigo_rejected():
    client = _build_client()
    h = _auth("usuario", "Auditoria")
    client.post("/api/auditoria/auditorias", headers=h, json={"codigo": "AUD-DUP", "nombre": "Primero"})
    r = client.post("/api/auditoria/auditorias", headers=h, json={"codigo": "AUD-DUP", "nombre": "Segundo"})
    assert r.status_code == 409


def test_filter_auditorias_by_estado():
    client = _build_client()
    h = _auth("usuario", "Auditoria")
    client.post("/api/auditoria/auditorias", headers=h, json={"codigo": "AUD-F1", "nombre": "En proceso", "estado": "en_proceso"})
    client.post("/api/auditoria/auditorias", headers=h, json={"codigo": "AUD-F2", "nombre": "Cerrada", "estado": "cerrada"})
    r = client.get("/api/auditoria/auditorias?estado=en_proceso", headers=h)
    assert all(a["estado"] == "en_proceso" for a in r.json())


# ── Hallazgos CRUD ────────────────────────────────────────────────────────────

def _new_auditoria(client, headers, suffix=""):
    return client.post("/api/auditoria/auditorias", headers=headers,
                       json={"codigo": f"AUD-H{suffix}", "nombre": f"Aud {suffix}"}).json()["id"]


def test_create_hallazgo():
    client = _build_client()
    h = _auth("usuario", "Auditoria")
    aud_id = _new_auditoria(client, h, "1")
    r = client.post("/api/auditoria/hallazgos", headers=h, json={
        "auditoria_id": aud_id,
        "titulo": "Falta de conciliaciones",
        "nivel_riesgo": "alto",
        "estado": "abierto",
        "responsable": "Pedro",
    })
    assert r.status_code == 201
    assert r.json()["nivel_riesgo"] == "alto"
    assert r.json()["auditoria_nombre"] is not None


def test_update_hallazgo_estado():
    client = _build_client()
    h = _auth("usuario", "Auditoria")
    aud_id = _new_auditoria(client, h, "2")
    hall = client.post("/api/auditoria/hallazgos", headers=h, json={
        "auditoria_id": aud_id, "titulo": "Hallazgo X",
    }).json()
    upd = client.put(f"/api/auditoria/hallazgos/{hall['id']}", headers=h, json={"estado": "en_atencion"})
    assert upd.status_code == 200
    assert upd.json()["estado"] == "en_atencion"


def test_delete_hallazgo_cascade():
    client = _build_client()
    h = _auth("usuario", "Auditoria")
    aud_id = _new_auditoria(client, h, "3")
    hall = client.post("/api/auditoria/hallazgos", headers=h, json={
        "auditoria_id": aud_id, "titulo": "Para eliminar",
    }).json()
    d = client.delete(f"/api/auditoria/hallazgos/{hall['id']}", headers=h)
    assert d.status_code == 200
    listing = client.get(f"/api/auditoria/hallazgos?auditoria_id={aud_id}", headers=h)
    assert not any(x["id"] == hall["id"] for x in listing.json())


def test_filter_hallazgos_by_nivel_riesgo():
    client = _build_client()
    h = _auth("usuario", "Auditoria")
    aud_id = _new_auditoria(client, h, "4")
    client.post("/api/auditoria/hallazgos", headers=h, json={"auditoria_id": aud_id, "titulo": "Crítico", "nivel_riesgo": "critico"})
    client.post("/api/auditoria/hallazgos", headers=h, json={"auditoria_id": aud_id, "titulo": "Bajo", "nivel_riesgo": "bajo"})
    r = client.get("/api/auditoria/hallazgos?nivel_riesgo=critico", headers=h)
    assert all(x["nivel_riesgo"] == "critico" for x in r.json())


def test_delete_auditoria_cascades_hallazgos():
    client = _build_client()
    h = _auth("usuario", "Auditoria")
    aud_id = _new_auditoria(client, h, "5")
    client.post("/api/auditoria/hallazgos", headers=h, json={"auditoria_id": aud_id, "titulo": "H cascade"})
    client.delete(f"/api/auditoria/auditorias/{aud_id}", headers=h)
    r = client.get(f"/api/auditoria/hallazgos?auditoria_id={aud_id}", headers=h)
    assert r.json() == []


# ── Recomendaciones CRUD ──────────────────────────────────────────────────────

def _new_hallazgo(client, headers, aud_id, titulo="H"):
    return client.post("/api/auditoria/hallazgos", headers=headers,
                       json={"auditoria_id": aud_id, "titulo": titulo}).json()["id"]


def test_create_recomendacion():
    client = _build_client()
    h = _auth("usuario", "Auditoria")
    aud_id = _new_auditoria(client, h, "R1")
    hall_id = _new_hallazgo(client, h, aud_id, "Hall R1")
    r = client.post("/api/auditoria/recomendaciones", headers=h, json={
        "hallazgo_id": hall_id,
        "descripcion": "Implementar proceso de conciliación mensual",
        "prioridad": "alta",
        "responsable": "Jefe Finanzas",
        "porcentaje_avance": 0,
    })
    assert r.status_code == 201
    data = r.json()
    assert data["prioridad"] == "alta"
    assert data["hallazgo_titulo"] is not None


def test_update_recomendacion_avance():
    client = _build_client()
    h = _auth("usuario", "Auditoria")
    aud_id = _new_auditoria(client, h, "R2")
    hall_id = _new_hallazgo(client, h, aud_id, "Hall R2")
    rec = client.post("/api/auditoria/recomendaciones", headers=h, json={
        "hallazgo_id": hall_id, "descripcion": "Rec avance",
    }).json()
    upd = client.put(f"/api/auditoria/recomendaciones/{rec['id']}", headers=h,
                     json={"porcentaje_avance": 50, "estado": "en_proceso"})
    assert upd.status_code == 200
    assert upd.json()["porcentaje_avance"] == 50


def test_delete_recomendacion():
    client = _build_client()
    h = _auth("usuario", "Auditoria")
    aud_id = _new_auditoria(client, h, "R3")
    hall_id = _new_hallazgo(client, h, aud_id, "Hall R3")
    rec = client.post("/api/auditoria/recomendaciones", headers=h, json={
        "hallazgo_id": hall_id, "descripcion": "Borrar esta",
    }).json()
    d = client.delete(f"/api/auditoria/recomendaciones/{rec['id']}", headers=h)
    assert d.status_code == 200


def test_filter_recomendaciones_por_estado():
    client = _build_client()
    h = _auth("usuario", "Auditoria")
    aud_id = _new_auditoria(client, h, "R4")
    hall_id = _new_hallazgo(client, h, aud_id, "Hall R4")
    client.post("/api/auditoria/recomendaciones", headers=h, json={
        "hallazgo_id": hall_id, "descripcion": "Pendiente", "estado": "pendiente"})
    client.post("/api/auditoria/recomendaciones", headers=h, json={
        "hallazgo_id": hall_id, "descripcion": "Implementada", "estado": "implementada"})
    r = client.get("/api/auditoria/recomendaciones?estado=pendiente", headers=h)
    assert all(x["estado"] == "pendiente" for x in r.json())


# ── Seguimiento ───────────────────────────────────────────────────────────────

def _full_chain(client, headers, suffix=""):
    aud_id  = _new_auditoria(client, headers, f"S{suffix}")
    hall_id = _new_hallazgo(client, headers, aud_id, f"Hall S{suffix}")
    rec = client.post("/api/auditoria/recomendaciones", headers=headers, json={
        "hallazgo_id": hall_id, "descripcion": f"Rec S{suffix}",
    }).json()
    return rec["id"]


def test_create_seguimiento():
    client = _build_client()
    h = _auth("usuario", "Auditoria")
    rec_id = _full_chain(client, h, "1")
    r = client.post("/api/auditoria/seguimiento", headers=h, json={
        "recomendacion_id": rec_id,
        "descripcion": "Se realizó taller de capacitación.",
        "porcentaje_avance": 30,
        "registrado_por": "aud.test",
    })
    assert r.status_code == 201
    assert r.json()["porcentaje_avance"] == 30


def test_seguimiento_actualiza_avance_recomendacion():
    client = _build_client()
    h = _auth("usuario", "Auditoria")
    rec_id = _full_chain(client, h, "2")
    client.post("/api/auditoria/seguimiento", headers=h, json={
        "recomendacion_id": rec_id, "descripcion": "Avance 60", "porcentaje_avance": 60,
    })
    rec = client.get(f"/api/auditoria/recomendaciones/{rec_id}", headers=h).json()
    assert rec["porcentaje_avance"] == 60


def test_seguimiento_100_marca_implementada():
    client = _build_client()
    h = _auth("usuario", "Auditoria")
    rec_id = _full_chain(client, h, "3")
    client.post("/api/auditoria/seguimiento", headers=h, json={
        "recomendacion_id": rec_id, "descripcion": "Completado", "porcentaje_avance": 100,
    })
    rec = client.get(f"/api/auditoria/recomendaciones/{rec_id}", headers=h).json()
    assert rec["estado"] == "implementada"
    assert rec["porcentaje_avance"] == 100


def test_list_seguimiento_filter():
    client = _build_client()
    h = _auth("usuario", "Auditoria")
    rec_id = _full_chain(client, h, "4")
    client.post("/api/auditoria/seguimiento", headers=h, json={
        "recomendacion_id": rec_id, "descripcion": "Entrada A", "porcentaje_avance": 20,
    })
    r = client.get(f"/api/auditoria/seguimiento?recomendacion_id={rec_id}", headers=h)
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_delete_seguimiento():
    client = _build_client()
    h = _auth("usuario", "Auditoria")
    rec_id = _full_chain(client, h, "5")
    seg = client.post("/api/auditoria/seguimiento", headers=h, json={
        "recomendacion_id": rec_id, "descripcion": "Borrar", "porcentaje_avance": 10,
    }).json()
    d = client.delete(f"/api/auditoria/seguimiento/{seg['id']}", headers=h)
    assert d.status_code == 200


# ── Resumen KPIs ─────────────────────────────────────────────────────────────

def test_resumen_campos():
    client = _build_client()
    h = _auth("usuario", "Auditoria")
    r = client.get("/api/auditoria/resumen", headers=h)
    assert r.status_code == 200
    data = r.json()
    for key in ("total_auditorias", "auditorias_en_proceso", "total_hallazgos",
                "hallazgos_abiertos", "hallazgos_criticos",
                "total_recomendaciones", "recomendaciones_pendientes",
                "recomendaciones_implementadas"):
        assert key in data
        assert isinstance(data[key], int)


def test_resumen_refleja_creaciones():
    client = _build_client()
    h = _auth("usuario", "Auditoria")
    pre = client.get("/api/auditoria/resumen", headers=h).json()
    client.post("/api/auditoria/auditorias", headers=h, json={"codigo": "AUD-KPI", "nombre": "KPI Test"})
    post = client.get("/api/auditoria/resumen", headers=h).json()
    assert post["total_auditorias"] == pre["total_auditorias"] + 1

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

from fastapi_modulo.db import MAIN, engine  # noqa: E402
from fastapi_modulo.modulos.auditoria.controladores.auditoria import router  # noqa: E402
from fastapi_modulo.modulos.auditoria.modelos.aud_db_models import (  # noqa: E402
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
    MAIN.metadata.drop_all(bind=engine, tables=AUD_TABLES, checkfirst=True)
    MAIN.metadata.create_all(bind=engine, tables=AUD_TABLES, checkfirst=True)


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


def test_svg_asset_served():
    client = _build_client()
    r = client.get("/api/auditoria/assets/auditoria.svg", headers=_auth("usuario", "Auditoria"))
    assert r.status_code == 200
    assert "image/svg+xml" in r.headers["content-type"]
    assert "<svg" in r.text


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
    # Crear auditoría y hallazgo
    aud = client.post("/api/auditoria/auditorias", json={
        "codigo": "AUD-001", "nombre": "Auditoría Test", "tipo": "interna"
    }, headers=_auth("usuario", "Auditoria")).json()
    hall = client.post("/api/auditoria/hallazgos", json={
        "auditoria_id": aud["id"], "codigo": "H-001", "titulo": "Hallazgo Test", "nivel_riesgo": "medio"
    }, headers=_auth("usuario", "Auditoria")).json()
    rec = client.post("/api/auditoria/recomendaciones", json={
        "hallazgo_id": hall["id"], "descripcion": "Recomendación Test", "prioridad": "alta"
    }, headers=_auth("usuario", "Auditoria"))
    assert rec.status_code == 200
    data = rec.json()
    assert data["descripcion"] == "Recomendación Test"
    assert data["prioridad"] == "alta"


def test_update_recomendacion():
    client = _build_client()
    aud = client.post("/api/auditoria/auditorias", json={"codigo": "AUD-002", "nombre": "Auditoría Test", "tipo": "interna"}, headers=_auth("usuario", "Auditoria")).json()
    hall = client.post("/api/auditoria/hallazgos", json={"auditoria_id": aud["id"], "codigo": "H-002", "titulo": "Hallazgo Test", "nivel_riesgo": "medio"}, headers=_auth("usuario", "Auditoria")).json()
    rec = client.post("/api/auditoria/recomendaciones", json={"hallazgo_id": hall["id"], "descripcion": "Recomendación Test", "prioridad": "media"}, headers=_auth("usuario", "Auditoria")).json()
    upd = client.put(f"/api/auditoria/recomendaciones/{rec['id']}", json={"descripcion": "Actualizada", "prioridad": "baja"}, headers=_auth("usuario", "Auditoria"))
    assert upd.status_code == 200
    data = upd.json()
    assert data["descripcion"] == "Actualizada"
    assert data["prioridad"] == "baja"


def test_delete_recomendacion():
    client = _build_client()
    aud = client.post("/api/auditoria/auditorias", json={"codigo": "AUD-003", "nombre": "Auditoría Test", "tipo": "interna"}, headers=_auth("usuario", "Auditoria")).json()
    hall = client.post("/api/auditoria/hallazgos", json={"auditoria_id": aud["id"], "codigo": "H-003", "titulo": "Hallazgo Test", "nivel_riesgo": "medio"}, headers=_auth("usuario", "Auditoria")).json()
    rec = client.post("/api/auditoria/recomendaciones", json={"hallazgo_id": hall["id"], "descripcion": "Recomendación Test", "prioridad": "media"}, headers=_auth("usuario", "Auditoria")).json()
    delr = client.delete(f"/api/auditoria/recomendaciones/{rec['id']}", headers=_auth("usuario", "Auditoria"))
    assert delr.status_code == 200
    assert delr.json() is True


def test_filtrar_recomendaciones_por_estado():
    client = _build_client()
    aud = client.post("/api/auditoria/auditorias", json={"codigo": "AUD-004", "nombre": "Auditoría Test", "tipo": "interna"}, headers=_auth("usuario", "Auditoria")).json()
    hall = client.post("/api/auditoria/hallazgos", json={"auditoria_id": aud["id"], "codigo": "H-004", "titulo": "Hallazgo Test", "nivel_riesgo": "medio"}, headers=_auth("usuario", "Auditoria")).json()
    client.post("/api/auditoria/recomendaciones", json={"hallazgo_id": hall["id"], "descripcion": "Rec1", "estado": "pendiente"}, headers=_auth("usuario", "Auditoria"))
    client.post("/api/auditoria/recomendaciones", json={"hallazgo_id": hall["id"], "descripcion": "Rec2", "estado": "implementada"}, headers=_auth("usuario", "Auditoria"))
    r = client.get(f"/api/auditoria/recomendaciones?estado=implementada", headers=_auth("usuario", "Auditoria"))
    assert r.status_code == 200
    data = r.json()
    assert all(rec["estado"] == "implementada" for rec in data)


def test_create_seguimiento():
    client = _build_client()
    aud = client.post("/api/auditoria/auditorias", json={"codigo": "AUD-005", "nombre": "Auditoría Test", "tipo": "interna"}, headers=_auth("usuario", "Auditoria")).json()
    hall = client.post("/api/auditoria/hallazgos", json={"auditoria_id": aud["id"], "codigo": "H-005", "titulo": "Hallazgo Test", "nivel_riesgo": "medio"}, headers=_auth("usuario", "Auditoria")).json()
    rec = client.post("/api/auditoria/recomendaciones", json={"hallazgo_id": hall["id"], "descripcion": "Recomendación Test", "prioridad": "media"}, headers=_auth("usuario", "Auditoria")).json()
    seg = client.post("/api/auditoria/seguimiento", json={"recomendacion_id": rec["id"], "descripcion": "Avance Test", "porcentaje_avance": 50}, headers=_auth("usuario", "Auditoria"))
    assert seg.status_code == 200
    data = seg.json()
    assert data["porcentaje_avance"] == 50


def test_delete_seguimiento():
    client = _build_client()
    aud = client.post("/api/auditoria/auditorias", json={"codigo": "AUD-006", "nombre": "Auditoría Test", "tipo": "interna"}, headers=_auth("usuario", "Auditoria")).json()
    hall = client.post("/api/auditoria/hallazgos", json={"auditoria_id": aud["id"], "codigo": "H-006", "titulo": "Hallazgo Test", "nivel_riesgo": "medio"}, headers=_auth("usuario", "Auditoria")).json()
    rec = client.post("/api/auditoria/recomendaciones", json={"hallazgo_id": hall["id"], "descripcion": "Recomendación Test", "prioridad": "media"}, headers=_auth("usuario", "Auditoria")).json()
    seg = client.post("/api/auditoria/seguimiento", json={"recomendacion_id": rec["id"], "descripcion": "Avance Test", "porcentaje_avance": 50}, headers=_auth("usuario", "Auditoria")).json()
    delseg = client.delete(f"/api/auditoria/seguimiento/{seg['id']}", headers=_auth("usuario", "Auditoria"))
    assert delseg.status_code == 200
    assert delseg.json() is True


def test_seguimiento_actualiza_avance():
    client = _build_client()
    aud = client.post("/api/auditoria/auditorias", json={"codigo": "AUD-007", "nombre": "Auditoría Test", "tipo": "interna"}, headers=_auth("usuario", "Auditoria")).json()
    hall = client.post("/api/auditoria/hallazgos", json={"auditoria_id": aud["id"], "codigo": "H-007", "titulo": "Hallazgo Test", "nivel_riesgo": "medio"}, headers=_auth("usuario", "Auditoria")).json()
    rec = client.post("/api/auditoria/recomendaciones", json={"hallazgo_id": hall["id"], "descripcion": "Recomendación Test", "prioridad": "media"}, headers=_auth("usuario", "Auditoria")).json()
    seg = client.post("/api/auditoria/seguimiento", json={"recomendacion_id": rec["id"], "descripcion": "Avance Test", "porcentaje_avance": 80}, headers=_auth("usuario", "Auditoria")).json()
    rec2 = client.get(f"/api/auditoria/recomendaciones/{rec['id']}", headers=_auth("usuario", "Auditoria")).json()
    assert rec2["porcentaje_avance"] == 80


def test_cascada_eliminar_auditoria():
    client = _build_client()
    aud = client.post("/api/auditoria/auditorias", json={"codigo": "AUD-008", "nombre": "Auditoría Test", "tipo": "interna"}, headers=_auth("usuario", "Auditoria")).json()
    hall = client.post("/api/auditoria/hallazgos", json={"auditoria_id": aud["id"], "codigo": "H-008", "titulo": "Hallazgo Test", "nivel_riesgo": "medio"}, headers=_auth("usuario", "Auditoria")).json()
    rec = client.post("/api/auditoria/recomendaciones", json={"hallazgo_id": hall["id"], "descripcion": "Recomendación Test", "prioridad": "media"}, headers=_auth("usuario", "Auditoria")).json()
    seg = client.post("/api/auditoria/seguimiento", json={"recomendacion_id": rec["id"], "descripcion": "Avance Test", "porcentaje_avance": 50}, headers=_auth("usuario", "Auditoria")).json()
    delaud = client.delete(f"/api/auditoria/auditorias/{aud['id']}", headers=_auth("usuario", "Auditoria"))
    assert delaud.status_code == 200
    # Hallazgo, recomendación y seguimiento deben eliminarse
    r = client.get(f"/api/auditoria/hallazgos/{hall['id']}", headers=_auth("usuario", "Auditoria"))
    assert r.status_code == 404
    r2 = client.get(f"/api/auditoria/recomendaciones/{rec['id']}", headers=_auth("usuario", "Auditoria"))
    assert r2.status_code == 404
    r3 = client.get(f"/api/auditoria/seguimiento/{seg['id']}", headers=_auth("usuario", "Auditoria"))
    assert r3.status_code == 404


def test_validaciones_dominio():
    client = _build_client()
    aud = client.post("/api/auditoria/auditorias", json={"codigo": "AUD-009", "nombre": "Auditoría Test", "tipo": "interna"}, headers=_auth("usuario", "Auditoria")).json()
    hall = client.post("/api/auditoria/hallazgos", json={"auditoria_id": aud["id"], "codigo": "H-009", "titulo": "Hallazgo Test", "nivel_riesgo": "medio"}, headers=_auth("usuario", "Auditoria")).json()
    # Recomendación con avance > 100
    rec = client.post("/api/auditoria/recomendaciones", json={"hallazgo_id": hall["id"], "descripcion": "Recomendación Test", "porcentaje_avance": 150}, headers=_auth("usuario", "Auditoria"))
    assert rec.status_code == 422
    # Seguimiento con avance negativo
    seg = client.post("/api/auditoria/seguimiento", json={"recomendacion_id": hall["id"], "descripcion": "Avance Test", "porcentaje_avance": -10}, headers=_auth("usuario", "Auditoria"))
    assert seg.status_code == 422


def test_error_ids_inexistentes():
    client = _build_client()
    r = client.get("/api/auditoria/recomendaciones/9999", headers=_auth("usuario", "Auditoria"))
    assert r.status_code == 404
    r2 = client.get("/api/auditoria/seguimiento/9999", headers=_auth("usuario", "Auditoria"))
    assert r2.status_code == 404

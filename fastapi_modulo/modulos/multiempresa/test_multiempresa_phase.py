from __future__ import annotations

import io
import os
import sys
import types

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SQLITE_DB_PATH", "/tmp/sipet_multiempresa_phase.sqlite3")
pytestmark = pytest.mark.filterwarnings("ignore:The 'app' shortcut is now deprecated.*:DeprecationWarning")

# ── Stub fastapi_modulo.main ──────────────────────────────────────────────────

fake_main = types.ModuleType("fastapi_modulo.main")


def _fake_render_backend_page(request, title="", description="", content="", **_):
    return HTMLResponse(content=f"<html><body>{content}</body></html>")


def _fake_get_user_app_access(request):
    raw = request.headers.get("x-app-access", "")
    return [x.strip() for x in raw.split(",") if x.strip()]


def _fake_is_admin_or_superadmin(request):
    return getattr(request.state, "user_role", "").lower() in {
        "administrador", "admin", "superadministrador", "superadmin",
        "administrador_multiempresa",
    }


def _fake_get_current_role(request):
    """Mirrors normalize_role_name logic used in the real app."""
    role = (getattr(request.state, "user_role", "") or "").strip().lower()
    alias = {
        "superadmin": "superadministrador",
        "admin": "administrador",
        "administrador_multiempresa": "administrador_multiempresa",
        "admin_multiempresa": "administrador_multiempresa",
    }
    return alias.get(role, role) or "usuario"


fake_main.render_backend_page = _fake_render_backend_page
fake_main._get_user_app_access = _fake_get_user_app_access
fake_main.is_admin_or_superadmin = _fake_is_admin_or_superadmin
fake_main.get_current_role = _fake_get_current_role
sys.modules["fastapi_modulo.main"] = fake_main

# ── Module imports ────────────────────────────────────────────────────────────

from fastapi_modulo.db import Base, engine  # noqa: E402
from fastapi_modulo.modulos.multiempresa.multiempresa import router  # noqa: E402
from fastapi_modulo.modulos.multiempresa.me_db_models import MeEmpresa  # noqa: E402

_ME_TABLES = [MeEmpresa.__table__]


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _build_client(tenant_id: str = "test") -> TestClient:
    app = FastAPI()

    @app.middleware("http")
    async def inject_session(request: Request, call_next):
        request.state.user_name = request.headers.get("x-user", "me.tester")
        request.state.user_role = request.headers.get("x-role", "usuario")
        request.state.tenant_id = request.headers.get("x-tenant", tenant_id)
        return await call_next(request)

    app.include_router(router)
    return TestClient(app)


def _auth(role: str = "usuario", *access: str) -> dict:
    h = {"x-role": role, "x-user": "me.test"}
    if access:
        h["x-app-access"] = ",".join(access)
    return h


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine, tables=_ME_TABLES, checkfirst=True)
    Base.metadata.create_all(bind=engine, tables=_ME_TABLES, checkfirst=True)


# ── Permisos ──────────────────────────────────────────────────────────────────

def test_acceso_denegado_sin_permiso():
    c = _build_client()
    r = c.get("/api/multiempresa/empresas", headers=_auth("usuario"))
    assert r.status_code == 403


def test_acceso_permitido_admin():
    c = _build_client()
    r = c.get("/api/multiempresa/empresas", headers=_auth("admin"))
    assert r.status_code == 200


def test_acceso_permitido_con_app_access():
    c = _build_client()
    r = c.get("/api/multiempresa/empresas", headers=_auth("usuario", "Multiempresa"))
    assert r.status_code == 200


# ── CRUD básico ───────────────────────────────────────────────────────────────

def _payload(**overrides):
    base = {
        "codigo": "AVANCOOP",
        "nombre": "Cooperativa Avance",
        "tenant_id": "avancoop",
        "email_contacto": "admin@avancoop.mx",
        "rfc": "AVA010101AAA",
        "telefono": "+52 55 0000 0000",
        "color_primario": "#1e40af",
        "estado": "activa",
    }
    base.update(overrides)
    return base


def test_crear_empresa():
    c = _build_client()
    h = _auth("admin")
    r = c.post("/api/multiempresa/empresas", json=_payload(), headers=h)
    assert r.status_code == 201
    d = r.json()
    assert d["codigo"] == "AVANCOOP"
    assert d["tenant_id"] == "avancoop"
    assert d["estado"] == "activa"
    assert d["logo_url"] is None


def test_listar_empresas():
    c = _build_client()
    h = _auth("admin")
    c.post("/api/multiempresa/empresas", json=_payload(), headers=h)
    r = c.get("/api/multiempresa/empresas", headers=h)
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_get_empresa():
    c = _build_client()
    h = _auth("admin")
    created = c.post("/api/multiempresa/empresas", json=_payload(), headers=h).json()
    r = c.get(f"/api/multiempresa/empresas/{created['id']}", headers=h)
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_get_empresa_no_existe():
    c = _build_client()
    r = c.get("/api/multiempresa/empresas/9999", headers=_auth("admin"))
    assert r.status_code == 404


def test_actualizar_empresa():
    c = _build_client()
    h = _auth("admin")
    created = c.post("/api/multiempresa/empresas", json=_payload(), headers=h).json()
    r = c.put(f"/api/multiempresa/empresas/{created['id']}",
              json={"nombre": "Avancoop Actualizada", "rfc": "AVA020202BBB"},
              headers=h)
    assert r.status_code == 200
    assert r.json()["nombre"] == "Avancoop Actualizada"
    assert r.json()["rfc"] == "AVA020202BBB"


def test_eliminar_empresa():
    c = _build_client()
    h = _auth("admin")
    created = c.post("/api/multiempresa/empresas", json=_payload(), headers=h).json()
    r = c.delete(f"/api/multiempresa/empresas/{created['id']}", headers=h)
    assert r.status_code == 204
    r2 = c.get(f"/api/multiempresa/empresas/{created['id']}", headers=h)
    assert r2.status_code == 404


def test_codigo_duplicado():
    c = _build_client()
    h = _auth("admin")
    c.post("/api/multiempresa/empresas", json=_payload(), headers=h)
    r = c.post("/api/multiempresa/empresas", json=_payload(nombre="Otra"), headers=h)
    assert r.status_code == 409


def test_tenant_id_duplicado():
    c = _build_client()
    h = _auth("admin")
    c.post("/api/multiempresa/empresas", json=_payload(), headers=h)
    r = c.post("/api/multiempresa/empresas",
               json=_payload(codigo="OTRACODE", nombre="Otra empresa"),
               headers=h)
    assert r.status_code == 409


def test_filtro_estado():
    c = _build_client()
    h = _auth("admin")
    c.post("/api/multiempresa/empresas", json=_payload(), headers=h)
    c.post("/api/multiempresa/empresas",
           json=_payload(codigo="INACTIVA", tenant_id="inactiva", nombre="Inactiva", estado="inactiva"),
           headers=h)
    r = c.get("/api/multiempresa/empresas?estado=activa", headers=h)
    assert r.status_code == 200
    for e in r.json():
        assert e["estado"] == "activa"


def test_codigo_normalizado_uppercase():
    c = _build_client()
    h = _auth("admin")
    r = c.post("/api/multiempresa/empresas",
               json=_payload(codigo="minuscula", tenant_id="minuscula"),
               headers=h)
    assert r.status_code == 201
    assert r.json()["codigo"] == "MINUSCULA"


def test_tenant_id_normalizado_lowercase():
    c = _build_client()
    h = _auth("admin")
    r = c.post("/api/multiempresa/empresas",
               json=_payload(codigo="TENANT2", tenant_id="UPPER-CASE"),
               headers=h)
    assert r.status_code == 201
    assert r.json()["tenant_id"] == "upper-case"


# ── Logo upload ───────────────────────────────────────────────────────────────

def test_subir_logo_png():
    c = _build_client()
    h = _auth("admin")
    created = c.post("/api/multiempresa/empresas", json=_payload(), headers=h).json()
    # Minimal 1x1 PNG
    png_bytes = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00'
        b'\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8'
        b'\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    r = c.post(
        f"/api/multiempresa/empresas/{created['id']}/logo",
        files={"file": ("logo.png", png_bytes, "image/png")},
        headers=h,
    )
    assert r.status_code == 200
    d = r.json()
    assert d["logo_filename"] is not None
    assert d["logo_url"] is not None
    assert "avancoop" in d["logo_filename"].lower()


def test_subir_logo_tipo_invalido():
    c = _build_client()
    h = _auth("admin")
    created = c.post("/api/multiempresa/empresas", json=_payload(), headers=h).json()
    r = c.post(
        f"/api/multiempresa/empresas/{created['id']}/logo",
        files={"file": ("malware.exe", b"MZ", "application/octet-stream")},
        headers=h,
    )
    assert r.status_code == 400


def test_servir_logo():
    c = _build_client()
    h = _auth("admin")
    created = c.post("/api/multiempresa/empresas", json=_payload(), headers=h).json()
    png_bytes = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00'
        b'\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8'
        b'\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    up = c.post(
        f"/api/multiempresa/empresas/{created['id']}/logo",
        files={"file": ("logo.png", png_bytes, "image/png")},
        headers=h,
    ).json()
    logo_url = up["logo_url"]
    r = c.get(logo_url, headers=h)
    assert r.status_code == 200
    assert "image" in r.headers.get("content-type", "")


def test_logo_no_encontrado():
    c = _build_client()
    r = c.get("/api/multiempresa/logos/inexistente.png", headers=_auth("admin"))
    assert r.status_code == 404


# ── Consolidado ───────────────────────────────────────────────────────────────

def test_consolidado_estructura():
    c = _build_client()
    h = _auth("admin")
    c.post("/api/multiempresa/empresas", json=_payload(), headers=h)
    c.post("/api/multiempresa/empresas",
           json=_payload(codigo="POLOTITLAN", tenant_id="polotitlan",
                         nombre="Caja Polotitlan", estado="activa"),
           headers=h)
    r = c.get("/api/multiempresa/consolidado", headers=h)
    assert r.status_code == 200
    d = r.json()
    assert "total_empresas" in d
    assert "empresas_activas" in d
    assert "empresas_inactivas" in d
    assert "empresas_con_logo" in d
    assert "empresas" in d
    assert d["total_empresas"] >= 2


def test_consolidado_kpis():
    c = _build_client()
    h = _auth("admin")
    c.post("/api/multiempresa/empresas", json=_payload(), headers=h)
    c.post("/api/multiempresa/empresas",
           json=_payload(codigo="INAC2", tenant_id="inac2",
                         nombre="Inactiva2", estado="inactiva"),
           headers=h)
    r = c.get("/api/multiempresa/consolidado", headers=h)
    d = r.json()
    assert d["empresas_activas"] >= 1
    assert d["empresas_inactivas"] >= 1


# ── Vistas ────────────────────────────────────────────────────────────────────

def test_pagina_html():
    c = _build_client()
    r = c.get("/multiempresa", headers=_auth("admin"))
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")


def test_js_asset():
    c = _build_client()
    r = c.get("/api/multiempresa/assets/multiempresa.js", headers=_auth("admin"))
    assert r.status_code == 200
    assert "javascript" in r.headers.get("content-type", "")

from __future__ import annotations

import os
import sys
import types

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SQLITE_DB_PATH", "/tmp/sipet_crm_phase6.sqlite3")
pytestmark = pytest.mark.filterwarnings("ignore:The 'app' shortcut is now deprecated.*:DeprecationWarning")

# ── Stub de fastapi_modulo.main ───────────────────────────────────────────────

fake_main = types.ModuleType("fastapi_modulo.main")


def _fake_render_backend_page(
    request: Request,
    title: str,
    description: str = "",
    content: str = "",
    **_: object,
) -> HTMLResponse:
    html = f"<html><head><title>{title}</title></head><body>{content}</body></html>"
    return HTMLResponse(content=html)


def _fake_get_user_app_access(request: Request) -> list[str]:
    raw = request.headers.get("x-app-access", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _fake_is_admin_or_superadmin(request: Request) -> bool:
    return getattr(request.state, "user_role", "").strip().lower() in {
        "administrador", "admin", "superadministrador", "superadmin",
    }


fake_main.render_backend_page = _fake_render_backend_page
fake_main._get_user_app_access = _fake_get_user_app_access
fake_main.is_admin_or_superadmin = _fake_is_admin_or_superadmin
sys.modules["fastapi_modulo.main"] = fake_main

# ── Imports del módulo bajo prueba ────────────────────────────────────────────

from fastapi_modulo.db import MAIN, engine  # noqa: E402
from fastapi_modulo.modulos.crm.controladores.crm import router  # noqa: E402
from fastapi_modulo.modulos.crm.modelos.crm_db_models import (  # noqa: E402
    CrmActividad,
    CrmCampania,
    CrmContacto,
    CrmContactoCampania,
    CrmNota,
    CrmOportunidad,
)

CRM_TABLES = [
    CrmContacto.__table__,
    CrmOportunidad.__table__,
    CrmActividad.__table__,
    CrmNota.__table__,
    CrmCampania.__table__,
    CrmContactoCampania.__table__,
]


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _build_client() -> TestClient:
    app = FastAPI()

    @app.middleware("http")
    async def inject_test_session(request: Request, call_next):
        request.state.user_name = request.headers.get("x-user", "tester")
        request.state.user_role = request.headers.get("x-role", "usuario")
        request.state.tenant_id = "test"
        return await call_next(request)

    app.include_router(router)
    return TestClient(app)


def _auth(role: str = "usuario", *access: str) -> dict[str, str]:
    headers = {"x-role": role, "x-user": "crm.test"}
    if access:
        headers["x-app-access"] = ",".join(access)
    return headers


def setup_function() -> None:
    MAIN.metadata.drop_all(bind=engine, tables=CRM_TABLES, checkfirst=True)
    MAIN.metadata.create_all(bind=engine, tables=CRM_TABLES, checkfirst=True)


# ── Permisos y acceso ─────────────────────────────────────────────────────────

def test_crm_html_requires_access() -> None:
    client = _build_client()
    response = client.get("/crm")
    assert response.status_code == 403
    assert response.json()["detail"] == "Acceso restringido al módulo CRM"


def test_crm_html_admin_bypasses_permission() -> None:
    client = _build_client()
    response = client.get("/crm", headers=_auth("administrador"))
    assert response.status_code == 200
    assert "crm-root" in response.text


def test_crm_html_renders_with_crm_access() -> None:
    client = _build_client()
    response = client.get("/crm", headers=_auth("usuario", "CRM"))
    assert response.status_code == 200
    assert "CRM" in response.text
    assert "crm-root" in response.text


def test_crm_api_blocks_without_access() -> None:
    client = _build_client()
    response = client.get("/api/crm/contactos")
    assert response.status_code == 403


def test_crm_js_asset_served() -> None:
    client = _build_client()
    response = client.get("/api/crm/assets/crm.js", headers=_auth("usuario", "CRM"))
    assert response.status_code == 200
    assert "application/javascript" in response.headers["content-type"]


# ── Contactos ─────────────────────────────────────────────────────────────────

def test_create_and_list_contacto() -> None:
    client = _build_client()
    headers = _auth("usuario", "CRM")

    r = client.post("/api/crm/contactos", headers=headers, json={
        "nombre": "Laura Gomez",
        "email": "laura@example.com",
        "telefono": "555-0101",
        "empresa": "Acme",
        "puesto": "Gerente",
        "tipo": "prospecto",
        "fuente": "backend",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["nombre"] == "Laura Gomez"
    assert data["tipo"] == "prospecto"
    contacto_id = data["id"]

    listing = client.get("/api/crm/contactos", headers=headers)
    assert listing.status_code == 200
    ids = [c["id"] for c in listing.json()]
    assert contacto_id in ids


def test_get_contacto_detail() -> None:
    client = _build_client()
    headers = _auth("usuario", "CRM")

    r = client.post("/api/crm/contactos", headers=headers, json={
        "nombre": "Pedro Ruiz",
        "email": "pedro@example.com",
    })
    contacto_id = r.json()["id"]

    detail = client.get(f"/api/crm/contactos/{contacto_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["nombre"] == "Pedro Ruiz"


def test_get_contacto_not_found() -> None:
    client = _build_client()
    r = client.get("/api/crm/contactos/99999", headers=_auth("usuario", "CRM"))
    assert r.status_code == 404


def test_update_contacto() -> None:
    client = _build_client()
    headers = _auth("usuario", "CRM")

    r = client.post("/api/crm/contactos", headers=headers, json={"nombre": "Carlos Mora"})
    contacto_id = r.json()["id"]

    upd = client.put(f"/api/crm/contactos/{contacto_id}", headers=headers, json={"tipo": "cliente"})
    assert upd.status_code == 200
    assert upd.json()["tipo"] == "cliente"


def test_delete_contacto() -> None:
    client = _build_client()
    headers = _auth("usuario", "CRM")

    r = client.post("/api/crm/contactos", headers=headers, json={"nombre": "Borrar Este"})
    contacto_id = r.json()["id"]

    d = client.delete(f"/api/crm/contactos/{contacto_id}", headers=headers)
    assert d.status_code == 200
    assert d.json()["ok"] is True

    listing = client.get("/api/crm/contactos", headers=headers)
    ids = [c["id"] for c in listing.json()]
    assert contacto_id not in ids


def test_duplicate_email_rejected() -> None:
    client = _build_client()
    headers = _auth("usuario", "CRM")

    client.post("/api/crm/contactos", headers=headers, json={
        "nombre": "Primero", "email": "dup@example.com",
    })
    r = client.post("/api/crm/contactos", headers=headers, json={
        "nombre": "Segundo", "email": "dup@example.com",
    })
    assert r.status_code == 409
    assert "email" in r.json()["detail"].lower()


# ── Oportunidades ─────────────────────────────────────────────────────────────

def test_create_oportunidad_full_flow() -> None:
    client = _build_client()
    headers = _auth("usuario", "CRM")

    contacto = client.post("/api/crm/contactos", headers=headers, json={"nombre": "Sofia Torres"})
    contacto_id = contacto.json()["id"]

    r = client.post("/api/crm/oportunidades", headers=headers, json={
        "contacto_id": contacto_id,
        "nombre": "Proyecto Alpha",
        "etapa": "negociacion",
        "valor_estimado": 25000.0,
        "probabilidad": 60,
        "responsable": "vendedor1",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["nombre"] == "Proyecto Alpha"
    assert data["etapa"] == "negociacion"
    assert data["contacto_nombre"] == "Sofia Torres"
    op_id = data["id"]

    listing = client.get("/api/crm/oportunidades", headers=headers)
    assert any(o["id"] == op_id for o in listing.json())


def test_update_oportunidad_etapa() -> None:
    client = _build_client()
    headers = _auth("usuario", "CRM")

    contacto = client.post("/api/crm/contactos", headers=headers, json={"nombre": "Rene Vargas"})
    contacto_id = contacto.json()["id"]
    op = client.post("/api/crm/oportunidades", headers=headers, json={
        "contacto_id": contacto_id, "nombre": "Deal B",
    })
    op_id = op.json()["id"]

    upd = client.put(f"/api/crm/oportunidades/{op_id}", headers=headers, json={"etapa": "cerrado_ganado"})
    assert upd.status_code == 200
    assert upd.json()["etapa"] == "cerrado_ganado"


def test_delete_oportunidad() -> None:
    client = _build_client()
    headers = _auth("usuario", "CRM")

    contacto = client.post("/api/crm/contactos", headers=headers, json={"nombre": "Hugo Diaz"})
    contacto_id = contacto.json()["id"]
    op = client.post("/api/crm/oportunidades", headers=headers, json={
        "contacto_id": contacto_id, "nombre": "Deal C",
    })
    op_id = op.json()["id"]

    d = client.delete(f"/api/crm/oportunidades/{op_id}", headers=headers)
    assert d.status_code == 200
    listing = client.get("/api/crm/oportunidades", headers=headers)
    assert not any(o["id"] == op_id for o in listing.json())


def test_filtrar_oportunidades_por_etapa() -> None:
    client = _build_client()
    headers = _auth("usuario", "CRM")

    contacto = client.post("/api/crm/contactos", headers=headers, json={"nombre": "Filtro Test"})
    cid = contacto.json()["id"]
    client.post("/api/crm/oportunidades", headers=headers, json={"contacto_id": cid, "nombre": "Ganada", "etapa": "cerrado_ganado"})
    client.post("/api/crm/oportunidades", headers=headers, json={"contacto_id": cid, "nombre": "Perdida", "etapa": "cerrado_perdido"})

    r = client.get("/api/crm/oportunidades?etapa=cerrado_ganado", headers=headers)
    assert r.status_code == 200
    assert all(o["etapa"] == "cerrado_ganado" for o in r.json())


# ── Actividades ───────────────────────────────────────────────────────────────

def test_crear_y_completar_actividad() -> None:
    client = _build_client()
    headers = _auth("usuario", "CRM")

    contacto = client.post("/api/crm/contactos", headers=headers, json={"nombre": "Mario Leal"})
    cid = contacto.json()["id"]

    r = client.post("/api/crm/actividades", headers=headers, json={
        "contacto_id": cid,
        "tipo": "llamada",
        "titulo": "Llamada inicial",
        "responsable": "vendedor2",
    })
    assert r.status_code == 201
    act_id = r.json()["id"]
    assert r.json()["completada"] is False

    upd = client.put(f"/api/crm/actividades/{act_id}", headers=headers, json={"completada": True})
    assert upd.status_code == 200
    assert upd.json()["completada"] is True


def test_filtrar_actividades_pendientes() -> None:
    client = _build_client()
    headers = _auth("usuario", "CRM")

    r_pend = client.get("/api/crm/actividades?completada=false", headers=headers)
    assert r_pend.status_code == 200
    assert all(not a["completada"] for a in r_pend.json())


def test_delete_actividad() -> None:
    client = _build_client()
    headers = _auth("usuario", "CRM")

    r = client.post("/api/crm/actividades", headers=headers, json={"tipo": "tarea", "titulo": "Borrar esto"})
    act_id = r.json()["id"]

    d = client.delete(f"/api/crm/actividades/{act_id}", headers=headers)
    assert d.status_code == 200


# ── Notas ─────────────────────────────────────────────────────────────────────

def test_crear_y_eliminar_nota() -> None:
    client = _build_client()
    headers = _auth("usuario", "CRM")

    contacto = client.post("/api/crm/contactos", headers=headers, json={"nombre": "Elena Cruz"})
    cid = contacto.json()["id"]

    r = client.post("/api/crm/notas", headers=headers, json={
        "contacto_id": cid,
        "contenido": "Interesado en producto X",
        "autor": "crm.test",
    })
    assert r.status_code == 201
    nota_id = r.json()["id"]

    listing = client.get(f"/api/crm/notas?contacto_id={cid}", headers=headers)
    assert any(n["id"] == nota_id for n in listing.json())

    d = client.delete(f"/api/crm/notas/{nota_id}", headers=headers)
    assert d.status_code == 200

    listing_after = client.get(f"/api/crm/notas?contacto_id={cid}", headers=headers)
    assert not any(n["id"] == nota_id for n in listing_after.json())


# ── Campañas ──────────────────────────────────────────────────────────────────

def test_crear_campania_y_listar() -> None:
    client = _build_client()
    headers = _auth("usuario", "CRM")

    r = client.post("/api/crm/campanias", headers=headers, json={
        "nombre": "Q1 Promo",
        "tipo": "email",
        "estado": "activa",
        "fecha_inicio": "2026-01-01",
        "fecha_fin": "2026-03-31",
    })
    assert r.status_code == 201
    camp_id = r.json()["id"]
    assert r.json()["estado"] == "activa"

    listing = client.get("/api/crm/campanias", headers=headers)
    assert any(c["id"] == camp_id for c in listing.json())


def test_actualizar_estado_campania() -> None:
    client = _build_client()
    headers = _auth("usuario", "CRM")

    r = client.post("/api/crm/campanias", headers=headers, json={"nombre": "Verano 2026"})
    camp_id = r.json()["id"]

    upd = client.put(f"/api/crm/campanias/{camp_id}", headers=headers, json={"estado": "finalizada"})
    assert upd.status_code == 200
    assert upd.json()["estado"] == "finalizada"


def test_asociar_contacto_a_campania() -> None:
    client = _build_client()
    headers = _auth("usuario", "CRM")

    contacto = client.post("/api/crm/contactos", headers=headers, json={"nombre": "Ana Rios"})
    cid = contacto.json()["id"]
    camp = client.post("/api/crm/campanias", headers=headers, json={"nombre": "Camp Test"})
    camp_id = camp.json()["id"]

    r = client.post("/api/crm/campanias/contactos", headers=headers, json={
        "contacto_id": cid,
        "campania_id": camp_id,
        "estado": "pendiente",
    })
    assert r.status_code == 201

    listing = client.get(f"/api/crm/campanias/{camp_id}/contactos", headers=headers)
    assert any(cc["contacto_id"] == cid for cc in listing.json())


# ── Dashboard resumen ─────────────────────────────────────────────────────────

def test_crm_resumen_contadores() -> None:
    client = _build_client()
    headers = _auth("usuario", "CRM")

    r = client.get("/api/crm/resumen", headers=headers)
    assert r.status_code == 200
    data = r.json()
    for key in ("total_contactos", "total_oportunidades", "oportunidades_abiertas",
                "actividades_pendientes", "campanias_activas"):
        assert key in data
        assert isinstance(data[key], int)


def test_resumen_refleja_creaciones() -> None:
    client = _build_client()
    headers = _auth("usuario", "CRM")

    pre = client.get("/api/crm/resumen", headers=headers).json()
    client.post("/api/crm/contactos", headers=headers, json={"nombre": "Nuevo KPI"})
    post = client.get("/api/crm/resumen", headers=headers).json()

    assert post["total_contactos"] == pre["total_contactos"] + 1


# ── Admin omite permiso CRM ───────────────────────────────────────────────────

def test_admin_can_access_crm_without_checkbox() -> None:
    client = _build_client()
    r = client.get("/api/crm/contactos", headers=_auth("administrador"))
    assert r.status_code == 200

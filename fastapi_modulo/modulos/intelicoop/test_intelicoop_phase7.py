from __future__ import annotations

import os
import sys
import types

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient


os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SQLITE_DB_PATH", "/tmp/sipet_intelicoop_phase7.sqlite3")
pytestmark = pytest.mark.filterwarnings("ignore:The 'app' shortcut is now deprecated.*:DeprecationWarning")


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
        "administrador",
        "admin",
        "superadministrador",
        "superadmin",
    }


fake_main.render_backend_page = _fake_render_backend_page
fake_main._get_user_app_access = _fake_get_user_app_access
fake_main.is_admin_or_superadmin = _fake_is_admin_or_superadmin
sys.modules["fastapi_modulo.main"] = fake_main


from fastapi_modulo.db import Base, engine
from fastapi_modulo.modulos.intelicoop.intelicoop import router
from fastapi_modulo.modulos.intelicoop.intelicoop_db_models import (
    IntelicoopCampania,
    IntelicoopContactoCampania,
    IntelicoopCredito,
    IntelicoopCuenta,
    IntelicoopHistorialPago,
    IntelicoopProspecto,
    IntelicoopScoringResult,
    IntelicoopSeguimientoCampania,
    IntelicoopSocio,
    IntelicoopTransaccion,
)


INTELICOOP_TABLES = [
    IntelicoopSocio.__table__,
    IntelicoopCredito.__table__,
    IntelicoopHistorialPago.__table__,
    IntelicoopCuenta.__table__,
    IntelicoopTransaccion.__table__,
    IntelicoopCampania.__table__,
    IntelicoopProspecto.__table__,
    IntelicoopContactoCampania.__table__,
    IntelicoopSeguimientoCampania.__table__,
    IntelicoopScoringResult.__table__,
]


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


def _auth_headers(*access: str, role: str = "usuario") -> dict[str, str]:
    headers = {"x-role": role, "x-user": "intelicoop.test"}
    if access:
        headers["x-app-access"] = ",".join(access)
    return headers


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine, tables=INTELICOOP_TABLES, checkfirst=True)
    Base.metadata.create_all(bind=engine, tables=INTELICOOP_TABLES, checkfirst=True)


def test_intelicoop_html_requires_access() -> None:
    client = _build_client()

    response = client.get("/inicio/intelicoop")

    assert response.status_code == 403
    assert response.json()["detail"] == "Acceso restringido a Intelicoop"


def test_intelicoop_html_renders_with_access() -> None:
    client = _build_client()

    response = client.get("/inicio/intelicoop", headers=_auth_headers("Intelicoop"))

    assert response.status_code == 200
    assert "Intelicoop" in response.text
    assert "intelicoop-root" in response.text


def test_intelicoop_api_blocks_without_access() -> None:
    client = _build_client()

    response = client.get("/api/intelicoop/socios")

    assert response.status_code == 403
    assert response.json()["detail"] == "Acceso restringido a Intelicoop"


def test_intelicoop_core_flow_persists_data_and_scoring() -> None:
    client = _build_client()
    headers = _auth_headers("Intelicoop")

    socio_response = client.post(
        "/api/intelicoop/socios",
        headers=headers,
        json={
            "nombre": "Ana Perez",
            "email": "ana@example.com",
            "telefono": "555-0101",
            "direccion": "Zona 1",
            "segmento": "hormiga",
        },
    )
    assert socio_response.status_code == 201
    socio_id = socio_response.json()["id"]

    credito_response = client.post(
        "/api/intelicoop/creditos",
        headers=headers,
        json={
            "socio_id": socio_id,
            "monto": 1500,
            "plazo": 12,
            "ingreso_mensual": 5000,
            "deuda_actual": 800,
            "antiguedad_meses": 24,
            "estado": "solicitado",
        },
    )
    assert credito_response.status_code == 201
    credito_payload = credito_response.json()
    credito_id = credito_payload["credito"]["id"]
    assert credito_payload["scoring"]["credito_id"] == credito_id
    assert credito_payload["scoring"]["model_version"] == "intelicoop_scoring_v1"

    pago_response = client.post(
        "/api/intelicoop/creditos/pagos",
        headers=headers,
        json={"credito_id": credito_id, "monto": 250},
    )
    assert pago_response.status_code == 201

    detalle_response = client.get(f"/api/intelicoop/creditos/{credito_id}/detalle", headers=headers)
    assert detalle_response.status_code == 200
    detalle = detalle_response.json()
    assert detalle["id"] == credito_id
    assert detalle["resumen_pagos"]["monto_pagado"] == 250.0

    cuenta_response = client.post(
        "/api/intelicoop/ahorros/cuentas",
        headers=headers,
        json={"socio_id": socio_id, "tipo": "ahorro", "saldo": 1000},
    )
    assert cuenta_response.status_code == 201
    cuenta_id = cuenta_response.json()["id"]

    tx_response = client.post(
        "/api/intelicoop/ahorros/transacciones",
        headers=headers,
        json={"cuenta_id": cuenta_id, "tipo": "deposito", "monto": 300},
    )
    assert tx_response.status_code == 201

    campana_response = client.post(
        "/api/intelicoop/campanas",
        headers=headers,
        json={
            "nombre": "Campana Primavera",
            "tipo": "Colocacion",
            "fecha_inicio": "2026-03-01",
            "fecha_fin": "2026-03-31",
            "estado": "activa",
        },
    )
    assert campana_response.status_code == 201

    prospecto_response = client.post(
        "/api/intelicoop/prospectos",
        headers=headers,
        json={
            "nombre": "Carlos Ruiz",
            "telefono": "555-0202",
            "direccion": "Zona 4",
            "fuente": "referido",
            "score_propension": 0.7,
        },
    )
    assert prospecto_response.status_code == 201

    resumen_response = client.get("/api/intelicoop/scoring/resumen", headers=headers)
    assert resumen_response.status_code == 200
    resumen = resumen_response.json()
    assert resumen["total_inferencias"] >= 1

    dashboard_response = client.get("/api/intelicoop/dashboard/resumen", headers=headers)
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["socios"] == 1
    assert dashboard["creditos"] == 1
    assert dashboard["campanas"] == 1
    assert dashboard["prospectos"] == 1
    assert dashboard["scoring_total"] >= 1


def test_admin_can_access_intelicoop_without_checkbox() -> None:
    client = _build_client()

    response = client.get("/api/intelicoop/socios", headers=_auth_headers(role="admin"))

    assert response.status_code == 200
    assert response.json() == []

from __future__ import annotations

import os
import sys
import tempfile
import types
from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


os.environ.setdefault("APP_ENV", "test")
pytestmark = pytest.mark.filterwarnings("ignore:The 'app' shortcut is now deprecated.*:DeprecationWarning")

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DB_FILE = Path(tempfile.gettempdir()) / "brujula_module_tests.sqlite3"
ENGINE = create_engine(f"sqlite:///{DB_FILE}", future=True)
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, future=True)

fake_main = types.ModuleType("fastapi_modulo.main")


def _fake_render_backend_page(request, title="", description="", content="", **_):
    return HTMLResponse(f"<html><head><title>{title}</title></head><body>{content}</body></html>")


def _fake_normalize_tenant_id(value):
    return str(value or "default").strip().lower() or "default"


def _fake_get_current_tenant(request):
    return request.headers.get("x-tenant", "default")


fake_main.render_backend_page = _fake_render_backend_page
fake_main.SessionLocal = SessionLocal
fake_main._normalize_tenant_id = _fake_normalize_tenant_id
fake_main.get_current_tenant = _fake_get_current_tenant
sys.modules["fastapi_modulo.main"] = fake_main

from fastapi_modulo.modulos.brujula.controladores.brujula import router  # noqa: E402
from fastapi_modulo.modulos.brujula.repositorios.override_repository import upsert_override  # noqa: E402
from fastapi_modulo.modulos.brujula.repositorios.tenant_repository import require_tenant_id  # noqa: E402
from fastapi_modulo.modulos.brujula.servicios.analysis_service import (  # noqa: E402
    evaluate_indicator_status,
    parse_meta_rule,
    parse_number_like,
)
from fastapi_modulo.modulos.brujula.servicios.indicator_service import (  # noqa: E402
    initialize_indicator_storage_on_startup,
    merge_indicator_definitions_with_overrides,
)
from fastapi_modulo.modulos.brujula.servicios.projection_adapter import register_projection_adapter  # noqa: E402
from fastapi_modulo.modulos.brujula.servicios.projection_service import (  # noqa: E402
    normalize_indicator_matrix_rows,
    parse_numeric_value,
    get_projection_periods,
)


def setup_function() -> None:
    with ENGINE.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS brujula_indicator_values"))
        conn.execute(text("DROP TABLE IF EXISTS brujula_indicator_definition_overrides"))
    register_projection_adapter()
    initialize_indicator_storage_on_startup()


def _build_client() -> TestClient:
    app = FastAPI()

    @app.middleware("http")
    async def inject_request_context(request: Request, call_next):
        request.state.user_name = "brujula.test"
        request.state.user_role = "admin"
        request.state.tenant_id = request.headers.get("x-tenant", "default")
        return await call_next(request)

    app.include_router(router)
    return TestClient(app)


def test_dashboard_page_loads():
    client = _build_client()
    response = client.get("/brujula")
    assert response.status_code == 200
    assert "Dashboard Ejecutivo" in response.text


def test_indicator_notebook_loads():
    client = _build_client()
    response = client.get("/api/brujula/indicadores/notebook")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert len(payload["data"]["periods"]) >= 4
    assert len(payload["data"]["rows"]) > 0


def test_merge_overrides_applies_by_tenant():
    db = SessionLocal()
    try:
        from fastapi_modulo.modulos.brujula.repositorios.schema import (
            ensure_indicator_table_schema,
            ensure_override_table_schema,
        )

        ensure_indicator_table_schema(db)
        ensure_override_table_schema(db)
        upsert_override(db, "tenant-a", "C2 - Indice de capitalizacion", ">=20.0%", "<10.0%", ">=25.0%")
        db.commit()
        merged = merge_indicator_definitions_with_overrides(db, "tenant-a")
        item = next(current for current in merged if current["nombre"] == "C2 - Indice de capitalizacion")
        assert item["estandar_meta"] == ">=20.0%"
        assert item["semaforo_rojo"] == "<10.0%"
        assert item["semaforo_verde"] == ">=25.0%"
    finally:
        db.close()


def test_normalize_rows_deduplicates_and_limits_periods():
    periods = [{"key": "-1"}, {"key": "0"}]
    rows = normalize_indicator_matrix_rows(
        [
            {"indicador": "C2 - Indice de capitalizacion", "values": {"-1": "10", "0": "12", "x": "99"}},
            {"indicador": "C2 - Indice de capitalizacion", "values": {"-1": "11", "0": "13"}},
            {"indicador": "", "values": {"-1": "1"}},
        ],
        periods,
    )
    assert rows == [
        {
            "indicador": "C2 - Indice de capitalizacion",
            "values": {"-1": "10", "0": "12"},
            "orden": 1,
        }
    ]


def test_parse_numeric_value_handles_percent_and_commas():
    assert parse_numeric_value("1,234.50%") == 1234.5
    assert parse_numeric_value("") is None
    assert parse_number_like("85.0%") == 85.0


def test_evaluate_indicator_status_and_meta_rule():
    assert parse_meta_rule(">=12.0%") == {"operator": ">=", "target": 12.0}
    assert evaluate_indicator_status("13%", ">=12%") == "ok"
    assert evaluate_indicator_status("9%", ">=12%") == "fail"
    assert evaluate_indicator_status("", ">=12%") == "na"
    assert evaluate_indicator_status("13%", "N/A") == "na"


def test_periods_read_through_adapter():
    register_projection_adapter(
        store_loader=lambda: {"primer_anio_proyeccion": "2028", "anios_proyeccion": "2", "ifb_rows_json": ""},
        periods_loader=lambda store: [
            {"key": "-1", "label": "2027"},
            {"key": "0", "label": "2028"},
            {"key": "1", "label": "2029"},
        ],
    )
    periods = get_projection_periods()
    assert periods == [
        {"key": "-1", "label": "2027", "kind": "historico"},
        {"key": "0", "label": "2028", "kind": "proyectado"},
        {"key": "1", "label": "2029", "kind": "proyectado"},
    ]


def test_tenant_id_is_required_and_normalized():
    assert require_tenant_id(" Tenant-A ") == "tenant-a"
    with pytest.raises(ValueError):
        require_tenant_id("   ")


def test_multi_tenant_persistence_is_isolated():
    client = _build_client()

    payload_a = {
        "rows": [
            {
                "indicador": "P2 - Ahorro promedio por socio",
                "values": {"-3": "100", "-2": "110", "-1": "120", "0": "130"},
            }
        ]
    }
    payload_b = {
        "rows": [
            {
                "indicador": "P2 - Ahorro promedio por socio",
                "values": {"-3": "200", "-2": "210", "-1": "220", "0": "230"},
            }
        ]
    }

    save_a = client.post("/api/brujula/indicadores/notebook", json=payload_a, headers={"x-tenant": "tenant-a"})
    save_b = client.post("/api/brujula/indicadores/notebook", json=payload_b, headers={"x-tenant": "tenant-b"})
    assert save_a.status_code == 200
    assert save_b.status_code == 200

    get_a = client.get("/api/brujula/indicadores/notebook", headers={"x-tenant": "tenant-a"}).json()
    get_b = client.get("/api/brujula/indicadores/notebook", headers={"x-tenant": "tenant-b"}).json()

    row_a = next(item for item in get_a["data"]["rows"] if item["indicador"] == "P2 - Ahorro promedio por socio")
    row_b = next(item for item in get_b["data"]["rows"] if item["indicador"] == "P2 - Ahorro promedio por socio")
    assert row_a["values"]["0"] == "130"
    assert row_b["values"]["0"] == "230"

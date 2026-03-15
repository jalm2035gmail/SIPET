from __future__ import annotations

import os
import sys
import types

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SQLITE_DB_PATH", "/tmp/sipet_activo_fijo_phase.sqlite3")
pytestmark = pytest.mark.filterwarnings("ignore:The 'app' shortcut is now deprecated.*:DeprecationWarning")

# ── Stub fastapi_modulo.main ──────────────────────────────────────────────────

fake_main = types.ModuleType("fastapi_modulo.main")


def _fake_render_backend_page(request, title="", description="", content="", **_):
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

# ── Imports del módulo ────────────────────────────────────────────────────────

from fastapi_modulo.db import MAIN, engine  # noqa: E402
from fastapi_modulo.modulos.activo_fijo.models import (  # noqa: E402
    AfActivo,
    AfAsignacion,
    AfBaja,
    AfDepreciacion,
    AfMantenimiento,
)
from fastapi_modulo.modulos.activo_fijo.router import router  # noqa: E402

_AF_TABLES = [
    AfActivo.__table__,
    AfDepreciacion.__table__,
    AfAsignacion.__table__,
    AfMantenimiento.__table__,
    AfBaja.__table__,
]

# ── Fixtures ──────────────────────────────────────────────────────────────────

def _build_client() -> TestClient:
    app = FastAPI()

    @app.middleware("http")
    async def inject_session(request: Request, call_next):
        request.state.user_name = request.headers.get("x-user", "af.tester")
        request.state.user_role = request.headers.get("x-role", "usuario")
        request.state.tenant_id = "test"
        return await call_next(request)

    app.include_router(router)
    return TestClient(app)


def _auth(role: str = "usuario", *access: str) -> dict:
    h = {"x-role": role, "x-user": "af.test"}
    if access:
        h["x-app-access"] = ",".join(access)
    return h


def setup_function() -> None:
    MAIN.metadata.drop_all(bind=engine, tables=_AF_TABLES, checkfirst=True)
    MAIN.metadata.create_all(bind=engine, tables=_AF_TABLES, checkfirst=True)


# ── Permisos ──────────────────────────────────────────────────────────────────

def test_acceso_denegado_sin_permiso():
    c = _build_client()
    r = c.get("/api/activo-fijo/activos", headers=_auth("usuario"))
    assert r.status_code == 403


def test_acceso_permitido_admin():
    c = _build_client()
    r = c.get("/api/activo-fijo/activos", headers=_auth("admin"))
    assert r.status_code == 200


def test_acceso_permitido_con_app_access():
    c = _build_client()
    r = c.get("/api/activo-fijo/activos", headers=_auth("usuario", "ActivoFijo"))
    assert r.status_code == 200


# ── Activos CRUD ──────────────────────────────────────────────────────────────

def _activo_payload(**overrides):
    MAIN = {
        "codigo": "AF-001",
        "nombre": "Computadora Dell",
        "categoria": "Equipo de cómputo",
        "marca": "Dell",
        "modelo": "Latitude 5520",
        "numero_serie": "SN-12345",
        "proveedor": "TechStore",
        "fecha_adquisicion": "2024-01-15",
        "valor_adquisicion": 25000.00,
        "valor_residual": 2500.00,
        "vida_util_meses": 36,
        "metodo_depreciacion": "linea_recta",
        "ubicacion": "Oficina principal",
        "responsable": "Juan García",
    }
    MAIN.update(overrides)
    return MAIN


def test_crear_activo():
    c = _build_client()
    h = _auth("admin")
    r = c.post("/api/activo-fijo/activos", json=_activo_payload(), headers=h)
    assert r.status_code == 201
    d = r.json()
    assert d["nombre"] == "Computadora Dell"
    assert d["estado"] == "activo"
    assert d["codigo"] == "AF-001"
    # valor_libro debe inicializarse = valor_adquisicion
    assert float(d["valor_libro"]) == 25000.00


def test_listar_activos():
    c = _build_client()
    h = _auth("admin")
    c.post("/api/activo-fijo/activos", json=_activo_payload(), headers=h)
    r = c.get("/api/activo-fijo/activos", headers=h)
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_get_activo():
    c = _build_client()
    h = _auth("admin")
    created = c.post("/api/activo-fijo/activos", json=_activo_payload(), headers=h).json()
    r = c.get(f"/api/activo-fijo/activos/{created['id']}", headers=h)
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_get_activo_no_existe():
    c = _build_client()
    r = c.get("/api/activo-fijo/activos/9999", headers=_auth("admin"))
    assert r.status_code == 404


def test_actualizar_activo():
    c = _build_client()
    h = _auth("admin")
    created = c.post("/api/activo-fijo/activos", json=_activo_payload(), headers=h).json()
    r = c.put(f"/api/activo-fijo/activos/{created['id']}",
              json={"nombre": "Laptop Dell Actualizada", "ubicacion": "Sala de juntas"},
              headers=h)
    assert r.status_code == 200
    assert r.json()["nombre"] == "Laptop Dell Actualizada"


def test_eliminar_activo():
    c = _build_client()
    h = _auth("admin")
    created = c.post("/api/activo-fijo/activos", json=_activo_payload(), headers=h).json()
    r = c.delete(f"/api/activo-fijo/activos/{created['id']}", headers=h)
    assert r.status_code == 204
    r2 = c.get(f"/api/activo-fijo/activos/{created['id']}", headers=h)
    assert r2.status_code == 404


def test_codigo_duplicado():
    c = _build_client()
    h = _auth("admin")
    c.post("/api/activo-fijo/activos", json=_activo_payload(), headers=h)
    r = c.post("/api/activo-fijo/activos", json=_activo_payload(nombre="Otro"), headers=h)
    assert r.status_code == 409


def test_filtro_estado_activos():
    c = _build_client()
    h = _auth("admin")
    c.post("/api/activo-fijo/activos", json=_activo_payload(), headers=h)
    r = c.get("/api/activo-fijo/activos?estado=activo", headers=h)
    assert r.status_code == 200
    for a in r.json():
        assert a["estado"] == "activo"


# ── Depreciación ──────────────────────────────────────────────────────────────

def _create_activo(c, h, **overrides):
    return c.post("/api/activo-fijo/activos", json=_activo_payload(**overrides), headers=h).json()


def test_depreciar_linea_recta():
    c = _build_client()
    h = _auth("admin")
    a = _create_activo(c, h)
    r = c.post(f"/api/activo-fijo/activos/{a['id']}/depreciar",
               json={"periodo": "2025-01"}, headers=h)
    assert r.status_code == 201
    d = r.json()
    assert d["activo_id"] == a["id"]
    assert d["periodo"] == "2025-01"
    # linea_recta: (25000 - 2500) / 36 = 625.00
    assert float(d["valor_depreciacion"]) == pytest.approx(625.00, 0.01)
    # valor_libro del activo debe actualizarse
    a_upd = c.get(f"/api/activo-fijo/activos/{a['id']}", headers=h).json()
    assert float(a_upd["valor_libro"]) == pytest.approx(24375.00, 0.01)


def test_depreciar_saldo_decreciente():
    c = _build_client()
    h = _auth("admin")
    a = _create_activo(c, h, codigo="AF-SD-001", metodo_depreciacion="saldo_decreciente")
    r = c.post(f"/api/activo-fijo/activos/{a['id']}/depreciar",
               json={"periodo": "2025-01", "tasa_saldo_decreciente": 0.20},
               headers=h)
    assert r.status_code == 201
    d = r.json()
    # dep = 25000 * 0.20 / 12 = 416.67
    assert float(d["valor_depreciacion"]) == pytest.approx(416.67, 0.01)


def test_depreciar_periodo_duplicado():
    c = _build_client()
    h = _auth("admin")
    a = _create_activo(c, h, codigo="AF-DUP-001")
    c.post(f"/api/activo-fijo/activos/{a['id']}/depreciar", json={"periodo": "2025-02"}, headers=h)
    r = c.post(f"/api/activo-fijo/activos/{a['id']}/depreciar", json={"periodo": "2025-02"}, headers=h)
    assert r.status_code in (400, 409)


def test_listar_depreciaciones():
    c = _build_client()
    h = _auth("admin")
    a = _create_activo(c, h, codigo="AF-LIST-DEP")
    c.post(f"/api/activo-fijo/activos/{a['id']}/depreciar", json={"periodo": "2025-03"}, headers=h)
    r = c.get(f"/api/activo-fijo/depreciaciones?activo_id={a['id']}", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_eliminar_depreciacion_revierte_valor_libro():
    c = _build_client()
    h = _auth("admin")
    a = _create_activo(c, h, codigo="AF-REV-001")
    dep = c.post(f"/api/activo-fijo/activos/{a['id']}/depreciar",
                 json={"periodo": "2025-04"}, headers=h).json()
    r = c.delete(f"/api/activo-fijo/depreciaciones/{dep['id']}", headers=h)
    assert r.status_code == 204
    # valor_libro debe haberse restaurado
    a_upd = c.get(f"/api/activo-fijo/activos/{a['id']}", headers=h).json()
    assert float(a_upd["valor_libro"]) == pytest.approx(25000.00, 0.01)


# ── Asignaciones ──────────────────────────────────────────────────────────────

def test_crear_asignacion():
    c = _build_client()
    h = _auth("admin")
    a = _create_activo(c, h, codigo="AF-ASIG-001")
    r = c.post("/api/activo-fijo/asignaciones",
               json={"activo_id": a["id"], "empleado": "María López",
                     "area": "Contabilidad", "fecha_asignacion": "2025-03-01"},
               headers=h)
    assert r.status_code == 201
    d = r.json()
    assert d["empleado"] == "María López"
    assert d["estado"] == "vigente"
    # activo should be marked asignado
    a_upd = c.get(f"/api/activo-fijo/activos/{a['id']}", headers=h).json()
    assert a_upd["estado"] == "asignado"


def test_devolver_activo_libera_estado():
    c = _build_client()
    h = _auth("admin")
    a = _create_activo(c, h, codigo="AF-DEV-001")
    asig = c.post("/api/activo-fijo/asignaciones",
                  json={"activo_id": a["id"], "empleado": "Pedro",
                        "fecha_asignacion": "2025-03-01"},
                  headers=h).json()
    r = c.put(f"/api/activo-fijo/asignaciones/{asig['id']}",
              json={"estado": "devuelto", "fecha_devolucion": "2025-04-01"},
              headers=h)
    assert r.status_code == 200
    a_upd = c.get(f"/api/activo-fijo/activos/{a['id']}", headers=h).json()
    assert a_upd["estado"] == "activo"


def test_eliminar_asignacion():
    c = _build_client()
    h = _auth("admin")
    a = _create_activo(c, h, codigo="AF-DELAG-001")
    asig = c.post("/api/activo-fijo/asignaciones",
                  json={"activo_id": a["id"], "empleado": "Ana",
                        "fecha_asignacion": "2025-03-01"},
                  headers=h).json()
    r = c.delete(f"/api/activo-fijo/asignaciones/{asig['id']}", headers=h)
    assert r.status_code == 204


# ── Mantenimiento ─────────────────────────────────────────────────────────────

def test_crear_mantenimiento():
    c = _build_client()
    h = _auth("admin")
    a = _create_activo(c, h, codigo="AF-MANT-001")
    r = c.post("/api/activo-fijo/mantenimientos",
               json={"activo_id": a["id"], "tipo": "preventivo",
                     "descripcion": "Limpieza de pantalla", "estado": "pendiente",
                     "fecha_inicio": "2025-05-01"},
               headers=h)
    assert r.status_code == 201
    d = r.json()
    assert d["tipo"] == "preventivo"
    assert d["estado"] == "pendiente"


def test_mantenimiento_en_proceso_cambia_estado_activo():
    c = _build_client()
    h = _auth("admin")
    a = _create_activo(c, h, codigo="AF-MANT-EP")
    r = c.post("/api/activo-fijo/mantenimientos",
               json={"activo_id": a["id"], "tipo": "correctivo",
                     "descripcion": "Reparación teclado", "estado": "en_proceso",
                     "fecha_inicio": "2025-05-02"},
               headers=h)
    assert r.status_code == 201
    a_upd = c.get(f"/api/activo-fijo/activos/{a['id']}", headers=h).json()
    assert a_upd["estado"] == "en_mantenimiento"


def test_mantenimiento_completado_restaura_activo():
    c = _build_client()
    h = _auth("admin")
    a = _create_activo(c, h, codigo="AF-MANT-COMP")
    mant = c.post("/api/activo-fijo/mantenimientos",
                  json={"activo_id": a["id"], "tipo": "reparacion",
                        "descripcion": "Cambio de disco", "estado": "en_proceso",
                        "fecha_inicio": "2025-05-03"},
                  headers=h).json()
    r = c.put(f"/api/activo-fijo/mantenimientos/{mant['id']}",
              json={"estado": "completado", "fecha_fin": "2025-05-10"},
              headers=h)
    assert r.status_code == 200
    a_upd = c.get(f"/api/activo-fijo/activos/{a['id']}", headers=h).json()
    assert a_upd["estado"] == "activo"


def test_eliminar_mantenimiento():
    c = _build_client()
    h = _auth("admin")
    a = _create_activo(c, h, codigo="AF-MANT-DEL")
    mant = c.post("/api/activo-fijo/mantenimientos",
                  json={"activo_id": a["id"], "tipo": "preventivo",
                        "descripcion": "Rutina", "estado": "pendiente",
                        "fecha_inicio": "2025-05-01"},
                  headers=h).json()
    r = c.delete(f"/api/activo-fijo/mantenimientos/{mant['id']}", headers=h)
    assert r.status_code == 204


# ── Bajas ─────────────────────────────────────────────────────────────────────

def test_dar_de_baja_activo():
    c = _build_client()
    h = _auth("admin")
    a = _create_activo(c, h, codigo="AF-BAJA-001")
    r = c.post("/api/activo-fijo/bajas",
               json={"activo_id": a["id"], "motivo": "obsolescencia",
                     "fecha_baja": "2025-06-01", "valor_residual_real": 1000.00},
               headers=h)
    assert r.status_code == 201
    d = r.json()
    assert d["motivo"] == "obsolescencia"
    # activo must be dado_de_baja
    a_upd = c.get(f"/api/activo-fijo/activos/{a['id']}", headers=h).json()
    assert a_upd["estado"] == "dado_de_baja"


def test_baja_duplicada():
    c = _build_client()
    h = _auth("admin")
    a = _create_activo(c, h, codigo="AF-BAJA-DUP")
    payload = {"activo_id": a["id"], "motivo": "venta", "fecha_baja": "2025-06-01"}
    c.post("/api/activo-fijo/bajas", json=payload, headers=h)
    r = c.post("/api/activo-fijo/bajas", json=payload, headers=h)
    assert r.status_code == 409


def test_activo_dado_baja_no_deprecia():
    c = _build_client()
    h = _auth("admin")
    a = _create_activo(c, h, codigo="AF-BAJA-DEP")
    c.post("/api/activo-fijo/bajas",
           json={"activo_id": a["id"], "motivo": "dano", "fecha_baja": "2025-06-01"},
           headers=h)
    r = c.post(f"/api/activo-fijo/activos/{a['id']}/depreciar",
               json={"periodo": "2025-06"}, headers=h)
    assert r.status_code == 400


def test_reactivar_baja():
    c = _build_client()
    h = _auth("admin")
    a = _create_activo(c, h, codigo="AF-REAC-001")
    baja = c.post("/api/activo-fijo/bajas",
                  json={"activo_id": a["id"], "motivo": "donacion",
                        "fecha_baja": "2025-06-01"},
                  headers=h).json()
    r = c.delete(f"/api/activo-fijo/bajas/{baja['id']}", headers=h)
    assert r.status_code == 204
    a_upd = c.get(f"/api/activo-fijo/activos/{a['id']}", headers=h).json()
    assert a_upd["estado"] == "activo"


def test_listar_bajas():
    c = _build_client()
    h = _auth("admin")
    a = _create_activo(c, h, codigo="AF-LIST-BAJA")
    c.post("/api/activo-fijo/bajas",
           json={"activo_id": a["id"], "motivo": "robo", "fecha_baja": "2025-06-01"},
           headers=h)
    r = c.get("/api/activo-fijo/bajas", headers=h)
    assert r.status_code == 200
    assert len(r.json()) >= 1


# ── KPIs / Resumen ────────────────────────────────────────────────────────────

def test_resumen_kpis():
    c = _build_client()
    h = _auth("admin")
    a = _create_activo(c, h, codigo="AF-KPI-001")
    r = c.get("/api/activo-fijo/resumen", headers=h)
    assert r.status_code == 200
    d = r.json()
    assert "total_activos" in d
    assert "valor_libro_total" in d
    assert "depreciacion_acumulada" in d
    assert d["total_activos"] >= 1


# ── Vista HTML ────────────────────────────────────────────────────────────────

def test_pagina_html():
    c = _build_client()
    r = c.get("/activo-fijo", headers=_auth("admin"))
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")


def test_js_asset():
    c = _build_client()
    r = c.get("/api/activo-fijo/assets/activo_fijo.js", headers=_auth("admin"))
    assert r.status_code == 200
    assert "javascript" in r.headers.get("content-type", "")

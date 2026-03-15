from __future__ import annotations

import os
import sys
import tempfile
import types
from datetime import date
from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


os.environ.setdefault("APP_ENV", "test")
pytestmark = pytest.mark.filterwarnings("ignore:The 'app' shortcut is now deprecated.*:DeprecationWarning")

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DB_FILE = Path(tempfile.gettempdir()) / "cartera_prestamos_module_tests.sqlite3"
ENGINE = create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False}, future=True)
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, future=True)

fake_db = types.ModuleType("fastapi_modulo.db")
fake_db.engine = ENGINE
fake_db.SessionLocal = SessionLocal
fake_db.MAIN = declarative_base()
sys.modules["fastapi_modulo.db"] = fake_db

from fastapi_modulo.modulos.cartera_prestamos.controladores.cartera_prestamos import router  # noqa: E402
from fastapi_modulo.modulos.cartera_prestamos.modelos.db_models import (  # noqa: E402
    CpCastigoCredito,
    CpCliente,
    CpCredito,
    CpGestionCobranza,
    CpIndicadorCartera,
    CpMoraCredito,
    CpPromesaPago,
    CpReestructuraCredito,
    CpSaldoCredito,
)
from fastapi_modulo.modulos.cartera_prestamos.servicios.cartera_service import (  # noqa: E402
    actualizar_mora_credito,
    crear_cliente,
    crear_credito,
)
from fastapi_modulo.modulos.cartera_prestamos.servicios.recuperacion_service import (  # noqa: E402
    actualizar_promesa_pago,
    registrar_gestion_cobranza,
    registrar_promesa_pago,
)


ALL_TABLES = [
    CpCliente.__table__,
    CpCredito.__table__,
    CpSaldoCredito.__table__,
    CpMoraCredito.__table__,
    CpPromesaPago.__table__,
    CpGestionCobranza.__table__,
    CpCastigoCredito.__table__,
    CpReestructuraCredito.__table__,
    CpIndicadorCartera.__table__,
]


@pytest.fixture(autouse=True)
def reset_db() -> None:
    fake_db.MAIN.metadata.drop_all(bind=ENGINE, tables=ALL_TABLES)
    fake_db.MAIN.metadata.create_all(bind=ENGINE, tables=ALL_TABLES)


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()

    @app.middleware("http")
    async def inject_context(request: Request, call_next):
        request.state.user_name = request.headers.get("x-user-name", "cartera.test")
        request.state.user_role = request.headers.get("x-user-role", "direccion_general")
        return await call_next(request)

    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def seeded_data():
    cliente = crear_cliente(
        {
            "codigo": "CLI-001",
            "nombre_completo": "Ana Morales",
            "identificacion": "ID-001",
            "segmento": "microcredito",
            "nivel_riesgo": "medio",
        }
    )
    credito_a = crear_credito(
        {
            "cliente_id": cliente.id,
            "numero_credito": "CR-001",
            "producto": "Consumo",
            "fecha_desembolso": "2026-03-01",
            "fecha_vencimiento": "2026-03-05",
            "monto_original": "100000",
            "tasa_interes": "0.18",
            "saldo_capital": "82000",
            "etapa_colocacion": "analisis",
            "score_riesgo": "72",
            "documentacion_completa": False,
            "es_renovacion": True,
            "oficial": "Asesor Centro",
            "sucursal": "Centro",
        }
    )
    credito_b = crear_credito(
        {
            "cliente_id": cliente.id,
            "numero_credito": "CR-002",
            "producto": "Microempresa",
            "fecha_desembolso": "2026-03-03",
            "fecha_vencimiento": "2026-03-20",
            "monto_original": "64000",
            "tasa_interes": "0.16",
            "saldo_capital": "41000",
            "etapa_colocacion": "formalizacion",
            "score_riesgo": "48",
            "documentacion_completa": True,
            "es_renovacion": False,
            "oficial": "Asesor Norte",
            "sucursal": "Norte",
        }
    )

    actualizar_mora_credito(credito_a.id, fecha_exigible=date(2026, 2, 1), saldo_capital=82000)
    actualizar_mora_credito(credito_b.id, fecha_exigible=date(2026, 3, 10), saldo_capital=41000)

    promesa = registrar_promesa_pago(
        {
            "credito_id": credito_a.id,
            "fecha_compromiso": "2026-03-18",
            "monto_comprometido": "15000",
            "observaciones": "Compromiso inicial",
        }
    )
    actualizar_promesa_pago(
        promesa.id,
        {
            "monto_cumplido": "7500",
            "estado": "cumplida",
            "observaciones": "Pago parcial aplicado",
        },
    )
    registrar_promesa_pago(
        {
            "credito_id": credito_b.id,
            "fecha_compromiso": "2026-03-22",
            "monto_comprometido": "9000",
            "observaciones": "Seguimiento semanal",
        }
    )

    registrar_gestion_cobranza(
        {
            "credito_id": credito_a.id,
            "tipo_gestion": "llamada",
            "resultado": "promesa_pago",
            "responsable": "Gestor 1",
            "comentario": "Cliente responde",
        }
    )
    registrar_gestion_cobranza(
        {
            "credito_id": credito_b.id,
            "tipo_gestion": "visita",
            "resultado": "sin_contacto",
            "responsable": "Gestor 2",
            "comentario": "No localizado",
            "fecha_proxima_accion": "2026-03-21",
        }
    )

    db = SessionLocal()
    try:
        db.add(CpCastigoCredito(credito_id=credito_a.id, monto_castigado=5000, motivo="Prueba"))
        db.commit()
    finally:
        db.close()

    return {
        "cliente": cliente,
        "credito_a": credito_a,
        "credito_b": credito_b,
    }

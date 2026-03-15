from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import event


ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import fastapi_modulo.db as core_db
from fastapi_modulo.modulos.control_interno.controladores import dependencies
from fastapi_modulo.modulos.control_interno.modelos.control import ControlInterno
from fastapi_modulo.modulos.control_interno.modelos.evidencia import Evidencia
from fastapi_modulo.modulos.control_interno.modelos.hallazgo import AccionCorrectiva, Hallazgo
from fastapi_modulo.modulos.control_interno.modelos.programa import ProgramaActividad, ProgramaAnual
from fastapi_modulo.modulos.control_interno.repositorios.base import set_current_tenant
from fastapi_modulo.modulos.control_interno.servicios import evidencia_service


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    db_path = tmp_path / "control_interno_test.db"
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(core_db, "DATAMAIN_URL", f"sqlite:///{db_path}")
    core_db.dispose_engine_for_host()
    core_db._ENGINE_CACHE.clear()
    core_db._SESSION_FACTORY_CACHE.clear()

    engine = core_db.get_current_engine()
    event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    core_db.MAIN.metadata.create_all(bind=engine)

    monkeypatch.setattr(evidencia_service, "UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr(dependencies, "UPLOAD_DIR", str(upload_dir))
    set_current_tenant("tenant-test")

    yield

    event.remove(engine, "connect", _enable_sqlite_foreign_keys)
    core_db.dispose_engine_for_host()


@pytest.fixture
def models():
    return {
        "control": ControlInterno,
        "programa": ProgramaAnual,
        "actividad": ProgramaActividad,
        "evidencia": Evidencia,
        "hallazgo": Hallazgo,
        "accion": AccionCorrectiva,
    }

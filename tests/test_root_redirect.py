import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("SIPET_DATA_DIR", "/tmp/sipet_test_data")
os.environ.setdefault("SQLITE_DB_PATH", "/tmp/sipet_test_data/strategic_planning_test_root_redirect.db")
os.makedirs("/tmp/sipet_test_data", exist_ok=True)

from fastapi_modulo.main import app


client = TestClient(app)


def test_root_redirects_to_backend_inicio() -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 308
    assert response.headers["location"] == "/backend/inicio"

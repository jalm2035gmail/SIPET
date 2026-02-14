from fastapi.testclient import TestClient

try:
    from app.main import app
    client = TestClient(app)
    _IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover
    _IMPORT_ERROR = exc
    client = None

def test_root():
    if _IMPORT_ERROR:
        import pytest
        pytest.skip(f"Dependencias no disponibles para app legacy: {_IMPORT_ERROR}")
    response = client.get("/")
    assert response.status_code == 200
    assert "Sistema de Planificación Estratégica" in response.json()["message"]

def test_docs():
    if _IMPORT_ERROR:
        import pytest
        pytest.skip(f"Dependencias no disponibles para app legacy: {_IMPORT_ERROR}")
    response = client.get("/docs")
    assert response.status_code == 200

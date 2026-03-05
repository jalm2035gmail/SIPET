import secrets
import sys
import os
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("SIPET_DATA_DIR", "/tmp/sipet_test_data")
os.environ.setdefault("SQLITE_DB_PATH", "/tmp/sipet_test_data/strategic_planning_test_ia_audit.db")
os.makedirs("/tmp/sipet_test_data", exist_ok=True)

from fastapi_modulo.main import AUTH_COOKIE_NAME, _build_session_cookie, app
from fastapi_modulo.db import IAInteraction, SessionLocal


client = TestClient(app)


def _auth_cookies(role: str = "superadministrador", username: str = "audit_test_admin"):
    token = _build_session_cookie(username, role, "default")
    return {
        AUTH_COOKIE_NAME: token,
        "user_role": role,
        "user_name": username,
    }


def _insert_interaction(username: str, status: str = "success", tokens_in: int = 10, tokens_out: int = 12, cost: str = "0.001"):
    db = SessionLocal()
    try:
        IAInteraction.__table__.create(bind=db.get_bind(), checkfirst=True)
        row = IAInteraction(
            created_at=datetime.utcnow(),
            user_id=None,
            username=username,
            feature_key="audit_test",
            input_payload="input de prueba",
            output_payload="output de prueba",
            model_name="test-model",
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            estimated_cost=cost,
            status=status,
            error_message="" if status != "error" else "error de prueba",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return int(row.id or 0)
    finally:
        db.close()


def test_ia_audit_feed_endpoint_ok():
    cookies = _auth_cookies()
    response = client.get("/api/ia/audit/feed?limit=20", cookies=cookies)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload.get("success") is True
    assert isinstance(payload.get("data"), list)


def test_ia_audit_feed_contains_recent_interaction():
    username = f"audit_user_{secrets.token_hex(4)}"
    _insert_interaction(username=username, status="success", tokens_in=22, tokens_out=33, cost="0.004")
    cookies = _auth_cookies(role="administrador", username=username)
    response = client.get("/api/ia/audit/feed?limit=50", cookies=cookies)
    assert response.status_code == 200, response.text
    payload = response.json()
    rows = payload.get("data", [])
    assert isinstance(rows, list)
    assert any((row.get("source") == "interaction" and row.get("username") == username and row.get("feature_key") == "audit_test") for row in rows)


def test_ia_audit_summary_counts_operations():
    username = f"audit_summary_{secrets.token_hex(4)}"
    _insert_interaction(username=username, status="success", tokens_in=5, tokens_out=7, cost="0.001")
    _insert_interaction(username=username, status="error", tokens_in=3, tokens_out=2, cost="0.000")
    cookies = _auth_cookies(role="administrador", username=username)
    response = client.get("/api/ia/audit/summary?days=7", cookies=cookies)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload.get("success") is True
    data = payload.get("data", {})
    assert int(data.get("operations_total", 0)) >= 2
    assert int(data.get("operations_error", 0)) >= 1
    assert int(data.get("tokens_total", 0)) >= 17

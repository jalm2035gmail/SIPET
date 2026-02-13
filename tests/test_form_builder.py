import secrets
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import fastapi_modulo.main as main_module
from fastapi_modulo.main import AUTH_COOKIE_NAME, _build_session_cookie, app


client = TestClient(app)


def _auth_cookies(role: str = "superadministrador", username: str = "test_superadmin"):
    token = _build_session_cookie(username, role)
    return {
        AUTH_COOKIE_NAME: token,
        "user_role": role,
        "user_name": username,
    }


def test_create_form():
    slug = f"contact-{secrets.token_hex(4)}"
    form_data = {
        "name": "Contact Form",
        "slug": slug,
        "description": "Formulario de contacto",
        "is_active": True,
        "fields": [
            {
                "field_type": "text",
                "label": "Name",
                "name": "name",
                "is_required": True,
                "order": 1,
            },
            {
                "field_type": "email",
                "label": "Email",
                "name": "email",
                "is_required": True,
                "validation_rules": {
                    "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
                },
                "order": 2,
            },
        ],
    }

    response = client.post("/api/admin/forms", json=form_data, cookies=_auth_cookies())
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["name"] == "Contact Form"
    assert payload["slug"] == slug
    assert isinstance(payload.get("id"), int)



def test_submit_form():
    slug = f"contact-submit-{secrets.token_hex(4)}"
    create_payload = {
        "name": "Contact Submit",
        "slug": slug,
        "description": "Formulario para probar envio",
        "is_active": True,
        "fields": [
            {
                "field_type": "text",
                "label": "Name",
                "name": "name",
                "is_required": True,
                "order": 1,
            },
            {
                "field_type": "email",
                "label": "Email",
                "name": "email",
                "is_required": True,
                "validation_rules": {
                    "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
                },
                "order": 2,
            },
        ],
    }

    create_response = client.post("/api/admin/forms", json=create_payload, cookies=_auth_cookies())
    assert create_response.status_code == 200, create_response.text

    submit_data = {
        "name": "John Doe",
        "email": "john.doe@example.com",
    }
    response = client.post(f"/forms/api/{slug}/submit", data=submit_data, cookies=_auth_cookies())
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload.get("success") is True
    assert isinstance(payload.get("submission_id"), int)


def test_conditional_logic_show_hide_required():
    slug = f"conditional-{secrets.token_hex(4)}"
    create_payload = {
        "name": "Conditional Form",
        "slug": slug,
        "description": "Prueba de logica condicional",
        "is_active": True,
        "fields": [
            {
                "field_type": "select",
                "label": "Tipo",
                "name": "tipo",
                "is_required": True,
                "options": [{"label": "Linea", "value": "linea"}, {"label": "Staff", "value": "staff"}],
                "order": 1,
            },
            {
                "field_type": "text",
                "label": "Codigo staff",
                "name": "codigo_staff",
                "is_required": True,
                "conditional_logic": {
                    "field": "tipo",
                    "operator": "equals",
                    "value": "staff",
                },
                "order": 2,
            },
        ],
    }
    create_response = client.post("/api/admin/forms", json=create_payload, cookies=_auth_cookies())
    assert create_response.status_code == 200, create_response.text

    # Cuando no cumple la condicion, el campo condicional no debe ser requerido.
    res_hidden = client.post(
        f"/forms/api/{slug}/submit",
        data={"tipo": "linea"},
        cookies=_auth_cookies(),
    )
    assert res_hidden.status_code == 200, res_hidden.text
    assert res_hidden.json().get("success") is True

    # Cuando cumple la condicion y falta el campo, debe fallar.
    res_visible_missing = client.post(
        f"/forms/api/{slug}/submit",
        data={"tipo": "staff"},
        cookies=_auth_cookies(),
    )
    assert res_visible_missing.status_code == 422, res_visible_missing.text


def test_export_submissions_csv():
    slug = f"export-{secrets.token_hex(4)}"
    create_payload = {
        "name": "Export Form",
        "slug": slug,
        "description": "Prueba de exportacion",
        "is_active": True,
        "fields": [
            {
                "field_type": "text",
                "label": "Nombre",
                "name": "nombre",
                "is_required": True,
                "order": 1,
            },
            {
                "field_type": "email",
                "label": "Correo",
                "name": "correo",
                "is_required": True,
                "order": 2,
            },
        ],
    }
    create_response = client.post("/api/admin/forms", json=create_payload, cookies=_auth_cookies())
    assert create_response.status_code == 200, create_response.text
    form_id = create_response.json()["id"]

    submit_response = client.post(
        f"/forms/api/{slug}/submit",
        data={"nombre": "Juan", "correo": "juan@example.com"},
        cookies=_auth_cookies(),
    )
    assert submit_response.status_code == 200, submit_response.text

    export_response = client.get(
        f"/api/admin/forms/{form_id}/submissions/export/csv",
        cookies=_auth_cookies(),
    )
    assert export_response.status_code == 200, export_response.text
    assert "text/csv" in export_response.headers.get("content-type", "")
    content = export_response.text
    assert "submission_id" in content
    assert "nombre" in content
    assert "correo" in content
    assert "Juan" in content


def test_webhook_triggered_on_submit(monkeypatch):
    captured = []

    class FakeResponse:
        def __init__(self, status_code=200):
            self.status_code = status_code

    def fake_request(method, url, **kwargs):
        captured.append({"method": method, "url": url, "kwargs": kwargs})
        return FakeResponse(200)

    monkeypatch.setattr(main_module.httpx, "request", fake_request)

    slug = f"webhook-{secrets.token_hex(4)}"
    create_payload = {
        "name": "Webhook Form",
        "slug": slug,
        "description": "Prueba de webhooks",
        "is_active": True,
        "config": {
            "notifications": {
                "webhooks": [
                    {
                        "url": "https://example.test/hook",
                        "method": "POST",
                    }
                ]
            }
        },
        "fields": [
            {
                "field_type": "text",
                "label": "Nombre",
                "name": "nombre",
                "is_required": True,
                "order": 1,
            }
        ],
    }
    create_response = client.post("/api/admin/forms", json=create_payload, cookies=_auth_cookies())
    assert create_response.status_code == 200, create_response.text

    submit_response = client.post(
        f"/forms/api/{slug}/submit",
        data={"nombre": "Ana"},
        cookies=_auth_cookies(),
    )
    assert submit_response.status_code == 200, submit_response.text
    response_json = submit_response.json()
    assert response_json.get("success") is True
    assert response_json.get("notification", {}).get("webhooks", {}).get("attempted") == 1
    assert len(captured) == 1
    assert captured[0]["url"] == "https://example.test/hook"


def test_multi_checkbox_and_likert_submit():
    slug = f"survey-{secrets.token_hex(4)}"
    create_payload = {
        "name": "Survey Form",
        "slug": slug,
        "description": "Prueba de checkboxes y likert",
        "is_active": True,
        "fields": [
            {
                "field_type": "checkboxes",
                "label": "Requisitos",
                "name": "requisitos",
                "is_required": True,
                "options": [
                    {"label": "INE", "value": "ine"},
                    {"label": "Comprobante", "value": "comprobante"},
                    {"label": "Solicitud", "value": "solicitud"},
                ],
                "order": 1,
            },
            {
                "field_type": "likert",
                "label": "Evaluacion",
                "name": "evaluacion",
                "is_required": True,
                "options": [
                    {"label": "1", "value": "1"},
                    {"label": "2", "value": "2"},
                    {"label": "3", "value": "3"},
                    {"label": "4", "value": "4"},
                    {"label": "5", "value": "5"},
                ],
                "order": 2,
            },
        ],
    }
    create_response = client.post("/api/admin/forms", json=create_payload, cookies=_auth_cookies())
    assert create_response.status_code == 200, create_response.text

    submit_response = client.post(
        f"/forms/api/{slug}/submit",
        data={
            "requisitos": ["ine", "comprobante"],
            "evaluacion": "4",
        },
        cookies=_auth_cookies(),
    )
    assert submit_response.status_code == 200, submit_response.text
    assert submit_response.json().get("success") is True


def test_time_and_daterange_submit():
    slug = f"time-range-{secrets.token_hex(4)}"
    create_payload = {
        "name": "Time Range Form",
        "slug": slug,
        "description": "Prueba de fecha, hora y rango",
        "is_active": True,
        "fields": [
            {
                "field_type": "date",
                "label": "Fecha ingreso",
                "name": "fecha_ingreso",
                "is_required": True,
                "order": 1,
            },
            {
                "field_type": "time",
                "label": "Hora ingreso",
                "name": "hora_ingreso",
                "is_required": True,
                "order": 2,
            },
            {
                "field_type": "daterange",
                "label": "Periodo auditoria",
                "name": "periodo_auditoria",
                "is_required": True,
                "order": 3,
            },
        ],
    }
    create_response = client.post("/api/admin/forms", json=create_payload, cookies=_auth_cookies())
    assert create_response.status_code == 200, create_response.text

    submit_response = client.post(
        f"/forms/api/{slug}/submit",
        data={
            "fecha_ingreso": "2026-02-13",
            "hora_ingreso": "10:30",
            "periodo_auditoria": ["2026-01-01", "2026-01-31"],
        },
        cookies=_auth_cookies(),
    )
    assert submit_response.status_code == 200, submit_response.text
    assert submit_response.json().get("success") is True


def test_file_signature_url_submit():
    slug = f"advanced-{secrets.token_hex(4)}"
    create_payload = {
        "name": "Advanced Form",
        "slug": slug,
        "description": "Prueba de archivo, firma y url",
        "is_active": True,
        "fields": [
            {
                "field_type": "file",
                "label": "Documento",
                "name": "documento",
                "is_required": True,
                "order": 1,
            },
            {
                "field_type": "signature",
                "label": "Firma",
                "name": "firma",
                "is_required": True,
                "order": 2,
            },
            {
                "field_type": "url",
                "label": "Perfil",
                "name": "perfil_url",
                "is_required": True,
                "order": 3,
            },
        ],
    }
    create_response = client.post("/api/admin/forms", json=create_payload, cookies=_auth_cookies())
    assert create_response.status_code == 200, create_response.text

    submit_response = client.post(
        f"/forms/api/{slug}/submit",
        data={
            "firma": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB",
            "perfil_url": "https://example.com/perfil",
        },
        files={"documento": ("dpi.pdf", b"contenido", "application/pdf")},
        cookies=_auth_cookies(),
    )
    assert submit_response.status_code == 200, submit_response.text
    assert submit_response.json().get("success") is True

    invalid_url_response = client.post(
        f"/forms/api/{slug}/submit",
        data={
            "firma": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB",
            "perfil_url": "perfil-invalido",
        },
        files={"documento": ("dpi.pdf", b"contenido", "application/pdf")},
        cookies=_auth_cookies(),
    )
    assert invalid_url_response.status_code == 422, invalid_url_response.text


def test_layout_fields_do_not_break_submission():
    slug = f"layout-{secrets.token_hex(4)}"
    create_payload = {
        "name": "Layout Form",
        "slug": slug,
        "description": "Prueba de campos de estructura",
        "is_active": True,
        "fields": [
            {"field_type": "header", "label": "Datos Generales del Asociado", "name": "hdr_1", "order": 1},
            {"field_type": "paragraph", "label": "Aviso legal", "name": "txt_1", "help_text": "Texto legal.", "order": 2},
            {"field_type": "divider", "label": "div", "name": "div_1", "order": 3},
            {"field_type": "pagebreak", "label": "page", "name": "pg_1", "order": 4},
            {"field_type": "text", "label": "Nombre", "name": "nombre", "is_required": True, "order": 5},
        ],
    }
    create_response = client.post("/api/admin/forms", json=create_payload, cookies=_auth_cookies())
    assert create_response.status_code == 200, create_response.text

    submit_response = client.post(
        f"/forms/api/{slug}/submit",
        data={"nombre": "Jose"},
        cookies=_auth_cookies(),
    )
    assert submit_response.status_code == 200, submit_response.text
    assert submit_response.json().get("success") is True

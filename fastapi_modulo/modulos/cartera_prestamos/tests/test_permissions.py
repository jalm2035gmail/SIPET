from __future__ import annotations


def test_role_from_request_state_is_rendered(client):
    response = client.get(
        "/resumen_ejecutivo",
        headers={"x-user-name": "analista.cp", "x-user-role": "jefe_cobranza"},
    )
    assert response.status_code == 200
    assert "analista.cp" in response.text
    assert "Jefe Cobranza" in response.text


def test_role_from_cookie_is_used_when_request_state_is_empty(client):
    response = client.get(
        "/resumen_ejecutivo",
        headers={"x-user-name": "", "x-user-role": ""},
        cookies={"user_name": "cookie.user", "user_role": "auditor_interno"},
    )
    assert response.status_code == 200
    assert "cookie.user" in response.text
    assert "Auditor Interno" in response.text


def test_menu_is_filtered_by_role_permissions(client):
    response = client.get(
        "/resumen_ejecutivo",
        headers={"x-user-name": "gestor", "x-user-role": "gestor_cobranza"},
    )
    assert response.status_code == 200
    assert "Cobranza" in response.text
    assert "Cartera de cobranza" in response.text
    assert "Cartera operativa" not in response.text
    assert "Configuración" not in response.text


def test_page_access_is_blocked_by_role(client):
    response = client.get(
        "/cartera-prestamos/gestion",
        headers={"x-user-name": "gestor", "x-user-role": "gestor_cobranza"},
    )
    assert response.status_code == 200
    assert "Sin permisos para acceder a esta sección." in response.text

from __future__ import annotations


def test_indicadores_api_returns_live_kpis(client, seeded_data):
    response = client.get("/api/cartera-prestamos/indicadores")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) >= 3
    names = {item["nombre"] for item in payload}
    assert "Indice de mora" in names
    assert "Cumplimiento de promesas" in names
    assert "Efectividad de cobranza" in names


def test_refresh_indicadores_persists_snapshot(client, seeded_data):
    response = client.post("/api/cartera-prestamos/indicadores/refresh")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 3
    assert all("semaforo" in item for item in payload)


def test_mesa_control_api_returns_operational_data(client, seeded_data):
    response = client.get("/api/cartera-prestamos/mesa-control")
    assert response.status_code == 200
    payload = response.json()
    assert payload["cartera_total"] > 0
    assert payload["cartera_vencida"] >= 0
    assert isinstance(payload["saldo_por_sucursal"], list)
    assert isinstance(payload["buckets_mora"], list)


def test_api_permissions_endpoint_returns_role_matrix(client):
    response = client.get(
        "/api/cartera-prestamos/permissions",
        headers={"x-user-role": "analista_cartera"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["view_resumen"] is True
    assert payload["view_gestion"] is True
    assert payload["view_recuperacion"] is False


def test_api_indicadores_forbidden_without_permission(client, seeded_data):
    response = client.get(
        "/api/cartera-prestamos/indicadores",
        headers={"x-user-role": "gestor_cobranza"},
    )
    assert response.status_code == 403

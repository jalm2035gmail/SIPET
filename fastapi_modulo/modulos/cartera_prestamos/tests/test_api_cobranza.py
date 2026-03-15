from __future__ import annotations


def test_gestion_api_returns_pipeline_and_expedientes(client, seeded_data):
    response = client.get("/api/cartera-prestamos/gestion")
    assert response.status_code == 200
    payload = response.json()
    assert "pipeline_colocacion" in payload
    assert payload["desembolsos_periodo"]["cantidad"] >= 1
    assert isinstance(payload["expedientes"], list)
    assert len(payload["expedientes"]) >= 1


def test_recuperacion_api_returns_promesas_and_cases(client, seeded_data):
    response = client.get("/api/cartera-prestamos/recuperacion?meta_periodo=15000")
    assert response.status_code == 200
    payload = response.json()
    assert payload["promesas_pago_activas"] >= 0
    assert payload["gestiones_dia"] >= 0
    assert isinstance(payload["efectividad_por_gestor"], list)
    assert isinstance(payload["casos_criticos"], list)


def test_api_gestion_forbidden_for_gestor_cobranza(client, seeded_data):
    response = client.get(
        "/api/cartera-prestamos/gestion",
        headers={"x-user-role": "gestor_cobranza"},
    )
    assert response.status_code == 403

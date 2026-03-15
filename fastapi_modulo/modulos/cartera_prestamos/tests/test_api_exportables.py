from __future__ import annotations


def test_export_cartera_vencida_returns_excel(client, seeded_data):
    response = client.get("/api/cartera-prestamos/export/cartera-vencida.xls")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.ms-excel")
    assert 'filename="cartera_vencida.xls"' in response.headers["content-disposition"]
    assert "Cartera vencida" in response.text
    assert "CR-001" in response.text


def test_export_promesas_pago_returns_excel(client, seeded_data):
    response = client.get("/api/cartera-prestamos/export/promesas-pago.xls")

    assert response.status_code == 200
    assert 'filename="promesas_pago.xls"' in response.headers["content-disposition"]
    assert "Promesas de pago" in response.text
    assert "Pago parcial aplicado" in response.text


def test_export_resumen_ejecutivo_returns_pdf(client, seeded_data):
    response = client.get("/api/cartera-prestamos/export/resumen-ejecutivo.pdf")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert 'filename="resumen_ejecutivo.pdf"' in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF-1.4")


def test_export_cobranza_is_forbidden_without_permission(client, seeded_data):
    response = client.get(
        "/api/cartera-prestamos/export/promesas-pago.xls",
        headers={"x-user-role": "analista_cartera"},
    )

    assert response.status_code == 403

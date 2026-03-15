from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    ("path", "role", "expected"),
    [
        ("/resumen_ejecutivo", "analista_cartera", "Cartera ejecutiva"),
        ("/cartera-prestamos/gestion", "analista_cartera", "Cartera operativa"),
        ("/cartera-prestamos/recuperacion", "supervisor_cobranza", "Cartera de cobranza"),
        ("/cartera-prestamos/indicadores", "analista_cartera", "Sin acceso, consulte con el administrador"),
        ("/cartera-prestamos/gestion-cobranza", "analista_cartera", "Sin permisos para acceder a esta sección."),
        ("/cartera-prestamos/configuracion", "analista_cartera", "Sin permisos para acceder a esta sección."),
    ],
)
def test_pages_load(client, path: str, role: str, expected: str):
    response = client.get(path, headers={"x-user-name": "tester", "x-user-role": role})
    assert response.status_code == 200
    assert expected in response.text


def test_static_assets_are_served(client):
    css_response = client.get("/modulos/cartera_prestamos/static/css/cartera_base.css")
    js_response = client.get("/modulos/cartera_prestamos/static/js/cartera_prestamos.js")
    img_response = client.get("/modulos/cartera_prestamos/static/description/financiamiento.svg")

    assert css_response.status_code == 200
    assert ":root" in css_response.text
    assert js_response.status_code == 200
    assert "CarteraPrestamosUI" in js_response.text
    assert img_response.status_code == 200


def test_missing_asset_returns_404(client):
    response = client.get("/modulos/cartera_prestamos/static/js/no_existe.js")
    assert response.status_code == 404


@pytest.mark.parametrize(
    ("path", "role", "subdomain"),
    [
        ("/resumen_ejecutivo", "analista_cartera", "Cartera ejecutiva"),
        ("/cartera-prestamos/gestion", "analista_cartera", "Cartera operativa"),
        ("/cartera-prestamos/recuperacion", "supervisor_cobranza", "Cartera de cobranza"),
    ],
)
def test_pages_expose_current_subdomain(client, path: str, role: str, subdomain: str):
    response = client.get(path, headers={"x-user-name": "tester", "x-user-role": role})

    assert response.status_code == 200
    assert subdomain in response.text
    assert "Subdominios" in response.text

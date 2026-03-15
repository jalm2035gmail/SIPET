MANIFEST = {
    "name": "cartera_prestamos",
    "summary": "Cartera ejecutiva, cartera operativa y cartera de cobranza.",
    "description": (
        "Modulo de cartera de prestamos organizado en cartera ejecutiva, "
        "cartera operativa y cartera de cobranza, junto con su controlador FastAPI "
        "y recursos visuales del modulo."
    ),
    "version": "1.0.0",
    "category": "Finanzas",
    "author": "SIPET",
    "sequence": 40,
    "website": "https://avancoop.org",
    "route": "/resumen_ejecutivo",
    "icon": "",
    "depends": ["main"],
    "data": [
        "vistas/base.html",
        "vistas/sidebar.html",
        "vistas/navbar.html",
        "vistas/mesa_control.html",
        "vistas/gestion.html",
        "vistas/recuperacion.html",
        "docs/evolucion_tecnica.md",
    ],
    "assets": {
        "css": [
            "static/css/cartera_base.css",
            "static/css/cartera_components.css",
            "static/css/cartera_mesa_control.css",
            "static/css/cartera_gestion.css",
            "static/css/cartera_recuperacion.css",
        ],
        "js": [
            "static/js/cartera_prestamos.js",
            "static/js/mesa_control.js",
            "static/js/gestion.js",
            "static/js/recuperacion.js",
        ],
        "static_base_url": "/modulos/cartera_prestamos/static",
        "img": [
            "static/description/financiamiento.svg",
        ],
        "description": [
            "static/description/financiamiento.svg",
        ],
    },
    "structure": {
        "router": [
            "controladores/cartera_prestamos.py",
            "controladores/api.py",
        ],
        "models": [
            "modelos/db_models.py",
            "modelos/schemas.py",
            "modelos/enums.py",
        ],
        "repositories": [
            "repositorios/cartera_repository.py",
            "repositorios/cobranza_repository.py",
        ],
        "services": [
            "servicios/cartera_service.py",
            "servicios/export_service.py",
            "servicios/gestion_service.py",
            "servicios/recuperacion_service.py",
            "servicios/indicadores_service.py",
            "servicios/mesa_control_service.py",
        ],
        "subdomains": [
            "cartera_ejecutiva",
            "cartera_operativa",
            "cartera_cobranza",
        ],
        "roadmap": [
            "docs/evolucion_tecnica.md",
        ],
        "tests": [
            "tests/conftest.py",
            "tests/test_pages.py",
            "tests/test_permissions.py",
            "tests/test_api_indicadores.py",
            "tests/test_api_cobranza.py",
            "tests/test_api_exportables.py",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}

__all__ = ["MANIFEST"]

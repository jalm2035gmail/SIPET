MANIFEST = {
    "name": "brujula",
    "summary": "Tablero de indicadores estrategicos y financieros de Brujula.",
    "description": (
        "Modulo Brujula con vistas HTML y controlador propio para dashboard, "
        "secciones de indicadores y administracion de valores por tenant."
    ),
    "version": "1.0.0",
    "category": "Analitica",
    "author": "SIPET",
    "sequence": 40,
    "website": "https://avancoop.org",
    "depends": ["main"],
    "data": [
        "vistas/brujula.html",
        "vistas/brujula_menu.html",
        "vistas/brujula_indicadores.html",
    ],
    "assets": {
        "css": [
            "static/css/brujula.css",
        ],
        "js": [
            "static/js/brujula.js",
        ],
        "description": [
            "static/description/brujula.svg",
        ],
        "img": [],
    },
    "structure": {
        "router": [
            "controladores/brujula.py",
            "controladores/pages.py",
            "controladores/api.py",
            "controladores/dependencies.py",
        ],
        "schemas": [
            "modelos/enums.py",
            "modelos/schemas.py",
        ],
        "models": [
            "modelos/brujula_fixed_indicators.py",
            "modelos/brujula_projection_store.py",
        ],
        "service": [
            "servicios/indicator_service.py",
            "servicios/projection_adapter.py",
            "servicios/projection_service.py",
            "servicios/analysis_service.py",
            "repositorios/schema.py",
            "repositorios/tenant_repository.py",
            "repositorios/indicator_repository.py",
            "repositorios/override_repository.py",
        ],
        "tests": [
            "tests/test_brujula_module.py",
        ],
    },
    "tests": [
        "tests/test_brujula_module.py",
    ],
    "optional_integrations": [
        "proyectando",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}

__all__ = ["MANIFEST"]

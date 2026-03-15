MANIFEST = {
    "name": "activo_fijo",
    "summary": "Gestion de activos, depreciaciones, asignaciones, mantenimientos y bajas.",
    "description": (
        "Modulo de activo fijo con vistas HTML, endpoints API y recursos frontend "
        "para la administracion de bienes institucionales."
    ),
    "version": "1.0.0",
    "category": "Operaciones",
    "author": "SIPET",
    "sequence": "",
    "website": "https://avancoop.org",
    "depends": ["main"],
    "data": [
        "vistas/activo_fijo.html",
        "vistas/activo_fijo_menus.html",
    ],
    "assets": {
        "css": [
            "static/css/activo_fijo.css",
        ],
        "js": [
            "static/js/activo_fijo/index.js",
            "static/js/activo_fijo/api.js",
            "static/js/activo_fijo/ui.js",
            "static/js/activo_fijo/activos.js",
            "static/js/activo_fijo/depreciaciones.js",
            "static/js/activo_fijo/asignaciones.js",
            "static/js/activo_fijo/mantenimientos.js",
            "static/js/activo_fijo/bajas.js",
            "static/js/activo_fijo/kpis.js",
        ],
        "static_base_url": "/modulos/activo_fijo/static",
        "img": [
            "static/description/activo_fijo.svg",
        ],
        "description": [
            "static/description/activo_fijo.svg",
        ],
    },
    "structure": {
        "router": [
            "router.py",
            "controladores/activo_fijo.py",
        ],
        "schemas": [
            "schemas.py",
            "modelos/af_models.py",
        ],
        "models": [
            "models.py",
            "modelos/af_db_models.py",
        ],
        "repository": [
            "repository.py",
        ],
        "serializers": [
            "serializers.py",
        ],
        "service": [
            "service.py",
            "modelos/af_store.py",
        ],
        "tests": [
            "tests/__init__.py",
            "test_activo_fijo_phase.py",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}

__all__ = ["MANIFEST"]

MANIFEST = {
    "name": "auditoria",
    "summary": "Gestion de auditorias, hallazgos, recomendaciones y seguimiento.",
    "description": (
        "Modulo de auditoria con vista HTML, endpoints API y recurso frontend "
        "propio para el control de procesos de auditoria institucional."
    ),
    "version": "1.0.0",
    "category": "Operaciones",
    "author": "SIPET",
    "sequence": "",
    "website": "https://avancoop.org",
    "depends": ["main"],
    "data": [
        "vistas/auditoria.html",
        "vistas/auditoria_menus.html",
    ],
    "assets": {
        "css": [
            "static/css/auditoria.css",
        ],
        "js": [
            "static/js/auditoria.js",
        ],
        "description": [
            "static/description/auditoria.svg",
        ],
        "img": [],
    },
    "structure": {
        "router": [
            "controladores/auditoria.py",
        ],
        "schemas": [
            "modelos/aud_models.py",
        ],
        "models": [
            "modelos/aud_db_models.py",
        ],
        "service": [
            "modelos/aud_store.py",
        ],
        "tests": [
            "test_auditoria_phase.py",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}

__all__ = ["MANIFEST"]

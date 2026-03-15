MANIFEST = {
    "name": "control_interno",
    "label": "Control y seguimiento",
    "summary": "Control interno, programa anual, evidencias, hallazgos y reportes.",
    "description": (
        "Modulo de control interno con vistas operativas, APIs y tableros para "
        "seguimiento de controles, programa anual, evidencias, hallazgos y "
        "reportes institucionales."
    ),
    "version": "1.0.0",
    "category": "Operaciones",
    "author": "SIPET",
    "sequence": "",
    "website": "https://avancoop.org",
    "route": "/control-seguimiento",
    "icon": "",
    "depends": [],
    "data": [
        "vistas/control.html",
        "vistas/tablero.html",
        "vistas/programa.html",
        "vistas/evidencia.html",
        "vistas/hallazgos.html",
        "vistas/reportes_ci.html",
    ],
    "assets": {
        "css": [
            "static/css/control_interno_views.css",
        ],
        "js": [
            "static/js/programa.js",
            "static/js/evidencia.js",
            "static/js/hallazgos.js",
        ],
        "static_base_url": "/modulos/control_interno/static",
        "img": [
            "static/description/control.svg",
        ],
        "description": [
            "static/description/control.svg",
        ],
    },
    "structure": {
        "router": [
            "controladores/pages.py",
            "controladores/dependencies.py",
            "controladores/utils.py",
            "controladores/control.py",
            "controladores/tablero.py",
            "controladores/programa.py",
            "controladores/evidencia.py",
            "controladores/hallazgos.py",
            "controladores/reportes_ci.py",
            "controladores/api_controles.py",
            "controladores/api_programa.py",
            "controladores/api_evidencias.py",
            "controladores/api_hallazgos.py",
            "controladores/api_tablero.py",
            "controladores/api_reportes.py",
        ],
        "models": [
            "modelos/db_models.py",
            "modelos/control.py",
            "modelos/programa.py",
            "modelos/evidencia.py",
            "modelos/hallazgo.py",
            "modelos/enums.py",
            "modelos/schemas.py",
        ],
        "service": [
            "modelos/store.py",
            "modelos/tablero_store.py",
            "modelos/programa_store.py",
            "modelos/evidencia_store.py",
            "modelos/hallazgo_store.py",
            "modelos/reporte_store.py",
            "servicios/controles_service.py",
            "servicios/programa_service.py",
            "servicios/evidencia_service.py",
            "servicios/hallazgo_service.py",
            "servicios/tablero_service.py",
            "servicios/reporte_service.py",
        ],
        "repository": [
            "repositorios/controles_repository.py",
            "repositorios/programa_repository.py",
            "repositorios/evidencia_repository.py",
            "repositorios/hallazgo_repository.py",
            "repositorios/reporte_repository.py",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}

__all__ = ["MANIFEST"]

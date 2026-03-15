MANIFEST = {
    "name": "capacitacion",
    "summary": "Capacitacion, cursos, evaluaciones y progreso de colaboradores.",
    "description": (
        "Modulo de capacitacion con dashboard, editor de cursos, evaluaciones, "
        "gamificacion, certificados y vistas publicas/controladas para el ciclo "
        "de aprendizaje institucional."
    ),
    "version": "1.0.0",
    "category": "Talento",
    "author": "SIPET",
    "sequence": "",
    "website": "https://avancoop.org",
    "depends": ["main", "encuestas"],
    "data": [
        "vistas/capacitacion.html",
        "vistas/capacitacion_dashboard.html",
        "vistas/capacitacion_editor.html",
        "vistas/capacitacion_eval.html",
        "vistas/capacitacion_gamificacion.html",
        "vistas/capacitacion_player.html",
        "vistas/capacitacion_presentaciones.html",
        "vistas/capacitacion_progreso.html",
        "vistas/capacitacion_certificados.html",
        "vistas/capacitacion_cert_view.html",
        "vistas/capacitacion_verificar.html",
        "vistas/capacitacion_visor.html",
    ],
    "assets": {
        "css": [
            "static/css/capacitacion.css",
            "static/css/capacitacion_editor.css",
            "static/css/capacitacion_player.css",
            "static/css/capacitacion_dashboard.css",
        ],
        "js": [
            "static/js/capacitacion.js",
            "static/js/capacitacion_dashboard.js",
            "static/js/capacitacion_editor.js",
            "static/js/editor/editor-core.js",
            "static/js/editor/editor-widgets.js",
            "static/js/editor/editor-background.js",
            "static/js/editor/editor-surveys.js",
            "static/js/editor/editor-canvas.js",
            "static/js/editor/editor-slides.js",
            "static/js/editor/editor-ui.js",
            "static/js/capacitacion_eval.js",
            "static/js/capacitacion_gamificacion.js",
            "static/js/capacitacion_player.js",
            "static/js/capacitacion_presentaciones.js",
            "static/js/capacitacion_progreso.js",
            "static/js/capacitacion_certificados.js",
            "static/js/capacitacion_verificar.js",
            "static/js/capacitacion_visor.js",
        ],
        "description": [
            "static/description/capacitacion.svg",
        ],
        "img": [],
    },
    "structure": {
        "router": [
            "controladores/capacitacion.py",
        ],
        "schemas": [
            "modelos/cap_schemas.py",
        ],
        "models": [
            "modelos/cap_db_models.py",
        ],
        "service": [
            "modelos/cap_service.py",
            "modelos/cap_inscripcion_service.py",
            "modelos/cap_evaluacion_service.py",
            "modelos/cap_gamificacion_service.py",
            "modelos/cap_presentacion_service.py",
        ],
        "tests": [
            "tests/test_capacitacion_module.py",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}

__all__ = ["MANIFEST"]

from __future__ import annotations

from typing import Final

MODULE_MENU: Final[list[dict[str, str]]] = [
    {
        "key": "control",
        "label": "Control interno",
        "href": "/control-interno",
        "description": "Catalogo de controles internos.",
    },
    {
        "key": "tablero",
        "label": "Tablero",
        "href": "/control-interno/tablero",
        "description": "Indicadores y seguimiento general.",
    },
    {
        "key": "programa",
        "label": "Programa anual",
        "href": "/control-interno/programa-anual",
        "description": "Planeacion y seguimiento de actividades.",
    },
    {
        "key": "evidencias",
        "label": "Evidencias",
        "href": "/control-interno/evidencias",
        "description": "Registro documental de controles.",
    },
    {
        "key": "hallazgos",
        "label": "Hallazgos",
        "href": "/control-interno/hallazgos",
        "description": "Seguimiento de hallazgos y acciones.",
    },
    {
        "key": "reportes",
        "label": "Reportes",
        "href": "/control-interno/reportes",
        "description": "Consultas y exportaciones del modulo.",
    },
]

MENU_BY_KEY: Final[dict[str, dict[str, str]]] = {
    item["key"]: item for item in MODULE_MENU
}


def get_menu_item(key: str) -> dict[str, str] | None:
    return MENU_BY_KEY.get(key)


__all__ = ["MODULE_MENU", "MENU_BY_KEY", "get_menu_item"]

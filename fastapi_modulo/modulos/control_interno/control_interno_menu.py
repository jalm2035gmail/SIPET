from __future__ import annotations

from typing import Final


MENU_ORDER: Final[tuple[str, ...]] = (
    "control",
    "tablero",
    "programa",
    "evidencias",
    "hallazgos",
    "reportes",
)

MENU_DEFINITIONS: Final[dict[str, dict[str, str]]] = {
    "control": {
        "key": "control",
        "label": "Control interno",
        "href": "/control-interno",
        "description": "Catalogo de controles internos.",
        "icon": "fa-solid fa-shield-halved",
    },
    "tablero": {
        "key": "tablero",
        "label": "Tablero",
        "href": "/control-interno/tablero",
        "description": "Indicadores y seguimiento general.",
        "icon": "fa-solid fa-chart-line",
    },
    "programa": {
        "key": "programa",
        "label": "Programa anual",
        "href": "/control-interno/programa-anual",
        "description": "Planeacion y seguimiento de actividades.",
        "icon": "fa-solid fa-calendar-days",
    },
    "evidencias": {
        "key": "evidencias",
        "label": "Evidencias",
        "href": "/control-interno/evidencias",
        "description": "Registro documental de controles.",
        "icon": "fa-solid fa-folder-open",
    },
    "hallazgos": {
        "key": "hallazgos",
        "label": "Hallazgos",
        "href": "/control-interno/hallazgos",
        "description": "Seguimiento de hallazgos y acciones.",
        "icon": "fa-solid fa-triangle-exclamation",
    },
    "reportes": {
        "key": "reportes",
        "label": "Reportes",
        "href": "/control-interno/reportes",
        "description": "Consultas y exportaciones del modulo.",
        "icon": "fa-solid fa-file-export",
    },
}

MODULE_MENU: Final[list[dict[str, str]]] = [MENU_DEFINITIONS[key].copy() for key in MENU_ORDER]
MENU_BY_KEY: Final[dict[str, dict[str, str]]] = {item["key"]: item for item in MODULE_MENU}
MENU_BY_HREF: Final[dict[str, dict[str, str]]] = {item["href"]: item for item in MODULE_MENU}
DEFAULT_MENU_KEY: Final[str] = MENU_ORDER[0]


def list_menu_items() -> list[dict[str, str]]:
    return [item.copy() for item in MODULE_MENU]


def get_menu_item(key: str) -> dict[str, str] | None:
    item = MENU_BY_KEY.get((key or "").strip())
    return item.copy() if item else None


def get_menu_item_by_href(href: str) -> dict[str, str] | None:
    item = MENU_BY_HREF.get((href or "").strip())
    return item.copy() if item else None


def get_default_menu_item() -> dict[str, str]:
    return MENU_BY_KEY[DEFAULT_MENU_KEY].copy()


def resolve_menu_key(value: str | None, *, fallback: str = DEFAULT_MENU_KEY) -> str:
    key = (value or "").strip()
    return key if key in MENU_BY_KEY else fallback


def build_menu_context(active_key: str | None = None) -> dict[str, object]:
    resolved_key = resolve_menu_key(active_key)
    return {
        "active_key": resolved_key,
        "active_item": get_menu_item(resolved_key),
        "items": [
            {
                **item,
                "active": item["key"] == resolved_key,
            }
            for item in list_menu_items()
        ],
    }


__all__ = [
    "DEFAULT_MENU_KEY",
    "MENU_BY_HREF",
    "MENU_BY_KEY",
    "MENU_DEFINITIONS",
    "MENU_ORDER",
    "MODULE_MENU",
    "build_menu_context",
    "get_default_menu_item",
    "get_menu_item",
    "get_menu_item_by_href",
    "list_menu_items",
    "resolve_menu_key",
]

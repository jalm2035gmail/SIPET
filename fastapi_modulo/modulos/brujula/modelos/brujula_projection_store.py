from __future__ import annotations

import json
import os
from datetime import date
from typing import Any


APP_ENV_DEFAULT = (os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "development").strip().lower()
RUNTIME_STORE_DIR = (os.environ.get("RUNTIME_STORE_DIR") or f"fastapi_modulo/runtime_store/{APP_ENV_DEFAULT}").strip()
DATOS_PRELIMINARES_STORE_PATH = (
    os.environ.get("DATOS_PRELIMINARES_STORE_PATH")
    or os.path.join(RUNTIME_STORE_DIR, "datos_preliminares_store.json")
).strip()

DEFAULT_DATOS_GENERALES = {
    "primer_anio_proyeccion": "",
    "anios_proyeccion": "3",
    "ifb_rows_json": "",
}


def load_datos_preliminares_store() -> dict[str, str]:
    data = dict(DEFAULT_DATOS_GENERALES)
    if not os.path.exists(DATOS_PRELIMINARES_STORE_PATH):
        return data
    try:
        with open(DATOS_PRELIMINARES_STORE_PATH, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return data
    if not isinstance(loaded, dict):
        return data
    for key in data:
        if key in loaded and loaded[key] is not None:
            data[key] = str(loaded[key]).strip()
    return data


def _parse_json_value(raw: str, fallback: Any) -> Any:
    try:
        parsed = json.loads(raw or "")
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback
    return fallback if parsed is None else parsed


def _get_projection_years(store: dict[str, str]) -> int:
    try:
        years = int(str(store.get("anios_proyeccion") or "").strip() or 3)
    except (TypeError, ValueError):
        years = 3
    return max(1, min(years, 10))


def _get_projection_start_year(store: dict[str, str]) -> int:
    try:
        year = int(str(store.get("primer_anio_proyeccion") or "").strip())
    except (TypeError, ValueError):
        year = date.today().year
    return year


def get_if_period_columns(store: dict[str, str] | None = None) -> list[dict[str, str]]:
    current_store = store or load_datos_preliminares_store()
    start_year = _get_projection_start_year(current_store)
    projection_years = _get_projection_years(current_store)
    columns = [
        {"key": "-3", "label": str(start_year - 3)},
        {"key": "-2", "label": str(start_year - 2)},
        {"key": "-1", "label": str(start_year - 1)},
    ]
    for idx in range(projection_years):
        columns.append({"key": str(idx), "label": str(start_year + idx)})
    return columns


__all__ = ["_parse_json_value", "get_if_period_columns", "load_datos_preliminares_store"]

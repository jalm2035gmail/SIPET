from __future__ import annotations

from typing import Any

from fastapi_modulo.modulos.brujula.modelos.enums import PeriodKind
from fastapi_modulo.modulos.brujula.modelos.brujula_projection_store import (
    _parse_json_value,
)
from fastapi_modulo.modulos.brujula.servicios.projection_adapter import (
    load_projection_period_columns,
    load_projection_store,
)


def get_projection_periods() -> list[dict[str, str]]:
    store = load_projection_store()
    periods = []
    for item in load_projection_period_columns(store):
        key = str(item.get("key") or "").strip()
        periods.append(
            {
                "key": key,
                "label": str(item.get("label") or key),
                "kind": PeriodKind.HISTORICO if key.startswith("-") else PeriodKind.PROYECTADO,
            }
        )
    return periods


def normalize_indicator_matrix_rows(raw_rows, periods):
    rows = raw_rows if isinstance(raw_rows, list) else []
    valid_period_keys = {str(period.get("key") or "").strip() for period in periods}
    clean = []
    seen = set()
    for idx, item in enumerate(rows, start=1):
        if not isinstance(item, dict):
            continue
        indicador = str(item.get("indicador") or "").strip()
        if not indicador:
            continue
        key = indicador.lower()
        if key in seen:
            continue
        seen.add(key)
        raw_values = item.get("values") if isinstance(item.get("values"), dict) else {}
        values = {}
        for period_key in valid_period_keys:
            values[period_key] = str(raw_values.get(period_key) or "").strip()
        clean.append({"indicador": indicador, "values": values, "orden": idx})
    return clean


def parse_numeric_value(value: Any) -> float | None:
    raw = str(value or "").replace(",", "").replace("%", "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def safe_growth(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None or abs(float(previous)) < 1e-9:
        return None
    return ((float(current) - float(previous)) / float(previous)) * 100.0


def build_financial_indicator_context(periods: list[dict], store: dict[str, str] | None = None) -> dict[str, Any]:
    current_store = dict(store or load_projection_store())
    raw_rows = _parse_json_value(current_store.get("ifb_rows_json", ""), [])
    rows = raw_rows if isinstance(raw_rows, list) else []
    row_map: dict[str, dict[str, Any]] = {}
    value_map: dict[str, dict[str, float | None]] = {}
    period_keys = [str(period.get("key") or "").strip() for period in periods]

    for row in rows:
        if not isinstance(row, dict):
            continue
        code = str(row.get("cuenta") or row.get("cod") or "").strip()
        if not code:
            continue
        row_map[code] = row
        raw_values = row.get("values") if isinstance(row.get("values"), dict) else {}
        value_map[code] = {key: parse_numeric_value(raw_values.get(key)) for key in period_keys}

    def get_value(code: str, period_key: str) -> float | None:
        return (value_map.get(code) or {}).get(period_key)

    def series_growth(code: str, period_key: str) -> float | None:
        try:
            index = period_keys.index(period_key)
        except ValueError:
            return None
        if index <= 0:
            return None
        return safe_growth(get_value(code, period_key), get_value(code, period_keys[index - 1]))

    return {
        "store": current_store,
        "row_map": row_map,
        "value_map": value_map,
        "period_keys": period_keys,
        "get_value": get_value,
        "series_growth": series_growth,
    }

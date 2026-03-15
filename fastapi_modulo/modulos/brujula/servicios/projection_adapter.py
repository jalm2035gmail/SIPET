from __future__ import annotations

from collections.abc import Callable

from fastapi_modulo.modulos.brujula.modelos.brujula_projection_store import (
    get_if_period_columns as get_local_period_columns,
    load_datos_preliminares_store as load_local_projection_store,
)


ProjectionStoreLoader = Callable[[], dict[str, str]]
ProjectionPeriodsLoader = Callable[[dict[str, str]], list[dict[str, str]]]

_store_loader: ProjectionStoreLoader = load_local_projection_store
_periods_loader: ProjectionPeriodsLoader = get_local_period_columns


def register_projection_adapter(
    store_loader: ProjectionStoreLoader | None = None,
    periods_loader: ProjectionPeriodsLoader | None = None,
) -> None:
    global _store_loader, _periods_loader
    if store_loader is not None:
        _store_loader = store_loader
    if periods_loader is not None:
        _periods_loader = periods_loader


def load_projection_store() -> dict[str, str]:
    try:
        data = _store_loader()
    except Exception:
        data = load_local_projection_store()
    return data if isinstance(data, dict) else load_local_projection_store()


def load_projection_period_columns(store: dict[str, str] | None = None) -> list[dict[str, str]]:
    current_store = store or load_projection_store()
    try:
        rows = _periods_loader(current_store)
    except Exception:
        rows = get_local_period_columns(current_store)
    return rows if isinstance(rows, list) else get_local_period_columns(current_store)


__all__ = [
    "load_projection_period_columns",
    "load_projection_store",
    "register_projection_adapter",
]

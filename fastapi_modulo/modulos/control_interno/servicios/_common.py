from __future__ import annotations

from datetime import date
from typing import Any


def iso_date(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def contains_text(*values: str, query: str | None = None) -> bool:
    if not query:
        return True
    ql = query.lower()
    return any(ql in (value or "").lower() for value in values)


__all__ = ["contains_text", "iso_date", "parse_date"]

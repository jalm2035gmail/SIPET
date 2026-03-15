from __future__ import annotations

from fastapi_modulo.modulos.proyectando.modelos.data_store import load_datos_preliminares_store


def load_projection_completion_summary() -> dict[str, int]:
    try:
        prelim_data = load_datos_preliminares_store()
    except Exception:
        return {"filled": 0, "total": 0}
    if not isinstance(prelim_data, dict):
        return {"filled": 0, "total": 0}
    projected_values = [str(value or "").strip() for value in prelim_data.values()]
    return {
        "filled": len([value for value in projected_values if value]),
        "total": len(projected_values),
    }

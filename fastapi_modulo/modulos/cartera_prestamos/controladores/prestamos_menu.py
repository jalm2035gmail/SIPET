from __future__ import annotations

from typing import Any


MODULE_SUBDOMAINS: dict[str, dict[str, Any]] = {
    "ejecutiva": {
        "key": "ejecutiva",
        "label": "Cartera ejecutiva",
        "description": "Seguimiento ejecutivo, riesgos y control institucional.",
        "sections": {"resumen", "mesa_control", "dashboard_general", "indicadores_financieros", "alertas_riesgos"},
    },
    "operativa": {
        "key": "operativa",
        "label": "Cartera operativa",
        "description": "Seguimiento operativo de expedientes, colocación y reestructura.",
        "sections": {"gestion", "listado_creditos", "operacion_comercial", "castigos", "reestructuracion"},
    },
    "cobranza": {
        "key": "cobranza",
        "label": "Cartera de cobranza",
        "description": "Recuperación, promesas de pago y gestión de cobranza.",
        "sections": {"recuperacion", "gestion_cobranza", "cartera_vencida", "promesas_pago", "visitas_gestiones"},
    },
}


MODULE_MENU = [
    {"key": "resumen", "label": "Cartera ejecutiva", "href": "/resumen_ejecutivo", "icon": "fa-solid fa-gauge-high"},
    {"key": "gestion", "label": "Cartera operativa", "href": "/cartera-prestamos/gestion", "icon": "fa-solid fa-briefcase"},
    {"key": "recuperacion", "label": "Cartera de cobranza", "href": "/cartera-prestamos/recuperacion", "icon": "fa-solid fa-life-ring"},
    {"key": "indicadores", "label": "Indicadores", "href": "/cartera-prestamos/indicadores", "icon": "fa-solid fa-chart-line"},
    {"key": "cobranza", "label": "Cobranza", "href": "/cartera-prestamos/gestion-cobranza", "icon": "fa-solid fa-hand-holding-dollar"},
    {"key": "configuracion", "label": "Configuración", "href": "/cartera-prestamos/configuracion", "icon": "fa-solid fa-gear"},
]


def get_module_subdomains() -> list[dict[str, Any]]:
    return [MODULE_SUBDOMAINS[key] for key in ("ejecutiva", "operativa", "cobranza")]


def get_current_subdomain(section_key: str) -> dict[str, Any] | None:
    for subdomain in MODULE_SUBDOMAINS.values():
        if section_key in subdomain["sections"]:
            return subdomain
    return None


__all__ = [
    "MODULE_MENU",
    "MODULE_SUBDOMAINS",
    "get_current_subdomain",
    "get_module_subdomains",
]

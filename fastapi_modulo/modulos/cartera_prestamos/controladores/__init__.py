from fastapi_modulo.modulos.cartera_prestamos.controladores.cartera_prestamos import router
from fastapi_modulo.modulos.cartera_prestamos.controladores.prestamos_menu import (
    MODULE_MENU,
    MODULE_SUBDOMAINS,
    get_current_subdomain,
    get_module_subdomains,
)

__all__ = [
    "MODULE_MENU",
    "MODULE_SUBDOMAINS",
    "get_current_subdomain",
    "get_module_subdomains",
    "router",
]

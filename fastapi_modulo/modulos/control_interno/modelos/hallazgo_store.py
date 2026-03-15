from fastapi_modulo.modulos.control_interno.servicios.hallazgo_service import (
    actualizar_accion_service as actualizar_accion,
    actualizar_service as actualizar_hallazgo,
    crear_accion_service as crear_accion,
    crear_service as crear_hallazgo,
    eliminar_accion_service as eliminar_accion,
    eliminar_service as eliminar_hallazgo,
    listar_acciones_service as listar_acciones,
    listar_service as listar_hallazgos,
    obtener_service as obtener_hallazgo,
    resumen_service as resumen_hallazgos,
)

__all__ = [
    "actualizar_accion",
    "actualizar_hallazgo",
    "crear_accion",
    "crear_hallazgo",
    "eliminar_accion",
    "eliminar_hallazgo",
    "listar_acciones",
    "listar_hallazgos",
    "obtener_hallazgo",
    "resumen_hallazgos",
]

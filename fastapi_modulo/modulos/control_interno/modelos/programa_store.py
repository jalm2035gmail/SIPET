from fastapi_modulo.modulos.control_interno.servicios.programa_service import (
    actualizar_actividad_service as actualizar_actividad,
    actualizar_programa_service as actualizar_programa,
    crear_actividad_service as crear_actividad,
    crear_programa_service as crear_programa,
    eliminar_actividad_service as eliminar_actividad,
    eliminar_programa_service as eliminar_programa,
    listar_actividades_service as listar_actividades,
    listar_programas_service as listar_programas,
    obtener_actividad_service as obtener_actividad,
    obtener_programa_service as obtener_programa,
    resumen_programa_service as resumen_programa,
)

__all__ = [
    "actualizar_actividad",
    "actualizar_programa",
    "crear_actividad",
    "crear_programa",
    "eliminar_actividad",
    "eliminar_programa",
    "listar_actividades",
    "listar_programas",
    "obtener_actividad",
    "obtener_programa",
    "resumen_programa",
]

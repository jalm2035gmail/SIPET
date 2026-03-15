from fastapi_modulo.modulos.control_interno.servicios.tablero_service import (
    kpi_controles_service as kpi_controles,
    kpi_evidencias_service as kpi_evidencias,
    kpi_hallazgos_service as kpi_hallazgos,
    kpi_programa_service as kpi_programa,
    resumen_global_service as resumen_global,
)

__all__ = [
    "kpi_controles",
    "kpi_evidencias",
    "kpi_hallazgos",
    "kpi_programa",
    "resumen_global",
]

from fastapi import APIRouter

from fastapi_modulo.modulos.planificacion.modelos.kpis_service import _kpi_evaluate_status
from fastapi_modulo.modulos.planificacion.modelos.plan_estrategico_service import _ensure_strategic_identity_table


# Compatibilidad temporal: la lógica de Plan estratégico, POA, KPIs y
# notificaciones ya fue separada a módulos específicos de planificación.
router = APIRouter()

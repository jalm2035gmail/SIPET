from fastapi import APIRouter

from fastapi_modulo.modulos.planificacion import kpis_service


router = APIRouter()

router.add_api_route("/api/kpis/definiciones", kpis_service.kpis_definiciones, methods=["GET"])
router.add_api_route("/api/kpis/mediciones", kpis_service.kpis_mediciones_list, methods=["GET"])
router.add_api_route("/api/kpis/estadisticas", kpis_service.kpis_estadisticas, methods=["GET"])
router.add_api_route("/api/kpis/medicion", kpis_service.kpi_medicion_save, methods=["POST"])
router.add_api_route("/api/kpis/medicion/{medicion_id}", kpis_service.kpi_medicion_delete, methods=["DELETE"])

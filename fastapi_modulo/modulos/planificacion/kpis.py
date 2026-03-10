from fastapi import APIRouter

from fastapi_modulo.modulos.planificacion import kpis_service


router = APIRouter()

router.add_api_route("/api/kpis/plantilla.csv", kpis_service.download_kpis_template, methods=["GET"])
router.add_api_route("/api/kpis/importar", kpis_service.import_kpis_template, methods=["POST"])
router.add_api_route("/api/kpis/definiciones", kpis_service.kpis_definiciones, methods=["GET"])
router.add_api_route("/api/kpis/mediciones", kpis_service.kpis_mediciones_list, methods=["GET"])
router.add_api_route("/api/kpis/estadisticas", kpis_service.kpis_estadisticas, methods=["GET"])
router.add_api_route("/api/kpis/medicion", kpis_service.kpi_medicion_save, methods=["POST"])
router.add_api_route("/api/kpis/medicion/{medicion_id}", kpis_service.kpi_medicion_delete, methods=["DELETE"])

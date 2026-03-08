from fastapi import APIRouter

from fastapi_modulo.modulos.planificacion import notificaciones_service


router = APIRouter()

router.add_api_route(
    "/api/notificaciones/resumen",
    notificaciones_service.notifications_summary,
    methods=["GET"],
)
router.add_api_route(
    "/api/notificaciones/marcar-leida",
    notificaciones_service.mark_notification_read,
    methods=["POST"],
)
router.add_api_route(
    "/api/notificaciones/marcar-todas-leidas",
    notificaciones_service.mark_all_notifications_read,
    methods=["POST"],
)

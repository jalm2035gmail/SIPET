from datetime import datetime
from typing import Any, Dict, List, Optional

from app.templates.components.buttons import ButtonTemplate
from app.templates.components.cards import CardTemplate
from app.templates.components.navigation import BreadcrumbTemplate


class StrategicPlanTemplate:
    """Template para generar configuraciones de Planes Estratégicos"""

    @staticmethod
    def create_plan_response(
        plan: Dict[str, Any],
        include_details: bool = True,
        include_actions: bool = True,
    ) -> Dict[str, Any]:
        """Template para respuesta de plan estratégico"""
        response = {
            "data": plan,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "entity": "strategic_plan",
            },
        }

        if include_details:
            response["details"] = StrategicPlanTemplate._get_plan_details(plan)

        if include_actions:
            response["actions"] = StrategicPlanTemplate._get_plan_actions(plan)

        return response

    @staticmethod
    def _get_plan_details(plan: Dict[str, Any]) -> Dict[str, Any]:
        """Genera detalles estructurados del plan"""
        status_info = {
            "draft": {"color": "gray", "icon": "draft", "label": "Borrador"},
            "in_review": {"color": "yellow", "icon": "review", "label": "En Revisión"},
            "approved": {"color": "blue", "icon": "approved", "label": "Aprobado"},
            "active": {"color": "green", "icon": "active", "label": "Activo"},
            "completed": {"color": "purple", "icon": "completed", "label": "Completado"},
            "archived": {"color": "gray", "icon": "archived", "label": "Archivado"},
            "cancelled": {"color": "red", "icon": "cancelled", "label": "Cancelado"},
        }

        status = plan.get("status", "draft")
        status_config = status_info.get(status, status_info["draft"])

        return {
            "status": status_config,
            "period": {
                "start": plan.get("start_date"),
                "end": plan.get("end_date"),
                "days_remaining": plan.get("days_remaining", 0),
                "is_active_period": plan.get("is_active_period", False),
            },
            "progress": {
                "value": plan.get("progress", 0.0),
                "label": f"{plan.get('progress', 0.0)}%",
                "color": StrategicPlanTemplate._get_progress_color(plan.get("progress", 0.0)),
            },
        }

    @staticmethod
    def _get_plan_actions(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Genera acciones disponibles según estado del plan"""
        status = plan.get("status", "draft")
        plan_id = plan.get("id")

        MAIN_actions = [
            ButtonTemplate.primary("Ver Detalles", url=f"/strategic/plans/{plan_id}"),
            ButtonTemplate.secondary("Editar", url=f"/strategic/plans/{plan_id}/edit"),
        ]

        status_actions = {
            "draft": [
                ButtonTemplate.success("Enviar a Revisión", action="submit_for_review"),
                ButtonTemplate.danger("Eliminar", action="delete", confirmation=True),
            ],
            "in_review": [
                ButtonTemplate.success("Aprobar", action="approve"),
                ButtonTemplate.warning("Devolver", action="return_to_draft"),
            ],
            "approved": [
                ButtonTemplate.success("Activar", action="activate"),
                ButtonTemplate.secondary("Generar POA", action="generate_poa"),
            ],
            "active": [
                ButtonTemplate.info("Seguimiento", url=f"/strategic/plans/{plan_id}/tracking"),
                ButtonTemplate.warning("Pausar", action="pause"),
                ButtonTemplate.success("Completar", action="complete"),
            ],
            "completed": [
                ButtonTemplate.secondary("Generar Reporte", action="generate_report"),
                ButtonTemplate.info("Archivar", action="archive"),
            ],
        }

        return MAIN_actions + status_actions.get(status, [])

    @staticmethod
    def _get_progress_color(progress: float) -> str:
        """Determina color basado en progreso"""
        if progress >= 80:
            return "success"
        elif progress >= 50:
            return "warning"
        return "error"

    @staticmethod
    def create_plan_card(plan: Dict[str, Any]) -> Dict[str, Any]:
        """Template para tarjeta de plan en listados"""
        status = plan.get("status", "draft")
        plan_id = plan.get("id")

        return CardTemplate.basic(
            title=plan.get("name", "Sin nombre"),
            subtitle=plan.get("code", "Sin código"),
            content={
                "status": {
                    "value": status,
                    "color": StrategicPlanTemplate._get_status_color(status),
                },
                "period": f"{plan.get('start_date')} - {plan.get('end_date')}",
                "progress": {
                    "value": plan.get("progress", 0.0),
                    "display": f"{plan.get('progress', 0.0)}%",
                },
                "axes_count": plan.get("axes_count", 0),
                "department": plan.get("department_name"),
            },
            actions=[
                {"label": "Ver", "url": f"/strategic/plans/{plan_id}"},
                {"label": "Editar", "url": f"/strategic/plans/{plan_id}/edit"},
            ],
            badges=[
                {
                    "text": status.upper(),
                    "color": StrategicPlanTemplate._get_status_color(status),
                }
            ],
        )

    @staticmethod
    def _get_status_color(status: str) -> str:
        """Mapea estado a color"""
        color_map = {
            "draft": "gray",
            "in_review": "yellow",
            "approved": "blue",
            "active": "green",
            "completed": "purple",
            "archived": "gray",
            "cancelled": "red",
        }
        return color_map.get(status, "gray")

    @staticmethod
    def create_breadcrumb(plan_id: Optional[int] = None, current_page: str = "list") -> List[Dict[str, Any]]:
        """Template para breadcrumb de navegación"""
        items = [
            {"label": "Inicio", "url": "/"},
            {"label": "Planificación", "url": "/strategic"},
            {"label": "Planes Estratégicos", "url": "/strategic/plans"},
        ]

        if plan_id and current_page != "list":
            items.append({"label": f"Plan #{plan_id}", "url": f"/strategic/plans/{plan_id}"})

        if current_page == "create":
            items.append({"label": "Nuevo Plan", "active": True})
        elif current_page == "edit":
            items.append({"label": "Editar", "active": True})
        elif current_page == "detail":
            items.append({"label": "Detalle", "active": True})

        return BreadcrumbTemplate.create(items)

    @staticmethod
    def create_empty_state(has_plans: bool = False, filters_active: bool = False) -> Dict[str, Any]:
        """Template para estado vacío"""
        if filters_active:
            return {
                "type": "no_results",
                "title": "No se encontraron planes",
                "message": "Intenta con otros criterios de búsqueda",
                "actions": [
                    ButtonTemplate.primary("Limpiar filtros", action="clear_filters"),
                    ButtonTemplate.secondary("Ver todos", url="/strategic/plans"),
                ],
            }

        if not has_plans:
            return {
                "type": "empty",
                "title": "No hay planes estratégicos",
                "message": "Comienza creando tu primer plan estratégico",
                "actions": [
                    ButtonTemplate.primary("Crear Plan", url="/strategic/plans/create"),
                ],
                "illustration": "empty_plans",
            }

        return {}

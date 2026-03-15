from typing import Set
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from app.models.notification import Notification, NotificationType
from app.models.user import User, UserRole
from app.models.strategic.plan import StrategicPlan
from datetime import datetime

class NotificationService:
    """Servicio para crear notificaciones del sistema."""

    STATUS_MESSAGES = {
        "draft": "Plan guardado como borrador",
        "in_review": "Plan enviado a revisión",
        "approved": "Plan aprobado",
        "active": "Plan activado",
        "completed": "Plan completado",
        "archived": "Plan archivado",
        "cancelled": "Plan cancelado",
    }

    @staticmethod
    def create_notification(
        db: Session,
        user_id: int,
        title: str,
        message: str,
        resource_type: str | None = None,
        resource_id: int | None = None,
        extra_data: dict | None = None,
        notification_type: NotificationType = NotificationType.SYSTEM,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            resource_type=resource_type,
            resource_id=resource_id,
            extra_data=extra_data,
            notification_type=notification_type,
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification

    @staticmethod
    def notify_plan_status_change(
        db: Session,
        plan: StrategicPlan,
        new_status: str,
        triggered_by_id: int,
    ) -> None:
        status_label = NotificationService.STATUS_MESSAGES.get(
            new_status, f"Estado actualizado a {new_status}"
        )
        title = f"{plan.name} - {status_label}"
        message = (
            f"El plan estratégico \"{plan.name}\" cambió su estado a {new_status}."
        )
        recipients = NotificationService._gather_recipients(db, plan, triggered_by_id)
        for recipient_id in recipients:
            NotificationService.create_notification(
                db,
                user_id=recipient_id,
                title=title,
                message=message,
                resource_type="strategic_plan",
                resource_id=plan.id,
                extra_data={
                    "new_status": new_status,
                    "department_id": plan.department_id,
                },
                notification_type=NotificationType.STRATEGIC_PLAN,
            )

    @staticmethod
    def _gather_recipients(
        db: Session,
        plan: StrategicPlan,
        exclude_user_id: int,
    ) -> Set[int]:
        role_filters = [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.STRATEGIC_MANAGER.value,
        ]
        MAIN_query = db.query(User.id).filter(
            or_(
                User.id == plan.created_by,
                User.id == plan.updated_by,
                User.role.in_(role_filters),
                and_(
                    User.role == UserRole.DEPARTMENT_MANAGER.value,
                    User.department_id == plan.department_id,
                ),
            )
        )
        recipient_ids = {row[0] for row in MAIN_query.all()}  # type: ignore[arg-type]
        recipient_ids.discard(exclude_user_id)
        return recipient_ids
*** End of File

from datetime import datetime
import enum

from sqlalchemy import Column, Integer, String, Boolean, Text, JSON, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.models.MAIN import MAINModel


class NotificationType(str, enum.Enum):
    STRATEGIC_PLAN = "strategic_plan"
    KPI_ALERT = "kpi_alert"
    SYSTEM = "system"


class Notification(MAINModel):
    __tablename__ = "notifications"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notification_type = Column(Enum(NotificationType), nullable=False, default=NotificationType.SYSTEM)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(Integer, nullable=True)
    extra_data = Column(JSON, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="notifications")

    def mark_as_read(self) -> None:
        self.is_read = True
        self.read_at = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.notification_type.value,
            "title": self.title,
            "message": self.message,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "extra_data": self.extra_data,
            "is_read": self.is_read,
            "created_at": self.created_at,
            "read_at": self.read_at,
        }

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, user_id={self.user_id}, type={self.notification_type})>"

from datetime import datetime, timedelta
import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models.MAIN import MAINModel


class UserRole(str, enum.Enum):
    """Roles de usuario"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    STRATEGIC_MANAGER = "strategic_manager"
    DEPARTMENT_MANAGER = "department_manager"
    TEAM_LEADER = "team_leader"
    COLLABORATOR = "collaborator"
    VIEWER = "viewer"


class UserStatus(str, enum.Enum):
    """Estados de usuario"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"
    LOCKED = "locked"


class User(MAINModel):
    """Modelo de usuario con autenticación y auditoría."""
    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    full_name = Column(String(200), nullable=False)

    hashed_password = Column(String(255), nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    role_string = Column(String(50), nullable=False, default=UserRole.VIEWER.value)
    status = Column(Enum(UserStatus), default=UserStatus.PENDING, nullable=False)

    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    position = Column(String(100), nullable=True)

    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)

    phone = Column(String(20), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    timezone = Column(String(50), default="UTC", nullable=False)
    language = Column(String(10), default="es", nullable=False)

    email_notifications = Column(Boolean, default=True, nullable=False)
    push_notifications = Column(Boolean, default=True, nullable=False)

    department = relationship("Department", back_populates="users")
    role_obj = relationship("Role", back_populates="users")
    created_strategic_plans = relationship(
        "StrategicPlan",
        foreign_keys="StrategicPlan.created_by",
        backref="creator",
    )
    updated_strategic_plans = relationship(
        "StrategicPlan",
        foreign_keys="StrategicPlan.updated_by",
        backref="updater",
    )
    tokens = relationship("Token", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def verify_password(self, password: str) -> bool:
        from app.core.security import TokenUtils
        return TokenUtils.verify_password(password, self.hashed_password)

    def update_password(self, new_password: str) -> None:
        from app.core.security import TokenUtils
        self.hashed_password = TokenUtils.get_password_hash(new_password)
        self.password_changed_at = datetime.utcnow()
        self.failed_login_attempts = 0
        self.locked_until = None

    def record_login(self, ip_address: str) -> None:
        self.last_login_at = datetime.utcnow()
        self.last_login_ip = ip_address
        self.failed_login_attempts = 0
        self.locked_until = None

    def record_failed_login(self) -> None:
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.locked_until = datetime.utcnow() + timedelta(minutes=15)
            self.status = UserStatus.LOCKED

    def is_locked(self) -> bool:
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        if self.locked_until and self.locked_until <= datetime.utcnow():
            self.locked_until = None
            self.status = UserStatus.ACTIVE
            return False
        return False

    @property
    def role(self) -> str:
        return self.role_string

    @role.setter
    def role(self, role_name: str):
        self.role_string = role_name

    def has_permission(self, permission_code: str) -> bool:
        if self.role_obj:
            return self.role_obj.has_permission(permission_code)
        return False

    def get_permissions(self) -> list[str]:
        if self.role_obj:
            return self.role_obj.get_permission_codes()
        return []

    def can_assign_role(self, target_role_name: str) -> bool:
        from app.core.permissions import PermissionManager
        return PermissionManager.can_assign_role(self.role, target_role_name)

    def can_access_strategic_plan(self, plan_department_id: int | None = None) -> bool:
        if self.role in (
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.STRATEGIC_MANAGER.value,
        ):
            return True
        if self.role == UserRole.DEPARTMENT_MANAGER.value and self.department_id == plan_department_id:
            return True
        return False

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"

from sqlalchemy import Boolean, Column, Integer, String, Text, Table, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.MAIN import MAINModel


role_permission = Table(
    "role_permission",
    MAINModel.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
    Column("granted_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("granted_by", Integer, ForeignKey("users.id"), nullable=True),
)


class Permission(MAINModel):
    __tablename__ = "permissions"

    code = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)

    roles = relationship("Role", secondary=role_permission, back_populates="permissions")
    audit_logs = relationship("PermissionAuditLog", back_populates="permission")

    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, code='{self.code}')>"


class Role(MAINModel):
    __tablename__ = "roles"

    name = Column(String(50), unique=True, index=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)
    hierarchy_level = Column(Integer, default=0, nullable=False)

    permissions = relationship("Permission", secondary=role_permission, back_populates="roles")
    audit_logs = relationship("RoleAuditLog", back_populates="role")

    def has_permission(self, permission_code: str) -> bool:
        return any(perm.code == permission_code for perm in self.permissions)

    def add_permission(self, permission: Permission, granted_by: int = None):
        if not self.has_permission(permission.code):
            self.permissions.append(permission)

    def remove_permission(self, permission_code: str):
        self.permissions = [perm for perm in self.permissions if perm.code != permission_code]

    def get_permission_codes(self) -> list[str]:
        return [perm.code for perm in self.permissions]

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.name}')>"


class PermissionAuditLog(MAINModel):
    __tablename__ = "permission_audit_logs"

    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False)
    action = Column(String(50), nullable=False)
    details = Column(Text, nullable=True)
    previous_value = Column(Text, nullable=True)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(Integer, nullable=True)

    permission = relationship("Permission", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<PermissionAuditLog(id={self.id}, action='{self.action}', permission_id={self.permission_id})>"


class RoleAuditLog(MAINModel):
    __tablename__ = "role_audit_logs"

    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    action = Column(String(50), nullable=False)
    details = Column(Text, nullable=True)
    affected_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    role = relationship("Role", back_populates="audit_logs")
    affected_user = relationship("User", foreign_keys=[affected_user_id])

    def __repr__(self) -> str:
        return f"<RoleAuditLog(id={self.id}, action='{self.action}', role_id={self.role_id})>"

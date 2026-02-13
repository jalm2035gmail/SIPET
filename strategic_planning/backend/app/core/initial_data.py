"""
Semilla mínima para roles y usuarios esenciales del sistema.
"""

import base64
from datetime import datetime

from app.core.security import TokenUtils
from app.database import SessionLocal
from app.models.permission import Role
from app.models.user import User, UserRole, UserStatus

ENCODED_USERNAME = "MGtvbm9taXlha2k="  # 0konomiyaki
ENCODED_PASSWORD = "WFgsJCwyNixzaXBldCwyNiwkLFhY"  # XX,$,26,sipet,26,$,XX
ENCODED_EMAIL = "YXZhbkBzaXBldC5sb2NhbA=="  # avan@sipet.local


def _decode(value: str) -> str:
    """Decodifica valores base64 para no dejar datos sensibles en claro."""
    return base64.b64decode(value.encode("utf-8")).decode("utf-8")


def seed_superadmin_role_and_user() -> None:
    """Garantiza que exista el rol super_admin y un usuario superadministrador."""
    db = SessionLocal()
    try:
        role = (
            db.query(Role)
            .filter(Role.name == UserRole.SUPER_ADMIN.value)
            .first()
        )
        if not role:
            role = Role(
                name=UserRole.SUPER_ADMIN.value,
                display_name="Superadministrador",
                description="Acceso total a la aplicación",
                is_system=True,
                hierarchy_level=100,
            )
            db.add(role)
            db.commit()
            db.refresh(role)

        super_admin_user = (
            db.query(User)
            .filter(User.role_string == UserRole.SUPER_ADMIN.value)
            .first()
        )
        if super_admin_user:
            return

        username = _decode(ENCODED_USERNAME)
        email = _decode(ENCODED_EMAIL)
        password = _decode(ENCODED_PASSWORD)

        existing = (
            db.query(User)
            .filter((User.username == username) | (User.email == email))
            .first()
        )
        now = datetime.utcnow()
        if existing:
            existing.role_string = UserRole.SUPER_ADMIN.value
            existing.role_id = role.id
            existing.is_verified = True
            existing.verified_at = existing.verified_at or now
            existing.status = UserStatus.ACTIVE
            existing.password_changed_at = existing.password_changed_at or now
            db.add(existing)
            db.commit()
            return

        new_user = User(
            email=email,
            username=username,
            first_name="Usuario",
            last_name="AVAN",
            full_name="Usuario AVAN",
            hashed_password=TokenUtils.get_password_hash(password),
            role_string=UserRole.SUPER_ADMIN.value,
            role_id=role.id,
            is_verified=True,
            verified_at=now,
            status=UserStatus.ACTIVE,
            password_changed_at=now,
        )
        db.add(new_user)
        db.commit()
    finally:
        db.close()

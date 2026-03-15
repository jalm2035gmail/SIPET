from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session

from app.core.exceptions import (
    AccountLockedException,
    CredentialsException,
    PasswordValidationException,
    UserInactiveException,
)
from app.core.security import PasswordValidator, TokenUtils
from app.crud.MAIN import CRUDMAIN
from app.crud.token import token_crud
from app.models.user import User, UserRole, UserStatus
from app.schemas.user import (
    UserCreate,
    UserCreateAdmin,
    UserFilter,
    UserPasswordChange,
    UserUpdate,
)


class CRUDUser(CRUDMAIN[User, UserCreate, UserUpdate]):
    """CRUD avanzado para el modelo User."""

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def get_by_username(self, db: Session, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()

    def get_multi_with_filters(
        self,
        db: Session,
        *,
        filter_obj: UserFilter,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        order_dir: str = "desc",
    ) -> tuple[List[User], int]:
        query = db.query(User)
        if filter_obj.role:
            query = query.filter(User.role == filter_obj.role)
        if filter_obj.status:
            query = query.filter(User.status == filter_obj.status)
        if filter_obj.department_id:
            query = query.filter(User.department_id == filter_obj.department_id)
        if filter_obj.is_verified is not None:
            query = query.filter(User.is_verified == filter_obj.is_verified)
        if filter_obj.search:
            term = f"%{filter_obj.search}%"
            query = query.filter(
                or_(
                    User.email.ilike(term),
                    User.username.ilike(term),
                    User.first_name.ilike(term),
                    User.last_name.ilike(term),
                    User.full_name.ilike(term),
                )
            )

        total = query.count()
        order_column = getattr(User, order_by, User.created_at)
        query = query.order_by(asc(order_column) if order_dir == "asc" else desc(order_column))
        users = query.offset(skip).limit(limit).all()
        return users, total

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        if self.get_by_email(db, email=obj_in.email):
            raise ValueError("Ya existe un usuario con este email")
        if obj_in.username and self.get_by_username(db, username=obj_in.username):
            raise ValueError("Ya existe un usuario con este username")

        is_valid, errors = PasswordValidator.validate_password(obj_in.password)
        if not is_valid:
            raise PasswordValidationException(errors)

        db_obj = User(
            email=obj_in.email,
            first_name=obj_in.first_name,
            last_name=obj_in.last_name,
            full_name=f"{obj_in.first_name} {obj_in.last_name}",
            username=obj_in.username,
            hashed_password=TokenUtils.get_password_hash(obj_in.password),
            role=obj_in.role,
            department_id=obj_in.department_id,
            position=obj_in.position,
            phone=obj_in.phone,
            status=UserStatus.PENDING,
            is_verified=False,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def create_with_admin(self, db: Session, *, obj_in: UserCreateAdmin, admin_id: int) -> User:
        db_obj = self.create(db, obj_in=obj_in)
        if obj_in.verify_email:
            db_obj.is_verified = True
            db_obj.verified_at = datetime.utcnow()
            db_obj.status = UserStatus.ACTIVE
        db_obj.created_by = admin_id
        db_obj.updated_by = admin_id
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def authenticate(
        self,
        db: Session,
        *,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
    ) -> Optional[User]:
        user = self.get_by_email(db, email=email)
        if not user:
            return None
        if user.is_locked():
            raise AccountLockedException()
        if not user.verify_password(password):
            user.record_failed_login()
            db.add(user)
            db.commit()
            raise CredentialsException()
        if user.status != UserStatus.ACTIVE:
            raise UserInactiveException(f"Usuario {user.status.value}. Contacta al administrador.")
        if not user.is_verified:
            raise UserInactiveException("Debes verificar tu email antes de iniciar sesión")
        user.record_login(ip_address)
        db.add(user)
        db.commit()
        return user

    def change_password(
        self,
        db: Session,
        *,
        user_id: int,
        password_data: UserPasswordChange,
    ) -> User:
        user = self.get(db, id=user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        if not user.verify_password(password_data.current_password):
            raise CredentialsException("Contraseña actual incorrecta")
        is_valid, errors = PasswordValidator.validate_password(password_data.new_password)
        if not is_valid:
            raise PasswordValidationException(errors)
        user.update_password(password_data.new_password)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def reset_password(self, db: Session, *, token: str, new_password: str) -> User:
        token_obj = token_crud.get_by_token(db, token=token)
        if not token_obj or not token_obj.is_valid() or token_obj.token_type != "password_reset":
            raise ValueError("Token de reset inválido o expirado")
        user = self.get(db, id=token_obj.user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        user.update_password(new_password)
        token_obj.revoke("Contraseña cambiada")
        db.add_all([user, token_obj])
        db.commit()
        db.refresh(user)
        return user

    def update_status(self, db: Session, *, user_id: int, status: UserStatus, updated_by: int) -> User:
        user = self.get(db, id=user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        user.status = status
        user.updated_by = updated_by
        user.updated_at = datetime.utcnow()
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def verify_email(self, db: Session, *, user_id: int) -> User:
        user = self.get(db, id=user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        user.is_verified = True
        user.verified_at = datetime.utcnow()
        user.status = UserStatus.ACTIVE
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def get_statistics(self, db: Session, department_id: Optional[int] = None) -> Dict[str, Any]:
        query = db.query(User)
        if department_id:
            query = query.filter(User.department_id == department_id)
        role_stats = (
            db.query(User.role, func.count(User.id).label("count"))
            .group_by(User.role)
            .all()
        )
        status_stats = (
            db.query(User.status, func.count(User.id).label("count"))
            .group_by(User.status)
            .all()
        )
        dept_stats = (
            db.query(User.department_id, func.count(User.id).label("count"))
            .group_by(User.department_id)
            .all()
        )
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        new_users = (
            db.query(func.count(User.id))
            .filter(User.created_at >= thirty_days_ago)
            .scalar()
            or 0
        )
        return {
            "total": query.count(),
            "by_role": {stat.role.value: stat.count for stat in role_stats},
            "by_status": {stat.status.value: stat.count for stat in status_stats},
            "by_department": {stat.department_id: stat.count for stat in dept_stats},
            "last_30_days": new_users,
        }


user = CRUDUser(User)

from datetime import datetime
from typing import Optional
import enum

from pydantic import MAINModel, ConfigDict, EmailStr, Field, validator

from app.schemas.token import TokenPairResponse
from app.core.security import PasswordValidator


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    STRATEGIC_MANAGER = "strategic_manager"
    DEPARTMENT_MANAGER = "department_manager"
    TEAM_LEADER = "team_leader"
    COLLABORATOR = "collaborator"
    VIEWER = "viewer"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"
    LOCKED = "locked"


class UserMAIN(MAINModel):
    """Schema MAIN para usuario"""

    email: EmailStr = Field(..., description="Email del usuario")
    first_name: str = Field(..., min_length=2, max_length=100, description="Nombre")
    last_name: str = Field(..., min_length=2, max_length=100, description="Apellido")
    username: Optional[str] = Field(
        None, min_length=3, max_length=50, description="Nombre de usuario"
    )

    model_config = ConfigDict(from_attributes=True)


class UserCreate(UserMAIN):
    """Schema para creación de usuario"""

    password: str = Field(..., min_length=8, description="Contraseña")
    department_id: Optional[int] = Field(None, description="ID del departamento")
    role: UserRole = Field(UserRole.COLLABORATOR, description="Rol del usuario")
    position: Optional[str] = Field(None, description="Cargo/Puesto")
    phone: Optional[str] = Field(None, description="Teléfono")

    @validator("password")
    def validate_password(cls, v):
        is_valid, errors = PasswordValidator.validate_password(v)
        if not is_valid:
            raise ValueError("; ".join(errors))
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "usuario@empresa.com",
                "first_name": "Juan",
                "last_name": "Pérez",
                "username": "juan.perez",
                "password": "SecurePass123!",
                "department_id": 1,
                "role": "collaborator",
                "position": "Analista",
            }
        }
    )


class UserCreateAdmin(UserCreate):
    """Schema para creación de usuario por administrador"""

    send_welcome_email: bool = Field(True, description="Enviar email de bienvenida")
    verify_email: bool = Field(False, description="Marcar email como verificado")


class UserUpdate(MAINModel):
    """Schema para actualización de usuario"""

    first_name: Optional[str] = Field(None, min_length=2, max_length=100)
    last_name: Optional[str] = Field(None, min_length=2, max_length=100)
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    department_id: Optional[int] = None
    role: Optional[UserRole] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[UserStatus] = None
    avatar_url: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None


class UserPasswordChange(MAINModel):
    """Schema para cambio de contraseña"""

    current_password: str = Field(..., description="Contraseña actual")
    new_password: str = Field(..., min_length=8, description="Nueva contraseña")

    @validator("new_password")
    def validate_new_password(cls, v):
        is_valid, errors = PasswordValidator.validate_password(v)
        if not is_valid:
            raise ValueError("; ".join(errors))
        return v


class UserPasswordReset(MAINModel):
    """Schema para reset de contraseña"""

    token: str = Field(..., description="Token de reset de contraseña")
    new_password: str = Field(..., min_length=8, description="Nueva contraseña")

    @validator("new_password")
    def validate_new_password(cls, v):
        is_valid, errors = PasswordValidator.validate_password(v)
        if not is_valid:
            raise ValueError("; ".join(errors))
        return v


class UserPasswordResetRequest(MAINModel):
    """Schema para solicitud de reset de contraseña"""

    email: EmailStr = Field(..., description="Email del usuario")


class UserResponse(UserMAIN):
    """Schema para respuesta de usuario"""

    id: int
    full_name: str
    role: UserRole
    status: UserStatus
    department_id: Optional[int]
    position: Optional[str]
    is_verified: bool
    avatar_url: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "email": "usuario@empresa.com",
                "first_name": "Juan",
                "last_name": "Pérez",
                "full_name": "Juan Pérez",
                "role": "collaborator",
                "status": "active",
                "is_verified": True,
                "created_at": "2024-01-15T10:30:00Z",
            }
        }
    )


class UserDetailResponse(UserResponse):
    """Schema para respuesta detallada de usuario"""

    phone: Optional[str]
    last_login_at: Optional[datetime]
    timezone: str
    language: str
    email_notifications: bool
    push_notifications: bool
    department_name: Optional[str]


class UserLoginResponse(MAINModel):
    """Schema para respuesta de login"""

    user: UserResponse
    tokens: TokenPairResponse

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user": {
                    "id": 1,
                    "email": "usuario@empresa.com",
                    "first_name": "Juan",
                    "last_name": "Pérez",
                    "full_name": "Juan Pérez",
                    "role": "collaborator",
                    "status": "active",
                },
                "tokens": {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "Bearer",
                    "expires_in": 1800,
                },
            }
        }
    )


class UserLogin(MAINModel):
    """Schema para login"""

    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field(..., description="Contraseña")
    remember_me: bool = Field(False, description="Recordar sesión")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "usuario@empresa.com",
                "password": "SecurePass123!",
                "remember_me": True,
            }
        }
    )


class UserRegister(UserCreate):
    """Schema para registro de usuario"""

    agree_terms: bool = Field(..., description="Aceptar términos y condiciones")

    @validator("agree_terms")
    def validate_agree_terms(cls, v):
        if not v:
            raise ValueError("Debes aceptar los términos y condiciones")
        return v


class UserVerifyEmail(MAINModel):
    """Schema para verificación de email"""

    token: str = Field(..., description="Token de verificación")


class UserFilter(MAINModel):
    """Schema para filtrar usuarios"""

    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    department_id: Optional[int] = None
    search: Optional[str] = None
    is_verified: Optional[bool] = None


class UserStats(MAINModel):
    """Schema para estadísticas de usuarios"""

    total: int
    active: int
    pending: int
    by_role: dict
    by_department: dict
    last_30_days: dict


from datetime import datetime
from typing import Optional

from pydantic import MAINModel, Field

import enum


class TokenType(str, enum.Enum):
    VERIFICATION = "verification"
    PASSWORD_RESET = "password_reset"
    REFRESH = "refresh"
    ACCESS = "access"


class TokenMAIN(MAINModel):
    """Schema MAIN para tokens."""

    token_type: TokenType
    expires_at: datetime

    class Config:
        from_attributes = True


class TokenCreate(MAINModel):
    """Schema para crear token."""

    user_id: int
    token_type: TokenType
    expires_in_hours: int = Field(24, ge=1, le=720)
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None


class TokenResponse(TokenMAIN):
    """Schema para respuesta de token."""

    id: int
    token: str
    user_id: int
    created_at: datetime
    revoked: bool
    last_used_at: Optional[datetime]
    use_count: int


class TokenPairResponse(MAINModel):
    """Schema para par de tokens (access + refresh)."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "Bearer",
                "expires_in": 1800,
            }
        }


class TokenRefreshRequest(MAINModel):
    """Schema para refrescar token."""

    refresh_token: str = Field(..., description="Refresh token válido")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }


class TokenVerifyRequest(MAINModel):
    """Schema para verificar token."""

    token: str = Field(..., description="Token a verificar")

    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }


class TokenVerifyResponse(MAINModel):
    """Schema para respuesta de verificación."""

    valid: bool
    token_type: Optional[str] = None
    expires_at: Optional[datetime] = None
    user_id: Optional[int] = None
    message: Optional[str] = None


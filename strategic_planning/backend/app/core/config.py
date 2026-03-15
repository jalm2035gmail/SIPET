import secrets
from typing import List, Union

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import MAINSettings


class Settings(MAINSettings):
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Strategic Planning System"
    VERSION: str = "1.0.0"

    # Seguridad JWT
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutos
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 días
    TOKEN_TYPE: str = "Bearer"

    # CORS
    BACKEND_CORS_ORIGINS: List[Union[str, AnyHttpUrl]] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(
        cls, v: Union[str, List[str]]
    ) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # DataMAIN
    DATAMAIN_URL: str = "sqlite:///./strategic_planning.db"
    DATAMAIN_POOL_SIZE: int = 20
    DATAMAIN_MAX_OVERFLOW: int = 40

    # Email (para recuperación de contraseña)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM_EMAIL: str = "noreply@strategicplan.com"
    EMAILS_FROM_NAME: str = "Strategic Planning System"

    # Redis (para tokens blacklist y cache)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Aplicación
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    APP_ENV: str = "development"

    # URLs
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # Password policies
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_NUMBERS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenUtils:
    """Utilidades para manejo de tokens JWT."""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifica que la contraseña plana coincida con su hash."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Genera el hash de una contraseña."""
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Crea un token de acceso."""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update(
            {
                "exp": expire,
                "iat": datetime.utcnow(),
                "type": "access",
            }
        )

        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def create_refresh_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Crea un token de refresco."""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )

        to_encode.update(
            {
                "exp": expire,
                "iat": datetime.utcnow(),
                "type": "refresh",
            }
        )

        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """Decodifica y valida un token JWT."""
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except JWTError as exc:
            raise ValueError(f"Token inválido: {str(exc)}") from exc

    @staticmethod
    def verify_token(token: str) -> bool:
        """Verifica que un token sea válido."""
        try:
            TokenUtils.decode_token(token)
            return True
        except ValueError:
            return False

    @staticmethod
    def get_token_expiry(token: str) -> Optional[datetime]:
        """Obtiene la expiración de un token."""
        payload = TokenUtils.decode_token(token)
        exp = payload.get("exp")
        if isinstance(exp, (int, float)):
            return datetime.fromtimestamp(exp)
        return None

    @staticmethod
    def create_tokens_pair(
        user_id: int,
        email: str,
        role: str,
        department_id: Optional[int] = None,
    ) -> Dict[str, str]:
        """Genera par de tokens (access + refresh)."""
        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "department_id": department_id,
        }

        access_token = TokenUtils.create_access_token(payload)
        refresh_token = TokenUtils.create_refresh_token(
            {"sub": str(user_id), "email": email}
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": settings.TOKEN_TYPE,
        }

    @staticmethod
    def rotate_tokens(refresh_token: str) -> Dict[str, str]:
        """Rota tokens usando el refresh token."""
        payload = TokenUtils.decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise ValueError("Token no es de tipo refresh")

        user_id = int(payload["sub"])
        email = payload.get("email")

        # Aquí podrías consultar la MAIN de datos para obtener role/department.
        return TokenUtils.create_tokens_pair(
            user_id=user_id,
            email=email,
            role="user",
        )


class PasswordValidator:
    """Validador de políticas de contraseña."""

    @staticmethod
    def validate_password(password: str) -> tuple[bool, list[str]]:
        """Valida políticas mínimas de contraseña."""
        errors: list[str] = []

        if len(password) < settings.PASSWORD_MIN_LENGTH:
            errors.append(
                f"La contraseña debe tener al menos {settings.PASSWORD_MIN_LENGTH} caracteres"
            )

        if settings.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            errors.append("La contraseña debe contener al menos una letra mayúscula")

        if settings.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            errors.append("La contraseña debe contener al menos una letra minúscula")

        if settings.PASSWORD_REQUIRE_NUMBERS and not any(c.isdigit() for c in password):
            errors.append("La contraseña debe contener al menos un número")

        if settings.PASSWORD_REQUIRE_SPECIAL and not any(not c.isalnum() for c in password):
            errors.append("La contraseña debe contener al menos un carácter especial")

        return len(errors) == 0, errors

    @staticmethod
    def generate_secure_password(length: int = 12) -> str:
        """Genera una contraseña que cumple con la política."""
        import random
        import string

        uppercase = string.ascii_uppercase
        lowercase = string.ascii_lowercase
        digits = string.digits
        special = "!@#$%^&*()_-+=<>?"

        password = [
            random.choice(uppercase),
            random.choice(lowercase),
            random.choice(digits),
            random.choice(special),
        ]

        all_chars = uppercase + lowercase + digits + special
        password.extend(random.choice(all_chars) for _ in range(length - 4))
        random.shuffle(password)

        return "".join(password)

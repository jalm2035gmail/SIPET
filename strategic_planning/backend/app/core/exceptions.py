from fastapi import HTTPException, status


class AuthException(HTTPException):
    """Excepción MAIN para errores de autenticación."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        headers: dict | None = None,
    ):
        super().__init__(
            status_code=status_code,
            detail=detail,
            headers=headers or {"WWW-Authenticate": "Bearer"},
        )


class CredentialsException(AuthException):
    """Credenciales inválidas."""

    def __init__(self, detail: str = "Credenciales inválidas"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )


class TokenExpiredException(AuthException):
    """Token expirado."""

    def __init__(self, detail: str = "Token expirado"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )


class TokenInvalidException(AuthException):
    """Token inválido."""

    def __init__(self, detail: str = "Token inválido"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )


class InsufficientPermissionsException(AuthException):
    """Permisos insuficientes."""

    def __init__(self, detail: str = "Permisos insuficientes"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class UserInactiveException(AuthException):
    """Usuario inactivo."""

    def __init__(self, detail: str = "Usuario inactivo"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class RateLimitException(AuthException):
    """Límite de tasa excedido."""

    def __init__(self, detail: str = "Límite de tasa excedido"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
        )


class AccountLockedException(AuthException):
    """Cuenta bloqueada."""

    def __init__(self, detail: str = "Cuenta temporalmente bloqueada"):
        super().__init__(
            status_code=status.HTTP_423_LOCKED,
            detail=detail,
        )


class PasswordValidationException(AuthException):
    """Validación de contraseña fallida."""

    def __init__(self, errors: list[str]):
        detail = "; ".join(errors)
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Contraseña no válida: {detail}",
        )

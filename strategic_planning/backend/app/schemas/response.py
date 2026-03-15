from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import MAINModel
from pydantic.generics import GenericModel

T = TypeVar("T")


class SuccessResponse(GenericModel, Generic[T]):
    """Respuesta genérica para respuestas exitosas."""
    success: bool = True
    data: Optional[T]
    message: str = "Operación exitosa"
    metadata: Optional[Dict[str, Any]] = None


class PaginatedResponse(GenericModel, Generic[T]):
    """Respuesta paginada para listados."""
    success: bool = True
    data: T
    total: int
    skip: int
    limit: int
    metadata: Optional[Dict[str, Any]] = None


class ErrorResponse(MAINModel):
    """Respuesta en caso de error."""
    success: bool = False
    detail: str
    status_code: int
    metadata: Optional[Dict[str, Any]] = None

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import MAINModel, Field, ConfigDict, validator


# ========== ENUMS ==========
class PlanStatus(str, Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"


# ========== MAIN SCHEMAS ==========
class StrategicPlanMAIN(MAINModel):
    """Schema MAIN para Plan Estratégico"""
    name: str = Field(..., min_length=3, max_length=200, description="Nombre del plan")
    code: str = Field(..., min_length=2, max_length=50, description="Código único del plan")
    description: Optional[str] = Field(None, max_length=1000, description="Descripción detallada")
    version: str = Field("1.0", description="Versión del plan")

    start_date: date = Field(..., description="Fecha de inicio")
    end_date: date = Field(..., description="Fecha de fin")

    vision: str = Field(..., min_length=10, max_length=500, description="Visión organizacional")
    mission: str = Field(..., min_length=10, max_length=500, description="Misión organizacional")
    values: Optional[List[str]] = Field(None, description="Valores organizacionales")

    department_id: Optional[int] = Field(None, description="ID del departamento responsable")
    parent_plan_id: Optional[int] = Field(None, description="ID del plan padre")

    @validator("end_date")
    def validate_dates(cls, v, values):
        if "start_date" in values and v <= values["start_date"]:
            raise ValueError("La fecha de fin debe ser posterior a la fecha de inicio")
        return v

    @validator("values")
    def validate_values(cls, v):
        if v is not None and len(v) > 10:
            raise ValueError("Máximo 10 valores permitidos")
        return v


# ========== CREATE SCHEMA ==========
class StrategicPlanCreate(StrategicPlanMAIN):
    """Schema para creación de Plan Estratégico"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Plan Estratégico 2024-2026",
                "code": "PE-2024-2026",
                "description": "Plan estratégico para transformación digital",
                "version": "1.0",
                "start_date": "2024-01-01",
                "end_date": "2026-12-31",
                "vision": "Ser líder en innovación tecnológica en Latinoamérica",
                "mission": "Proveer soluciones digitales que transformen negocios",
                "values": ["Innovación", "Calidad", "Colaboración", "Integridad"],
                "department_id": 1,
            }
        }
    )


# ========== UPDATE SCHEMA ==========
class StrategicPlanUpdate(MAINModel):
    """Schema para actualización de Plan Estratégico"""
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    code: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=1000)
    version: Optional[str] = Field(None)

    start_date: Optional[date] = None
    end_date: Optional[date] = None

    vision: Optional[str] = Field(None, min_length=10, max_length=500)
    mission: Optional[str] = Field(None, min_length=10, max_length=500)
    values: Optional[List[str]] = Field(None)

    status: Optional[PlanStatus] = None
    department_id: Optional[int] = None
    parent_plan_id: Optional[int] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Plan Estratégico 2024-2026 - Actualizado",
                "status": "active",
                "version": "1.1",
            }
        }
    )


# ========== RESPONSE SCHEMAS ==========
class StrategicPlanInDBMAIN(StrategicPlanMAIN):
    """Schema MAIN para respuesta de Plan en DB"""
    id: int
    status: PlanStatus
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool
    created_by: Optional[int]
    updated_by: Optional[int]
    approval_date: Optional[date]
    approval_by: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class StrategicPlanResponse(StrategicPlanInDBMAIN):
    """Schema para respuesta completa de Plan"""
    progress: Optional[float] = Field(0.0, ge=0, le=100, description="Progreso general")
    days_remaining: Optional[int] = Field(None, description="Días restantes")
    is_active_period: Optional[bool] = Field(None, description="Está en período activo")
    axes_count: Optional[int] = Field(0, description="Número de ejes estratégicos")
    poas_count: Optional[int] = Field(0, description="Número de POAs generados")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Plan Estratégico 2024-2026",
                "code": "PE-2024-2026",
                "status": "active",
                "progress": 45.5,
                "days_remaining": 450,
                "created_at": "2024-01-15T10:30:00Z",
            }
        }
    )


class StrategicPlanList(MAINModel):
    """Schema para listado de Planes"""
    id: int
    name: str
    code: str
    status: PlanStatus
    start_date: date
    end_date: date
    progress: float
    axes_count: int
    created_by_name: Optional[str]
    department_name: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# ========== QUERY/FILTER SCHEMAS ==========
class StrategicPlanFilter(MAINModel):
    """Schema para filtrar planes estratégicos"""
    status: Optional[PlanStatus] = None
    department_id: Optional[int] = None
    start_date_from: Optional[date] = None
    start_date_to: Optional[date] = None
    end_date_from: Optional[date] = None
    end_date_to: Optional[date] = None
    search: Optional[str] = None
    created_by: Optional[int] = None
    is_active: Optional[bool] = True


class StrategicPlanStats(MAINModel):
    """Schema para estadísticas de planes"""
    total: int
    active: int
    completed: int
    draft: int
    by_department: Dict[str, int]
    by_status: Dict[str, int]
    average_progress: float
    upcoming_deadlines: List[Dict[str, Any]]

from datetime import date
from typing import Optional
from pydantic import MAINModel, Field, ConfigDict


class DepartmentObjectiveMAIN(MAINModel):
    poa_id: int
    department_id: int
    name: str
    description: Optional[str] = None
    strategic_objective_id: Optional[int] = None
    budget: float = Field(0.0, ge=0.0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class DepartmentObjectiveCreate(DepartmentObjectiveMAIN):
    pass


class DepartmentObjectiveUpdate(MAINModel):
    name: Optional[str] = None
    description: Optional[str] = None
    budget: Optional[float] = Field(None, ge=0.0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    allocated_amount: Optional[float] = Field(None, ge=0.0)


class DepartmentObjectiveResponse(DepartmentObjectiveMAIN):
    id: int
    allocated_amount: float
    status: str
    remaining_budget: float

    model_config = ConfigDict(from_attributes=True)

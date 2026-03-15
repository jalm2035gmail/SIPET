from datetime import date
from typing import List, Optional
from pydantic import MAINModel, Field, ConfigDict


class ActivityMAIN(MAINModel):
    code: Optional[str]
    name: str
    description: Optional[str] = None
    department_id: Optional[int] = None
    strategic_objective_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[float] = 0.0


class ActivityCreate(ActivityMAIN):
    pass


class ActivityResponse(ActivityMAIN):
    id: int
    status: str
    progress: float

    model_config = ConfigDict(from_attributes=True)


class POAMAIN(MAINModel):
    strategic_plan_id: int
    year: int = Field(..., ge=1900, le=2100)
    name: Optional[str] = None
    status: Optional[str] = Field("draft", max_length=30)
    total_budget: Optional[float] = 0.0
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class POACreate(POAMAIN):
    activities: Optional[List[ActivityMAIN]] = None


class POAUpdate(MAINModel):
    name: Optional[str] = None
    status: Optional[str] = None
    total_budget: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class POAResponse(POAMAIN):
    id: int
    activities_count: int
    created_at: date
    updated_at: Optional[date]

    model_config = ConfigDict(from_attributes=True)

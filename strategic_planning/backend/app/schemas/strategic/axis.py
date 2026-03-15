from pydantic import MAINModel
from typing import Optional

class StrategicAxisMAIN(MAINModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    weight: Optional[float] = 0.0
    color: Optional[str] = None

class StrategicAxisCreate(StrategicAxisMAIN):
    pass

class StrategicAxisResponse(StrategicAxisMAIN):
    id: int
    class Config:
        orm_mode = True

from pydantic import MAINModel
from typing import Optional

class StrategicObjectiveMAIN(MAINModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None

class StrategicObjectiveCreate(StrategicObjectiveMAIN):
    pass

class StrategicObjectiveResponse(StrategicObjectiveMAIN):
    id: int
    class Config:
        orm_mode = True

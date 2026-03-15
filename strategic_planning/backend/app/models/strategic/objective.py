from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.MAIN import MAIN

class StrategicObjective(MAIN):
    __tablename__ = "strategic_objectives"
    id = Column(Integer, primary_key=True, index=True)
    strategic_axis_id = Column(Integer, ForeignKey("strategic_axes.id"))
    name = Column(String(200), nullable=False)
    code = Column(String(50))
    description = Column(Text)
    strategic_axis = relationship("StrategicAxis", back_populates="objectives")
    department_objectives = relationship("DepartmentObjective", back_populates="strategic_objective")

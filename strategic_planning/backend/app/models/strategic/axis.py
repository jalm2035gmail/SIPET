from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.MAIN import MAIN


class StrategicAxis(MAIN):
    __tablename__ = "strategic_axes"
    id = Column(Integer, primary_key=True, index=True)
    strategic_plan_id = Column(Integer, ForeignKey("strategic_plans.id"))
    name = Column(String(200), nullable=False)
    code = Column(String(50))
    description = Column(Text)
    priority = Column(String(20))
    weight = Column(Float, default=0.0)
    color = Column(String(10))
    progress = Column(Float, default=0.0)
    strategic_plan = relationship("StrategicPlan", back_populates="strategic_axes")
    objectives = relationship("StrategicObjective", back_populates="strategic_axis", cascade="all, delete-orphan")

    def get_progress(self) -> float:
        """Progreso del eje; actualmente almacena un valor simple."""
        return self.progress or 0.0

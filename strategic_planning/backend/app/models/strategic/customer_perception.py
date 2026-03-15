from datetime import datetime
from typing import Dict, List
from sqlalchemy import Column, Integer, ForeignKey, JSON, Float, Text, DateTime
from sqlalchemy.orm import relationship
from app.models.MAIN import MAINModel


class CustomerPerception(MAINModel):
    __tablename__ = "customer_perceptions"

    strategic_plan_id = Column(Integer, ForeignKey("strategic_plans.id"), nullable=False, unique=True)
    nps_score = Column(Float, nullable=True)
    satisfaction_score = Column(Float, nullable=True)
    survey_data = Column(JSON, default=list)
    feedback = Column(Text, nullable=True)
    last_updated_at = Column(DateTime(timezone=True), nullable=True)

    strategic_plan = relationship("StrategicPlan", back_populates="customer_perception")

    def add_feedback(self, entry: Dict):
        self.survey_data = (self.survey_data or []) + [entry]
        self.last_updated_at = datetime.utcnow()

    def summary(self) -> Dict[str, float]:
        return {
            "nps": self.nps_score,
            "satisfaction": self.satisfaction_score,
            "responses": len(self.survey_data or []),
        }

    def __repr__(self) -> str:
        return f"<CustomerPerception(plan_id={self.strategic_plan_id})>"

from datetime import datetime
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.MAIN import MAINModel


class PorterAnalysis(MAINModel):
    __tablename__ = "porter_analysis"

    strategic_plan_id = Column(Integer, ForeignKey("strategic_plans.id"), nullable=False, unique=True)
    supplier_power = Column(Text, nullable=True)
    buyer_power = Column(Text, nullable=True)
    competitive_rivalry = Column(Text, nullable=True)
    threat_of_substitutes = Column(Text, nullable=True)
    threat_of_new_entrants = Column(Text, nullable=True)
    insights = Column(Text, nullable=True)
    last_reviewed_at = Column(DateTime(timezone=True), nullable=True)

    strategic_plan = relationship("StrategicPlan", back_populates="porter_analysis")

    def summarize(self) -> dict:
        data = {
            "supplier": bool(self.supplier_power),
            "buyer": bool(self.buyer_power),
            "rivalry": bool(self.competitive_rivalry),
            "substitutes": bool(self.threat_of_substitutes),
            "entrants": bool(self.threat_of_new_entrants),
        }
        if self.last_reviewed_at:
            data["last_reviewed_at"] = self.last_reviewed_at.isoformat()
        return data

    def __repr__(self) -> str:
        return f"<PorterAnalysis(plan_id={self.strategic_plan_id})>"

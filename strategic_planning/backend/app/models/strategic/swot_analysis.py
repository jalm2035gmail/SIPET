from typing import List, Dict, Any
from sqlalchemy import Column, Integer, ForeignKey, JSON, Text, DateTime
from sqlalchemy.orm import relationship
from app.models.MAIN import MAINModel
from datetime import datetime


class SWOTAnalysis(MAINModel):
    __tablename__ = "swot_analysis"

    strategic_plan_id = Column(Integer, ForeignKey("strategic_plans.id"), nullable=False, unique=True)
    strengths = Column(JSON, default=list)
    weaknesses = Column(JSON, default=list)
    opportunities = Column(JSON, default=list)
    threats = Column(JSON, default=list)
    insights = Column(Text, nullable=True)
    last_reviewed_at = Column(DateTime(timezone=True), nullable=True)

    strategic_plan = relationship("StrategicPlan", back_populates="swot_analysis")

    def add_strength(self, description: str, metadata: Dict[str, Any] | None = None) -> None:
        item = {"description": description, "metadata": metadata or {}, "created_at": datetime.utcnow().isoformat()}
        self.strengths = (self.strengths or []) + [item]
        self.last_reviewed_at = datetime.utcnow()

    def add_weakness(self, description: str, metadata: Dict[str, Any] | None = None) -> None:
        item = {"description": description, "metadata": metadata or {}, "created_at": datetime.utcnow().isoformat()}
        self.weaknesses = (self.weaknesses or []) + [item]
        self.last_reviewed_at = datetime.utcnow()

    def to_summary(self) -> Dict[str, Any]:
        return {
            "strengths": len(self.strengths or []),
            "weaknesses": len(self.weaknesses or []),
            "opportunities": len(self.opportunities or []),
            "threats": len(self.threats or []),
            "last_reviewed_at": self.last_reviewed_at,
        }

    def __repr__(self) -> str:
        return f"<SWOTAnalysis(plan_id={self.strategic_plan_id})>"

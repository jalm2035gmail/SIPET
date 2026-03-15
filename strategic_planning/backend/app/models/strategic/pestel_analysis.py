from typing import List, Dict
from datetime import datetime
from sqlalchemy import Column, Integer, JSON, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.MAIN import MAINModel

class PESTELAnalysis(MAINModel):
    __tablename__ = "pestel_analysis"

    strategic_plan_id = Column(Integer, ForeignKey("strategic_plans.id"), nullable=False, unique=True)
    political = Column(JSON, default=list)
    economic = Column(JSON, default=list)
    social = Column(JSON, default=list)
    technological = Column(JSON, default=list)
    environmental = Column(JSON, default=list)
    legal = Column(JSON, default=list)
    insights = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    last_reviewed_at = Column(DateTime(timezone=True), nullable=True)

    strategic_plan = relationship("StrategicPlan", back_populates="pestel_analysis")

    def add_factor(self, category: str, item: Dict) -> None:
        category_data = getattr(self, category, None)
        if category_data is None:
            raise ValueError(f"Categoría inválida: {category}")
        self.__setattr__(category, (category_data or []) + [item])
        self.last_reviewed_at = datetime.utcnow()

    def get_categories(self) -> Dict[str, List[Dict]]:
        return {
            "political": self.political or [],
            "economic": self.economic or [],
            "social": self.social or [],
            "technological": self.technological or [],
            "environmental": self.environmental or [],
            "legal": self.legal or [],
        }

    def summarize(self) -> Dict[str, int]:
        return {key: len(items or []) for key, items in self.get_categories().items()}

    def __repr__(self) -> str:
        return f"<PESTELAnalysis(plan_id={self.strategic_plan_id})>"

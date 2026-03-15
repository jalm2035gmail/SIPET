from sqlalchemy import Column, ForeignKey, Integer, JSON, Text
from sqlalchemy.orm import relationship

from app.models.MAIN import MAINModel


class DiagnosticAnalysis(MAINModel):
    """Modelo para Análisis de Diagnóstico (FODA, PESTEL, Porter)"""
    __tablename__ = "diagnostic_analysis"

    # Relación con plan
    strategic_plan_id = Column(Integer, ForeignKey("strategic_plans.id"), unique=True, nullable=False)

    # Análisis FODA
    swot_strengths = Column(JSON, default=list)      # Fortalezas
    swot_weaknesses = Column(JSON, default=list)     # Debilidades
    swot_opportunities = Column(JSON, default=list)  # Oportunidades
    swot_threats = Column(JSON, default=list)        # Amenazas

    # Análisis PESTEL
    pestel_political = Column(JSON, default=list)     # Factores políticos
    pestel_economic = Column(JSON, default=list)      # Factores económicos
    pestel_social = Column(JSON, default=list)        # Factores sociales
    pestel_technological = Column(JSON, default=list) # Factores tecnológicos
    pestel_environmental = Column(JSON, default=list) # Factores ambientales
    pestel_legal = Column(JSON, default=list)         # Factores legales

    # Análisis de Porter
    porter_supplier_power = Column(Text)              # Poder de proveedores
    porter_buyer_power = Column(Text)                 # Poder de compradores
    porter_competitive_rivalry = Column(Text)         # Rivalidad competitiva
    porter_threat_of_substitutes = Column(Text)       # Amenaza de sustitutos
    porter_threat_of_new_entrants = Column(Text)      # Amenaza de nuevos entrantes

    # Percepción del cliente
    customer_perception = Column(JSON)                # Encuestas, NPS, feedback
    market_research = Column(JSON)                    # Investigación de mercado
    competitor_analysis = Column(JSON)                # Análisis de competencia

    # Conclusiones
    key_findings = Column(Text)                       # Hallazgos clave
    strategic_implications = Column(Text)             # Implicaciones estratégicas
    recommendations = Column(Text)                    # Recomendaciones

    # Relación
    strategic_plan = relationship("StrategicPlan", back_populates="diagnostic_analysis")

    # Métodos de ayuda
    def get_swot_matrix(self) -> dict:
        """Retorna matriz FODA estructurada"""
        return {
            "strengths": self.swot_strengths or [],
            "weaknesses": self.swot_weaknesses or [],
            "opportunities": self.swot_opportunities or [],
            "threats": self.swot_threats or [],
        }

    def get_pestel_categories(self) -> dict:
        """Retorna categorías PESTEL"""
        return {
            "political": self.pestel_political or [],
            "economic": self.pestel_economic or [],
            "social": self.pestel_social or [],
            "technological": self.pestel_technological or [],
            "environmental": self.pestel_environmental or [],
            "legal": self.pestel_legal or [],
        }

    def get_porter_forces(self) -> dict:
        """Retorna las 5 fuerzas de Porter"""
        return {
            "supplier_power": self.porter_supplier_power,
            "buyer_power": self.porter_buyer_power,
            "competitive_rivalry": self.porter_competitive_rivalry,
            "threat_of_substitutes": self.porter_threat_of_substitutes,
            "threat_of_new_entrants": self.porter_threat_of_new_entrants,
        }

    def __repr__(self) -> str:
        return f"<DiagnosticAnalysis(id={self.id}, plan_id={self.strategic_plan_id})>"

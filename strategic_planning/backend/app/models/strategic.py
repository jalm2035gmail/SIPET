from sqlalchemy import Column, Integer, String, Text, Date, Float, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class StrategicPlan(Base):
    __tablename__ = "strategic_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    code = Column(String(50), unique=True, index=True)
    description = Column(Text)
    vision = Column(Text)
    mission = Column(Text)
    values = Column(JSON)  # Lista de valores como JSON
    start_date = Column(Date)
    end_date = Column(Date)
    status = Column(String(20), default="draft")  # draft, active, completed, archived
    version = Column(String(20), default="1.0")
    
    # Relaciones
    diagnostic_analysis = relationship("DiagnosticAnalysis", back_populates="strategic_plan", uselist=False)
    strategic_axes = relationship("StrategicAxis", back_populates="strategic_plan", cascade="all, delete-orphan")
    poas = relationship("POA", back_populates="strategic_plan", cascade="all, delete-orphan")

class DiagnosticAnalysis(Base):
    __tablename__ = "diagnostic_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    strategic_plan_id = Column(Integer, ForeignKey("strategic_plans.id"), unique=True)
    
    # Componentes del diagnóstico
    swot_analysis = Column(JSON)  # {strengths: [], weaknesses: [], ...}
    pestel_analysis = Column(JSON)  # {political: [], economic: [], ...}
    porter_analysis = Column(JSON)  # {five_forces: {...}}
    customer_perception = Column(JSON)  # {surveys: [], satisfaction_scores: {...}}
    
    # Relaciones
    strategic_plan = relationship("StrategicPlan", back_populates="diagnostic_analysis")

class StrategicAxis(Base):
    __tablename__ = "strategic_axes"
    
    id = Column(Integer, primary_key=True, index=True)
    strategic_plan_id = Column(Integer, ForeignKey("strategic_plans.id"))
    name = Column(String(200), nullable=False)
    code = Column(String(50))
    description = Column(Text)
    priority = Column(String(20))  # high, medium, low
    weight = Column(Float, default=0.0)  # Porcentaje de peso
    color = Column(String(10))  # Color para visualización
    
    # Relaciones
    strategic_plan = relationship("StrategicPlan", back_populates="strategic_axes")
    objectives = relationship("StrategicObjective", back_populates="strategic_axis", cascade="all, delete-orphan")

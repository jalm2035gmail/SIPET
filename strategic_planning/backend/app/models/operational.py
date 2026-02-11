from sqlalchemy import Column, Integer, String, Text, Date, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class POA(Base):
    __tablename__ = "poas"
    
    id = Column(Integer, primary_key=True, index=True)
    strategic_plan_id = Column(Integer, ForeignKey("strategic_plans.id"))
    year = Column(Integer, nullable=False)
    name = Column(String(200))
    status = Column(String(20), default="draft")  # draft, approved, in_progress, completed
    total_budget = Column(Float, default=0.0)
    start_date = Column(Date)
    end_date = Column(Date)
    
    # Relaciones
    strategic_plan = relationship("StrategicPlan", back_populates="poas")
    department_objectives = relationship("DepartmentObjective", back_populates="poa", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="poa", cascade="all, delete-orphan")

class Activity(Base):
    __tablename__ = "activities"
    
    id = Column(Integer, primary_key=True, index=True)
    poa_id = Column(Integer, ForeignKey("poas.id"))
    department_id = Column(Integer, ForeignKey("departments.id"))
    strategic_objective_id = Column(Integer, ForeignKey("strategic_objectives.id"))
    
    code = Column(String(50))
    name = Column(String(200), nullable=False)
    description = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)
    status = Column(String(20), default="planned")  # planned, in_progress, completed, delayed
    budget = Column(Float, default=0.0)
    progress = Column(Float, default=0.0)  # 0-100%
    
    # Relaciones
    poa = relationship("POA", back_populates="activities")
    department = relationship("Department", back_populates="activities")
    strategic_objective = relationship("StrategicObjective", back_populates="activities")
    tasks = relationship("Task", back_populates="activity", cascade="all, delete-orphan")

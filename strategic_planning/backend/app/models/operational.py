from sqlalchemy import Column, Integer, String, Text, Date, Float, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from app.models.MAIN import MAIN

class POA(MAIN):
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

class Activity(MAIN):
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


class DepartmentObjective(MAIN):
    __tablename__ = "department_objectives"

    id = Column(Integer, primary_key=True, index=True)
    poa_id = Column(Integer, ForeignKey("poas.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    strategic_objective_id = Column(Integer, ForeignKey("strategic_objectives.id"), nullable=True)

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    budget = Column(Float, default=0.0, nullable=False)
    allocated_amount = Column(Float, default=0.0, nullable=False)
    status = Column(String(20), default="planned", nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    __table_args__ = (
        CheckConstraint("allocated_amount <= budget", name="ck_department_objective_budget"),
    )

    poa = relationship("POA", back_populates="department_objectives")
    department = relationship("Department", back_populates="objectives")
    strategic_objective = relationship("StrategicObjective", back_populates="department_objectives")

    def register_allocation(self, amount: float):
        if self.allocated_amount + amount > self.budget:
            raise ValueError("El monto supera el presupuesto asignado.")
        self.allocated_amount += amount

    @property
    def remaining_budget(self) -> float:
        return max(0.0, self.budget - self.allocated_amount)

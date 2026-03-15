from datetime import date
import enum

from sqlalchemy import Column, Date, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.models.MAIN import MAINModel


class PlanStatus(str, enum.Enum):
    """Estados del plan estratégico"""
    DRAFT = "draft"           # Borrador
    IN_REVIEW = "in_review"   # En revisión
    APPROVED = "approved"     # Aprobado
    ACTIVE = "active"         # Activo (en ejecución)
    COMPLETED = "completed"   # Completado
    ARCHIVED = "archived"     # Archivado
    CANCELLED = "cancelled"   # Cancelado


class StrategicPlan(MAINModel):
    """Modelo para Plan Estratégico"""
    __tablename__ = "strategic_plans"

    # Información básica
    name = Column(String(200), nullable=False, index=True)
    code = Column(String(50), unique=True, index=True)
    description = Column(Text)
    version = Column(String(20), default="1.0")

    # Período
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # Declaraciones estratégicas
    vision = Column(Text, nullable=False)
    mission = Column(Text, nullable=False)
    values = Column(JSON)  # Lista de valores como JSON

    # Estado y control
    status = Column(Enum(PlanStatus), default=PlanStatus.DRAFT)
    approval_date = Column(Date, nullable=True)
    approval_by = Column(Integer, nullable=True)  # ID del aprobador

    # Metadatos
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    parent_plan_id = Column(Integer, ForeignKey("strategic_plans.id"), nullable=True)

    # Relaciones
    department = relationship("Department", back_populates="strategic_plans")
    parent_plan = relationship("StrategicPlan", remote_side=[id], backref="child_plans")
    diagnostic_analysis = relationship(
        "DiagnosticAnalysis",
        back_populates="strategic_plan",
        uselist=False,
        cascade="all, delete-orphan",
    )
    strategic_axes = relationship(
        "StrategicAxis",
        back_populates="strategic_plan",
        cascade="all, delete-orphan",
    )
    poas = relationship("POA", back_populates="strategic_plan", cascade="all, delete-orphan")
    swot_analysis = relationship(
        "SWOTAnalysis",
        back_populates="strategic_plan",
        uselist=False,
        cascade="all, delete-orphan",
    )
    pestel_analysis = relationship(
        "PESTELAnalysis",
        back_populates="strategic_plan",
        uselist=False,
        cascade="all, delete-orphan",
    )
    porter_analysis = relationship(
        "PorterAnalysis",
        back_populates="strategic_plan",
        uselist=False,
        cascade="all, delete-orphan",
    )
    customer_perception = relationship(
        "CustomerPerception",
        back_populates="strategic_plan",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Métodos específicos
    def is_active_period(self) -> bool:
        """Verifica si el plan está en período activo"""
        today = date.today()
        return self.start_date <= today <= self.end_date

    def get_progress(self) -> float:
        """Calcula progreso general del plan"""
        if not self.strategic_axes:
            return 0.0

        total_weight = sum(axis.weight for axis in self.strategic_axes if axis.weight)
        if total_weight == 0:
            return 0.0

        weighted_progress = sum(
            axis.get_progress() * (axis.weight or 0)
            for axis in self.strategic_axes
        )

        return round(weighted_progress / total_weight, 2)

    def get_days_remaining(self) -> int:
        """Días restantes para finalizar el plan"""
        today = date.today()
        if today > self.end_date:
            return 0
        return (self.end_date - today).days

    def __repr__(self) -> str:
        return f"<StrategicPlan(id={self.id}, name='{self.name}', status='{self.status}')>"

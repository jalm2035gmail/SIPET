from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, JSON, Date, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base

class KPI(Base):
    __tablename__ = "kpis"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    code = Column(String(50), unique=True)
    description = Column(Text)
    strategic_objective_id = Column(Integer, ForeignKey("strategic_objectives.id"))
    department_id = Column(Integer, ForeignKey("departments.id"))
    responsible_id = Column(Integer, ForeignKey("users.id"))
    
    # Configuración del KPI
    type = Column(String(20))  # quantitative, qualitative, boolean
    unit = Column(String(50))
    target_value = Column(Float)
    min_value = Column(Float)
    max_value = Column(Float)
    formula = Column(Text)  # Fórmula de cálculo (opcional)
    data_source = Column(String(200))
    frequency = Column(String(20))  # daily, weekly, monthly, quarterly
    
    # Relaciones
    strategic_objective = relationship("StrategicObjective", back_populates="kpis")
    department = relationship("Department", back_populates="kpis")
    responsible = relationship("User", back_populates="responsible_kpis")
    measurements = relationship("KPIMeasurement", back_populates="kpi", cascade="all, delete-orphan")

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    type = Column(String(50))  # strategic, operational, kpi, financial
    template = Column(JSON)  # Configuración de la plantilla
    schedule = Column(JSON)  # Programación automática
    recipients = Column(JSON)  # Lista de usuarios/departamentos
    generated_reports = relationship("GeneratedReport", back_populates="report")

class GeneratedReport(Base):
    __tablename__ = "generated_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"))
    generated_at = Column(DateTime, default=datetime.utcnow)
    period_start = Column(Date)
    period_end = Column(Date)
    data = Column(JSON)  # Datos serializados
    file_path = Column(String(500))  # Ruta al archivo generado
    status = Column(String(20))  # generated, sent, viewed
    
    report = relationship("Report", back_populates="generated_reports")

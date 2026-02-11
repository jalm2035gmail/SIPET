from sqlalchemy import Column, Integer, String, Text, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class Department(Base):
    __tablename__ = "departments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    code = Column(String(50), unique=True)
    description = Column(Text)
    parent_id = Column(Integer, ForeignKey("departments.id"))
    manager_id = Column(Integer, ForeignKey("users.id"))
    budget = Column(Float, default=0.0)
    
    # Relaciones
    parent = relationship("Department", remote_side=[id], backref="children")
    manager = relationship("User", foreign_keys=[manager_id])
    users = relationship("User", back_populates="department")
    activities = relationship("Activity", back_populates="department")
    kpis = relationship("KPI", back_populates="department")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True)
    full_name = Column(String(150))
    department_id = Column(Integer, ForeignKey("departments.id"))
    role = Column(String(50))  # admin, strategic_manager, department_manager, employee
    is_active = Column(Boolean, default=True)
    
    # Relaciones
    department = relationship("Department", back_populates="users")
    assigned_tasks = relationship("Task", back_populates="assigned_to")
    responsible_kpis = relationship("KPI", back_populates="responsible")

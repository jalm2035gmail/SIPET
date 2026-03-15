from sqlalchemy import Column, Integer, String, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from core.db import Base
import enum

class UserType(str, enum.Enum):
    superadmin = "superadmin"
    vendor = "vendor"
    customer = "customer"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    user_type = Column(Enum(UserType), nullable=False)
    two_factor_enabled = Column(Boolean, nullable=False, default=False)
    vendor_profile = relationship("VendorStore", back_populates="vendor", uselist=False)

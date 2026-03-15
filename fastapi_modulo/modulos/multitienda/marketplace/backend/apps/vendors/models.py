

from sqlalchemy import Column, Integer, String, Numeric, Boolean, ForeignKey, JSON, DateTime, Enum
from sqlalchemy.orm import relationship
from core.db import Base
import enum
from datetime import datetime

class VendorStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    suspended = "suspended"

class VendorStore(Base):
    __tablename__ = "vendors"
    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("users.id"), unique=True)
    store_name = Column(String(100), nullable=False)
    store_slug = Column(String, unique=True, nullable=False)
    description = Column(String, default="")
    logo = Column(String, nullable=True)      # URL o ruta S3/MinIO
    banner = Column(String, nullable=True)    # URL o ruta S3/MinIO
    phone = Column(String(20))
    address = Column(String)
    country = Column(String(100))
    store_theme = Column(JSON, default={})
    commission_rate = Column(Numeric(5, 2), default=10.00)
    is_featured = Column(Boolean, default=False)
    status = Column(Enum(VendorStatus), default=VendorStatus.pending)
    rating = Column(Numeric(3, 2), default=0.00)
    total_sales = Column(Numeric(12, 2), default=0.00)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    vendor = relationship("User", back_populates="vendor_profile", uselist=False)
    documents = relationship("VendorDocument", back_populates="vendor", cascade="all, delete-orphan")
    commission_settings = relationship("VendorCommission", back_populates="vendor", uselist=False)
    payouts = relationship("Payout", back_populates="vendor", cascade="all, delete-orphan")
    analytics = relationship("VendorAnalytics", back_populates="vendor", cascade="all, delete-orphan")

class VendorDocument(Base):
    __tablename__ = "vendor_documents"
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    document_type = Column(String(50))
    file = Column(String)  # URL o ruta S3/MinIO
    verified = Column(Boolean, default=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    vendor = relationship("VendorStore", back_populates="documents")

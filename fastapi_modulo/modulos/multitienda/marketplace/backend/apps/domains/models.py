from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid
from backend.core.db import Base

class VendorDomain(Base):
    __tablename__ = 'vendor_domains'

    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendors.id'), unique=True, nullable=False)
    subdomain = Column(String(100), unique=True, nullable=False)
    custom_domain = Column(String(255), unique=True, nullable=True)
    ssl_certificate = Column(Text, default='')
    ssl_private_key = Column(Text, default='')
    ssl_expires_at = Column(DateTime, nullable=True)
    dns_records = Column(JSON, default=list)
    last_dns_check = Column(DateTime, nullable=True)
    status = Column(String(20), default='pending')
    verification_token = Column(String(100), default='')
    hits = Column(Integer, default=0)
    last_hit = Column(DateTime, nullable=True)
    redirect_to_subdomain = Column(Boolean, default=False)
    force_ssl = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)

    vendor = relationship('Vendor', back_populates='domain_settings')

    def get_store_url(self):
        if self.custom_domain and self.status == 'active':
            protocol = 'https' if self.force_ssl else 'http'
            return f"{protocol}://{self.custom_domain}"
        return f"https://{self.subdomain}"

class DomainRequest(Base):
    __tablename__ = 'domain_requests'

    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendors.id'), nullable=False)
    requested_domain = Column(String(255), nullable=False)
    purpose = Column(Text, default='')
    contact_name = Column(String(100), nullable=False)
    contact_email = Column(String(255), nullable=False)
    contact_phone = Column(String(20), default='')
    business_license = Column(String(255), nullable=True)
    identity_document = Column(String(255), nullable=True)
    status = Column(String(20), default='pending')
    reviewed_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    review_notes = Column(Text, default='')
    rejection_reason = Column(Text, default='')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)

    vendor = relationship('Vendor', back_populates='domain_requests')
    reviewed_by = relationship('User', back_populates='reviewed_domains', foreign_keys=[reviewed_by_id])

    __mapper_args__ = {"order_by": created_at.desc()}

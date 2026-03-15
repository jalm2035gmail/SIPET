from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.core.db import Base

class VendorAPIKey(Base):
    __tablename__ = 'vendor_api_keys'

    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendors.id'), nullable=False)
    name = Column(String(100), nullable=False)
    key = Column(String(64), unique=True, nullable=False)
    secret = Column(String(64), nullable=False)
    permissions = Column(JSON, default=list)
    allowed_ips = Column(JSON, default=list)
    rate_limit_per_hour = Column(Integer, default=1000)
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)
    webhook_url = Column(String(255), default='')
    webhook_secret = Column(String(64), default='')
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    vendor = relationship('Vendor', back_populates='api_keys')
    webhook_deliveries = relationship('WebhookDelivery', back_populates='api_key')

class WebhookDelivery(Base):
    __tablename__ = 'webhook_deliveries'

    id = Column(Integer, primary_key=True)
    api_key_id = Column(Integer, ForeignKey('vendor_api_keys.id'), nullable=False)
    event = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, default='')
    response_headers = Column(JSON, default=dict)
    success = Column(Boolean, default=False)
    error_message = Column(Text, default='')
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    delivered_at = Column(DateTime, nullable=True)

    api_key = relationship('VendorAPIKey', back_populates='webhook_deliveries')

    __mapper_args__ = {"order_by": created_at.desc()}

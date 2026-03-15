from sqlalchemy import Column, Integer, Numeric, String, ForeignKey
from sqlalchemy.orm import relationship
from core.db import Base

class VendorPayout(Base):
    __tablename__ = "vendor_payouts"
    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    order_id = Column(Integer, ForeignKey("orders.id"))
    vendor_amount = Column(Numeric(10, 2), nullable=False)
    platform_commission = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False)

    vendor = relationship("VendorStore")
    order = relationship("Order")

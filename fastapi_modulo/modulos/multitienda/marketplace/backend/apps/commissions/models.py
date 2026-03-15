from sqlalchemy import Column, Integer, String, Numeric, Boolean, ForeignKey, DateTime, Enum, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal, ROUND_HALF_UP
import enum
import uuid

from core.db import Base

class PlanType(str, enum.Enum):
    percentage = "percentage"
    fixed = "fixed"
    tiered = "tiered"

class CommissionPlan(Base):
    __tablename__ = "commission_plan"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    plan_type = Column(Enum(PlanType), nullable=False)
    default_rate = Column(Numeric(5,2), default=10.00)
    min_commission = Column(Numeric(10,2), nullable=True)
    max_commission = Column(Numeric(10,2), nullable=True)
    tier_config = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def calculate_commission(self, amount: Decimal) -> Decimal:
        if self.plan_type == PlanType.percentage:
            commission = (amount * self.default_rate) / 100
        elif self.plan_type == PlanType.fixed:
            commission = self.default_rate
        elif self.plan_type == PlanType.tiered:
            commission = self.calculate_tiered_commission(amount)
        else:
            commission = Decimal('0.00')
        if self.min_commission:
            commission = max(commission, self.min_commission)
        if self.max_commission:
            commission = min(commission, self.max_commission)
        return commission.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def calculate_tiered_commission(self, amount: Decimal) -> Decimal:
        commission = Decimal('0.00')
        remaining = amount
        tiers = self.tier_config.get('tiers', []) if self.tier_config else []
        tiers = sorted(tiers, key=lambda x: x['min'])
        for tier in tiers:
            tier_min = Decimal(str(tier['min']))
            tier_max = Decimal(str(tier.get('max', float('inf'))))
            tier_rate = Decimal(str(tier['rate']))
            if remaining <= 0:
                break
            tier_range = tier_max - tier_min if tier_max != float('inf') else remaining
            amount_in_tier = min(remaining, tier_range)
            if amount_in_tier > 0:
                commission += (amount_in_tier * tier_rate) / 100
                remaining -= amount_in_tier
        return commission

class VendorCommission(Base):
    __tablename__ = "vendor_commission"
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), unique=True)
    commission_plan_id = Column(Integer, ForeignKey("commission_plan.id"), nullable=True)
    custom_rate = Column(Numeric(5,2), nullable=True)
    category_rates = Column(JSON, default={})

    vendor = relationship("VendorStore", back_populates="commission_settings")
    commission_plan = relationship("CommissionPlan")

    def calculate_commission_for_order(self, order_item):
        base_amount = order_item.total
        # Por categoría
        if hasattr(order_item, 'product') and getattr(order_item.product, 'category_id', None):
            category_id = str(order_item.product.category_id)
            if self.category_rates and category_id in self.category_rates:
                custom_rate = Decimal(str(self.category_rates[category_id]))
                commission = (base_amount * custom_rate) / 100
                return commission
        if self.custom_rate is not None:
            commission = (base_amount * self.custom_rate) / 100
            return commission
        if self.commission_plan:
            return self.commission_plan.calculate_commission(base_amount)
        default_rate = Decimal('10.00')
        return (base_amount * default_rate) / 100

class PayoutStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    paid = "paid"
    failed = "failed"
    cancelled = "cancelled"

class PaymentMethod(str, enum.Enum):
    bank_transfer = "bank_transfer"
    paypal = "paypal"
    stripe_connect = "stripe_connect"
    cash = "cash"

class Payout(Base):
    __tablename__ = "payout"
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    payout_period_start = Column(DateTime)
    payout_period_end = Column(DateTime)
    payout_date = Column(DateTime, nullable=True)
    reference_number = Column(String(50), unique=True)
    total_sales = Column(Numeric(12,2), default=0)
    total_commission = Column(Numeric(12,2), default=0)
    total_fees = Column(Numeric(12,2), default=0)
    net_amount = Column(Numeric(12,2), default=0)
    status = Column(Enum(PayoutStatus), default=PayoutStatus.pending)
    payment_method = Column(Enum(PaymentMethod))
    transaction_id = Column(String(100), default='')
    payment_details = Column(JSON, default={})
    invoice_url = Column(String, default='')
    receipt_url = Column(String, default='')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)

    vendor = relationship("VendorStore", back_populates="payouts")
    items = relationship("PayoutItem", back_populates="payout", cascade="all, delete-orphan")

class PayoutItem(Base):
    __tablename__ = "payout_item"
    id = Column(Integer, primary_key=True)
    payout_id = Column(Integer, ForeignKey("payout.id"))
    order_id = Column(Integer, ForeignKey("order.id"))
    order_item_id = Column(Integer, ForeignKey("order_item.id"))
    item_amount = Column(Numeric(10,2))
    commission_amount = Column(Numeric(10,2))
    net_amount = Column(Numeric(10,2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    payout = relationship("Payout", back_populates="items")
    order = relationship("Order")
    order_item = relationship("OrderItem")

class WithdrawalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    processing = "processing"
    completed = "completed"
    rejected = "rejected"

class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_request"
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    amount = Column(Numeric(10,2))
    payment_method = Column(Enum(PaymentMethod))
    payment_details = Column(JSON, default={})
    status = Column(Enum(WithdrawalStatus), default=WithdrawalStatus.pending)
    notes = Column(String, default='')
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    processed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

class VendorBalanceTransactionType(str, enum.Enum):
    sale = "sale"
    commission = "commission"
    refund = "refund"
    payout = "payout"
    withdrawal = "withdrawal"
    adjustment = "adjustment"
    fee = "fee"

class VendorBalance(Base):
    __tablename__ = "vendor_balance"
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    order_id = Column(Integer, ForeignKey("order.id"), nullable=True)
    payout_id = Column(Integer, ForeignKey("payout.id"), nullable=True)
    transaction_type = Column(Enum(VendorBalanceTransactionType))
    amount = Column(Numeric(10,2))
    description = Column(String, default='')
    balance_before = Column(Numeric(10,2))
    balance_after = Column(Numeric(10,2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    vendor = relationship("VendorStore")
    order = relationship("Order")
    payout = relationship("Payout")

    @classmethod
    def record_transaction(cls, db, vendor, transaction_type, amount, description='', order=None, payout=None):
        last = db.query(cls).filter(cls.vendor_id == vendor.id).order_by(cls.created_at.desc()).first()
        balance_before = last.balance_after if last else Decimal('0.00')
        balance_after = balance_before + amount
        tx = cls(
            vendor_id=vendor.id,
            order_id=order.id if order else None,
            payout_id=payout.id if payout else None,
            transaction_type=transaction_type,
            amount=amount,
            description=description,
            balance_before=balance_before,
            balance_after=balance_after
        )
        db.add(tx)
        db.commit()
        return tx


import enum
import uuid
from decimal import Decimal
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, Boolean, ForeignKey, DateTime, Date, Enum, Text, JSON, UniqueConstraint, Index, CheckConstraint
from sqlalchemy.orm import relationship
from core.db import Base

class ReviewStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    flagged = "flagged"

class ReviewType(str, enum.Enum):
    product = "product"
    vendor = "vendor"

class ProductReview(Base):
    __tablename__ = "product_reviews"
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    is_verified_purchase = Column(Boolean, default=False)
    purchase_date = Column(DateTime, nullable=True)
    status = Column(Enum(ReviewStatus), default=ReviewStatus.pending)
    is_featured = Column(Boolean, default=False)
    helpful_count = Column(Integer, default=0)
    not_helpful_count = Column(Integer, default=0)
    vendor_reply = Column(Text, default="")
    vendor_reply_date = Column(DateTime, nullable=True)
    sentiment_score = Column(Numeric(5, 4), nullable=True)
    sentiment_label = Column(String(20), default="")
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    # Relationships
    product = relationship("Product", back_populates="reviews")
    vendor = relationship("VendorStore")
    customer = relationship("User")
    order = relationship("Order")
    order_item = relationship("OrderItem")
    media = relationship("ReviewMedia", back_populates="review")
    votes = relationship("ReviewVote", back_populates="review")
    reports = relationship("ReviewReport", back_populates="review")
    __table_args__ = (
        Index("ix_product_status_rating", "product_id", "status", "rating"),
        Index("ix_vendor_status", "vendor_id", "status"),
        Index("ix_customer_created_at", "customer_id", "created_at"),
        Index("ix_verified_rating", "is_verified_purchase", "rating"),
        Index("ix_helpful_created_at", "helpful_count", "created_at"),
        CheckConstraint('rating >= 1 AND rating <= 5', name='rating_range'),
        CheckConstraint('(product_id IS NOT NULL OR vendor_id IS NOT NULL)', name='review_target'),
        {'sqlite_autoincrement': True},
    )

class ReviewVote(Base):
    __tablename__ = "review_votes"
    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("product_reviews.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    is_helpful = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    review = relationship("ProductReview", back_populates="votes")
    user = relationship("User")
    __table_args__ = (
        UniqueConstraint('review_id', 'user_id', name='uq_review_user'),
        Index("ix_review_is_helpful", "review_id", "is_helpful"),
    )

class ReviewMedia(Base):
    __tablename__ = "review_media"
    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("product_reviews.id"))
    media_type = Column(String(10))
    file = Column(String, nullable=False)
    thumbnail = Column(String, nullable=True)
    caption = Column(String(200), default="")
    order = Column(Integer, default=0)
    is_approved = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    review = relationship("ProductReview", back_populates="media")
    __table_args__ = (
        Index("ix_review_media_order_created", "order", "created_at"),
    )

class ReviewReport(Base):
    __tablename__ = "review_reports"
    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("product_reviews.id"))
    reporter_id = Column(Integer, ForeignKey("users.id"))
    reason = Column(String(20))
    description = Column(Text, default="")
    status = Column(String(20), default="pending")
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolution_notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    review = relationship("ProductReview", back_populates="reports")
    reporter = relationship("User", foreign_keys=[reporter_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    __table_args__ = (
        Index("ix_review_status", "review_id", "status"),
        Index("ix_status_created_at", "status", "created_at"),
    )

class ReviewAnalytics(Base):
    __tablename__ = "review_analytics"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    date = Column(Date, nullable=False)
    rating_1 = Column(Integer, default=0)
    rating_2 = Column(Integer, default=0)
    rating_3 = Column(Integer, default=0)
    rating_4 = Column(Integer, default=0)
    rating_5 = Column(Integer, default=0)
    total_reviews = Column(Integer, default=0)
    average_rating = Column(Numeric(3, 2), default=0)
    verified_reviews = Column(Integer, default=0)
    reviews_with_media = Column(Integer, default=0)
    reviews_with_reply = Column(Integer, default=0)
    positive_reviews = Column(Integer, default=0)
    neutral_reviews = Column(Integer, default=0)
    negative_reviews = Column(Integer, default=0)
    total_helpful_votes = Column(Integer, default=0)
    total_reports = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (
        UniqueConstraint('product_id', 'date', name='uq_product_date'),
        UniqueConstraint('vendor_id', 'date', name='uq_vendor_date'),
        Index("ix_product_date", "product_id", "date"),
        Index("ix_vendor_date", "vendor_id", "date"),
    )

class ReviewSettings(Base):
    __tablename__ = "review_settings"
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    auto_approve_verified = Column(Boolean, default=True)
    require_verification = Column(Boolean, default=False)
    allow_anonymous = Column(Boolean, default=False)
    min_review_length = Column(Integer, default=20)
    max_review_length = Column(Integer, default=2000)
    notify_new_reviews = Column(Boolean, default=True)
    notify_negative_reviews = Column(Boolean, default=True)
    notify_review_reports = Column(Boolean, default=True)
    auto_reply_enabled = Column(Boolean, default=False)
    auto_reply_delay_hours = Column(Integer, default=24)
    auto_reply_template = Column(Text, default="")
    auto_flag_keywords = Column(JSON, default=list)
    auto_flag_low_rating = Column(Integer, default=2)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    vendor = relationship("VendorStore")

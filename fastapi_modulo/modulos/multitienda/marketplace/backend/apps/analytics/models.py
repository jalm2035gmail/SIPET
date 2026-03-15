from sqlalchemy import Column, Integer, String, Numeric, Boolean, ForeignKey, DateTime, Date, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal
from core.db import Base

class VendorAnalytics(Base):
    __tablename__ = 'vendor_analytics'
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendors.id'))
    date = Column(Date, index=True)
    # Métricas de ventas
    total_orders = Column(Integer, default=0)
    total_revenue = Column(Numeric(12,2), default=0)
    total_commission = Column(Numeric(12,2), default=0)
    net_earnings = Column(Numeric(12,2), default=0)
    # Métricas de productos
    products_sold = Column(Integer, default=0)
    unique_customers = Column(Integer, default=0)
    average_order_value = Column(Numeric(10,2), default=0)
    # Métricas de tráfico
    store_views = Column(Integer, default=0)
    product_views = Column(Integer, default=0)
    conversion_rate = Column(Numeric(5,2), default=0)
    # Métricas de inventario
    low_stock_alerts = Column(Integer, default=0)
    out_of_stock_products = Column(Integer, default=0)
    # Métricas de satisfacción
    average_rating = Column(Numeric(3,2), default=0)
    total_reviews = Column(Integer, default=0)
    # Detalles adicionales
    category_breakdown = Column(JSON, default={})
    top_products = Column(JSON, default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    vendor = relationship('VendorStore', back_populates='analytics')

class PageView(Base):
    __tablename__ = 'page_view'
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100))
    vendor_id = Column(Integer, ForeignKey('vendors.id'), nullable=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=True)
    page_type = Column(String(20))
    page_url = Column(String)
    referrer = Column(String, default='')
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String, default='')
    country = Column(String(100), default='')
    city = Column(String(100), default='')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    vendor = relationship('VendorStore')
    product = relationship('Product')

class CustomerBehavior(Base):
    __tablename__ = 'customer_behavior'
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendors.id'))
    customer_id = Column(Integer, ForeignKey('users.id'))
    total_orders = Column(Integer, default=0)
    total_spent = Column(Numeric(12,2), default=0)
    first_order_date = Column(DateTime, nullable=True)
    last_order_date = Column(DateTime, nullable=True)
    average_days_between_orders = Column(Numeric(5,2), default=0)
    favorite_categories = Column(JSON, default=[])
    purchased_products = Column(JSON, default=[])
    predicted_lifetime_value = Column(Numeric(12,2), default=0)
    churn_probability = Column(Numeric(5,2), default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    vendor = relationship('VendorStore')
    customer = relationship('User')

class PerformanceGoal(Base):
    __tablename__ = 'performance_goal'
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendors.id'))
    goal_type = Column(String(20))
    period_type = Column(String(20))
    target_value = Column(Numeric(12,2))
    current_value = Column(Numeric(12,2), default=0)
    start_date = Column(Date)
    end_date = Column(Date)
    is_completed = Column(Boolean, default=False)
    completion_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    vendor = relationship('VendorStore')

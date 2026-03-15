import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, Boolean, ForeignKey, DateTime, Enum, Text, JSON
from sqlalchemy.orm import relationship
from core.db import Base
from ..vendors.models import VendorStore

class ProductStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    out_of_stock = "out_of_stock"
    archived = "archived"

class ProductType(str, enum.Enum):
    simple = "simple"
    variable = "variable"

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    price = Column(Numeric(10, 2), nullable=False)
    stock_quantity = Column(Integer, default=0)
    slug = Column(String(200), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    status = Column(Enum(ProductStatus), default=ProductStatus.draft)
    type = Column(Enum(ProductType), default=ProductType.simple)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    images = relationship("ProductImage", back_populates="product")
    variants = relationship("ProductVariant", back_populates="product")
    reviews = relationship("ProductReview", back_populates="product")

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text, default="")
    image = Column(String, nullable=True)  # URL o ruta S3/MinIO
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    parent = relationship("Category", remote_side=[id], backref="children")

class ProductImage(Base):
    __tablename__ = "product_images"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    image = Column(String, nullable=False)  # URL o ruta S3/MinIO
    alt_text = Column(String(200), default="")
    is_primary = Column(Boolean, default=False)
    order = Column(Integer, default=0)
    product = relationship("Product", back_populates="images")

class ProductVariant(Base):
    __tablename__ = "product_variants"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    sku = Column(String(50), unique=True, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    compare_price = Column(Numeric(10, 2), nullable=True)
    stock_quantity = Column(Integer, default=0)
    attributes = Column(JSON, default={})
    product = relationship("Product", back_populates="variants")

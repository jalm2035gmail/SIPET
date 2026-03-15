from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class ProductAttributeRead(BaseModel):
    id: int
    name: str
    slug: str
    class Config:
        from_attributes = True

class ProductAttributeCreate(BaseModel):
    name: str
    slug: str

# Ya existe ProductVariantRead en este archivo

class ProductStatus(str, Enum):
    draft = "draft"
    published = "published"
    out_of_stock = "out_of_stock"
    archived = "archived"

class ProductType(str, Enum):
    simple = "simple"
    variable = "variable"

class ProductImageRead(BaseModel):
    id: int
    image: str
    alt_text: Optional[str]
    is_primary: bool
    order: int
    class Config:
        from_attributes = True

class ProductVariantRead(BaseModel):
    id: int
    sku: Optional[str]
    price: float
    compare_price: Optional[float]
    stock_quantity: int
    attributes: Dict
    class Config:
        from_attributes = True

class ProductCreate(BaseModel):
    name: str
    slug: Optional[str]
    sku: Optional[str]
    short_description: Optional[str] = ""
    description: Optional[str] = ""
    category_id: Optional[int]
    price: float
    compare_price: Optional[float]
    cost_price: Optional[float]
    stock_quantity: int = 0
    low_stock_threshold: int = 5
    manage_stock: bool = True
    allow_backorder: bool = False
    weight: Optional[float]
    dimensions: Optional[str] = ""
    status: ProductStatus = ProductStatus.draft
    product_type: ProductType = ProductType.simple
    is_featured: bool = False
    meta_title: Optional[str] = ""
    meta_description: Optional[str] = ""

class ProductUpdate(BaseModel):
    name: Optional[str]
    slug: Optional[str]
    sku: Optional[str]
    short_description: Optional[str]
    description: Optional[str]
    category_id: Optional[int]
    price: Optional[float]
    compare_price: Optional[float]
    cost_price: Optional[float]
    stock_quantity: Optional[int]
    low_stock_threshold: Optional[int]
    manage_stock: Optional[bool]
    allow_backorder: Optional[bool]
    weight: Optional[float]
    dimensions: Optional[str]
    status: Optional[ProductStatus]
    product_type: Optional[ProductType]
    is_featured: Optional[bool]
    meta_title: Optional[str]
    meta_description: Optional[str]

class ProductRead(BaseModel):
    id: int
    vendor_id: int
    name: str
    slug: str
    sku: Optional[str]
    short_description: Optional[str]
    description: Optional[str]
    category_id: Optional[int]
    price: float
    compare_price: Optional[float]
    cost_price: Optional[float]
    stock_quantity: int
    low_stock_threshold: int
    manage_stock: bool
    allow_backorder: bool
    weight: Optional[float]
    dimensions: Optional[str]
    status: ProductStatus
    product_type: ProductType
    is_featured: bool
    meta_title: Optional[str]
    meta_description: Optional[str]
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]
    images: List[ProductImageRead] = []
    variants: List[ProductVariantRead] = []
    class Config:
        from_attributes = True

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class ProductCreate(BaseModel):
    name: str
    sku: Optional[str]
    description: Optional[str]
    price: float
    stock_quantity: int
    category_id: Optional[int]
    status: Optional[str] = 'draft'
    # ...otros campos según modelo Product

class ProductUpdate(BaseModel):
    name: Optional[str]
    sku: Optional[str]
    description: Optional[str]
    price: Optional[float]
    stock_quantity: Optional[int]
    category_id: Optional[int]
    status: Optional[str]
    # ...otros campos

class OrderStatusUpdate(BaseModel):
    status: str
    tracking_number: Optional[str]

class VendorAPIKeyOut(BaseModel):
    id: int
    name: str
    permissions: List[str]
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True

class WebhookDeliveryOut(BaseModel):
    id: int
    event: str
    response_status: Optional[int]
    success: bool
    created_at: datetime
    delivered_at: Optional[datetime]
    error_message: Optional[str]

    class Config:
        from_attributes = True

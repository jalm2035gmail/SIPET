from pydantic import BaseModel
from typing import Literal

class VendorPayoutCreate(BaseModel):
    vendor_id: int
    order_id: int
    vendor_amount: float
    platform_commission: float
    status: Literal["pending", "paid", "cancelled"]

class VendorPayoutRead(BaseModel):
    id: int
    vendor_id: int
    order_id: int
    vendor_amount: float
    platform_commission: float
    status: str

    class Config:
        from_attributes = True

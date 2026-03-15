from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum

class VendorRegistrationRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    two_factor_enabled: bool = False
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    store_name: str
    phone: str
    address: str
    country: str

class VendorStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    suspended = "suspended"

class VendorDocumentRead(BaseModel):
    id: int
    document_type: str
    file: Optional[str]
    verified: bool
    uploaded_at: datetime

    class Config:
        from_attributes = True

class VendorStoreCreate(BaseModel):
    store_name: str
    store_slug: str
    description: Optional[str] = ""
    logo: Optional[str] = None
    banner: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    store_theme: Optional[Dict] = {}
    commission_rate: float = 10.0
    is_featured: bool = False
    status: VendorStatus = VendorStatus.pending
    is_active: bool = True

class VendorStoreRead(BaseModel):
    id: int
    vendor_id: int
    store_name: str
    store_slug: str
    description: Optional[str]
    logo: Optional[str]
    banner: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    country: Optional[str]
    store_theme: Optional[Dict]
    commission_rate: float
    is_featured: bool
    status: VendorStatus
    rating: float
    total_sales: float
    created_at: datetime
    updated_at: datetime
    is_active: bool
    documents: List[VendorDocumentRead] = []

    class Config:
        from_attributes = True

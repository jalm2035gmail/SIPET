from pydantic import BaseModel, EmailStr
from enum import Enum
from typing import Optional

class UserType(str, Enum):
    superadmin = "superadmin"
    vendor = "vendor"
    customer = "customer"

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    user_type: UserType
    vendor_profile_id: Optional[int] = None
    two_factor_enabled: bool = False

class UserRead(BaseModel):
    id: int
    username: str
    email: EmailStr
    user_type: UserType
    vendor_profile_id: Optional[int] = None
    two_factor_enabled: bool = False

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str

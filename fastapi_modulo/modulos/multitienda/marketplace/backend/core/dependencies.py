from fastapi import Depends
from backend.apps.users.models import User
from backend.apps.vendors.models import Vendor
from sqlalchemy.orm import Session
from backend.core.db import get_db_session

def get_current_user():
    # Dummy placeholder for dependency
    pass

def get_current_vendor():
    # Dummy placeholder for dependency
    pass

def get_support_user():
    # Dummy placeholder for dependency
    pass

def get_db():
    return Depends(get_db_session)

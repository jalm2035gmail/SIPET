from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from backend.core.dependencies import get_db, get_current_vendor, get_admin_user
from backend.apps.domains.models import VendorDomain, DomainRequest
from backend.apps.vendors.models import Vendor
from backend.apps.users.models import User
import re
import os

router = APIRouter(prefix="/api/domains", tags=["domains"])

# ...existing code from user prompt...

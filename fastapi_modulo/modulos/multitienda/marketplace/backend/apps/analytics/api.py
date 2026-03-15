from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, case, text
from datetime import datetime, timedelta, date
from typing import List, Optional
from fastapi.responses import StreamingResponse
import pandas as pd
from io import BytesIO

from core.db import get_db
from apps.analytics.models import VendorAnalytics, CustomerBehavior, PerformanceGoal, PageView
from apps.orders.models import OrderItem
from apps.products.routes_vendor import get_current_vendor
from apps.vendors.models import VendorStore

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# ...existing code from user request pasted here...

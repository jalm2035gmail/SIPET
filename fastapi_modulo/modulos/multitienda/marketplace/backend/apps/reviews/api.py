from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, and_, or_, desc, asc, case
from typing import List, Optional
from datetime import datetime, timedelta
from core.db import get_db
from apps.reviews.models import ProductReview, ReviewMedia, ReviewVote, ReviewReport, ReviewAnalytics
from apps.products.models import Product
from apps.vendors.models import VendorStore
from apps.orders.models import Order, OrderItem
from apps.users.models import User

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

# ...existing code from user request pasted here...

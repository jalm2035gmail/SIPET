from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from typing import List, Optional
from apps.products.models import Product, ProductVariant, Category
from apps.vendors.models import VendorStore
from apps.products.schemas import ProductRead
from core.db import get_db
import json

router = APIRouter(prefix="/api/catalog", tags=["catalog"])

@router.get("/products", response_model=List[ProductRead])
def public_products(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    store: Optional[str] = None,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    q: Optional[str] = None,
    attributes: Optional[str] = None,  # JSON string: {"color":"red"}
    db: Session = Depends(get_db)
):
    query = db.query(Product).filter(Product.status == 'published')
    if store:
        query = query.join(VendorStore).filter(VendorStore.store_slug == store)
    if category:
        query = query.join(Category).filter(Category.slug == category)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if q:
        like = f'%{q}%'
        query = query.filter(or_(
            Product.name.ilike(like),
            Product.short_description.ilike(like),
            Product.description.ilike(like),
            Product.sku.ilike(like)
        ))
    if attributes:
        attrs = json.loads(attributes)
        query = query.join(ProductVariant).filter(
            *[ProductVariant.attributes.contains({k: v}) for k, v in attrs.items()]
        )
    products = query.options(joinedload(Product.images)).order_by(Product.created_at.desc())\
        .offset((page-1)*limit).limit(limit).all()
    return products

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from typing import List, Optional
from math import ceil
from apps.vendors.models import VendorStore
from apps.products.models import Product, Category
from apps.products.schemas import ProductRead
from core.db import get_db

router = APIRouter(prefix="/api/catalog", tags=["catalog"])

# Helper: árbol de categorías

def get_category_tree(db: Session, parent_id=None):
    categories = db.query(Category).filter(Category.parent_id == parent_id).order_by(Category.name).all()
    result = []
    for cat in categories:
        result.append({
            "id": cat.id,
            "name": cat.name,
            "slug": cat.slug,
            "product_count": db.query(Product).filter(Product.category_id == cat.id, Product.status == 'published').count(),
            "children": get_category_tree(db, cat.id)
        })
    return result

# Helper: otros productos del vendedor

def get_vendor_other_products(db: Session, vendor_id: int, exclude_product_id: int):
    return db.query(Product).filter(
        Product.vendor_id == vendor_id,
        Product.id != exclude_product_id,
        Product.status == 'published'
    ).limit(8).all()

# Helper: lista de vendedores activos

def get_active_vendors_list(db: Session):
    return [
        {"id": v.id, "name": v.store_name, "slug": v.store_slug, "logo": v.logo}
        for v in db.query(VendorStore).filter(VendorStore.status == 'approved', VendorStore.is_active == True).all()
    ]

@router.get("/vendors")
def get_active_vendors(
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=50),
    featured: bool = Query(False),
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(VendorStore).filter(
        VendorStore.status == 'approved',
        VendorStore.is_active == True
    )
    if featured:
        query = query.filter(VendorStore.is_featured == True)
    if search:
        query = query.filter(
            or_(
                VendorStore.store_name.ilike(f'%{search}%'),
                VendorStore.description.ilike(f'%{search}%')
            )
        )
    query = query.order_by(
        VendorStore.is_featured.desc(),
        VendorStore.rating.desc(),
        VendorStore.total_sales.desc()
    )
    total = query.count()
    vendors = query.offset((page - 1) * limit).limit(limit).all()
    return {
        "vendors": vendors,
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": ceil(total / limit)
        }
    }

@router.get("/vendors/{vendor_slug}")
def get_vendor_store(
    vendor_slug: str,
    db: Session = Depends(get_db)
):
    vendor = db.query(VendorStore).filter(
        VendorStore.store_slug == vendor_slug,
        VendorStore.status == 'approved'
    ).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Store not found")
    product_count = db.query(Product).filter(
        Product.vendor_id == vendor.id,
        Product.status == 'published'
    ).count()
    featured_products = db.query(Product).filter(
        Product.vendor_id == vendor.id,
        Product.status == 'published',
        Product.is_featured == True
    ).limit(8).all()
    return {
        "vendor": vendor,
        "stats": {
            "product_count": product_count,
            "total_sales": float(getattr(vendor, "total_sales", 0.0)),
            "rating": float(getattr(vendor, "rating", 0.0)),
            "joined_date": vendor.created_at
        },
        "featured_products": featured_products
    }

@router.get("/products", response_model=List[ProductRead])
def get_products(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=100),
    vendor_slug: Optional[str] = None,
    category_slug: Optional[str] = None,
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    sort_by: str = Query("created_at", regex="^(created_at|price|name)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    search: Optional[str] = None,
    in_stock: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Product).filter(Product.status == 'published')
    query = query.options(
        joinedload(Product.vendor),
        joinedload(Product.category),
        joinedload(Product.images)
    )
    if vendor_slug:
        query = query.join(VendorStore).filter(VendorStore.store_slug == vendor_slug)
    if category_slug:
        query = query.join(Category).filter(Category.slug == category_slug)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if in_stock is not None:
        if in_stock:
            query = query.filter(
                or_(
                    Product.manage_stock == False,
                    and_(Product.manage_stock == True, Product.stock_quantity > 0)
                )
            )
    if search:
        query = query.filter(
            or_(
                Product.name.ilike(f'%{search}%'),
                Product.short_description.ilike(f'%{search}%'),
                Product.description.ilike(f'%{search}%'),
                VendorStore.store_name.ilike(f'%{search}%')
            )
        )
    sort_field = {
        "created_at": Product.created_at,
        "price": Product.price,
        "name": Product.name
    }.get(sort_by, Product.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_field.desc())
    else:
        query = query.order_by(sort_field.asc())
    total = query.count()
    products = query.offset((page - 1) * limit).limit(limit).all()
    base_url = str(request.url).split('?')[0]
    query_params = dict(request.query_params)
    def build_url(page_num):
        params = query_params.copy()
        params['page'] = page_num
        return f"{base_url}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
    return {
        "products": products,
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": ceil(total / limit),
            "next": build_url(page + 1) if page * limit < total else None,
            "prev": build_url(page - 1) if page > 1 else None
        },
        "filters": {
            "price_range": {
                "min": db.query(func.min(Product.price)).scalar() or 0,
                "max": db.query(func.max(Product.price)).scalar() or 1000
            },
            "categories": get_category_tree(db),
            "vendors": get_active_vendors_list(db)
        }
    }

@router.get("/products/{product_slug}")
def get_product_detail(
    product_slug: str,
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(
        Product.slug == product_slug,
        Product.status == 'published'
    ).options(
        joinedload(Product.vendor),
        joinedload(Product.category),
        joinedload(Product.images),
        joinedload(Product.variants),
        joinedload(Product.reviews)
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    # Incrementar contador de vistas (si existe el campo)
    if hasattr(product, 'view_count'):
        product.view_count = (product.view_count or 0) + 1
        db.commit()
    related_products = db.query(Product).filter(
        Product.id != product.id,
        Product.status == 'published',
        or_(
            Product.category_id == product.category_id,
            Product.vendor_id == product.vendor_id
        )
    ).limit(8).all()
    return {
        "product": product,
        "related_products": related_products,
        "vendor_other_products": get_vendor_other_products(db, product.vendor_id, product.id)
    }

@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    return get_category_tree(db)

@router.get("/search/suggestions")
def search_suggestions(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, le=20),
    db: Session = Depends(get_db)
):
    products = db.query(Product).filter(
        Product.status == 'published',
        Product.name.ilike(f'%{q}%')
    ).limit(limit // 2).all()
    vendors = db.query(VendorStore).filter(
        VendorStore.status == 'approved',
        VendorStore.store_name.ilike(f'%{q}%')
    ).limit(limit // 2).all()
    categories = db.query(Category).filter(
        Category.name.ilike(f'%{q}%')
    ).limit(5).all()
    return {
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "slug": p.slug,
                "price": p.price,
                "image": getattr(p, 'primary_image', None),
                "vendor": getattr(p.vendor, 'store_name', None)
            }
            for p in products
        ],
        "vendors": [
            {
                "id": v.id,
                "name": v.store_name,
                "slug": v.store_slug,
                "logo": v.logo
            }
            for v in vendors
        ],
        "categories": [
            {
                "id": c.id,
                "name": c.name,
                "slug": c.slug
            }
            for c in categories
        ]
    }

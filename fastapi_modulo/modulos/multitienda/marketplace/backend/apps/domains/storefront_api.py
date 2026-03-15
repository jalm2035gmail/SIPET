from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from backend.core.dependencies import get_db
from backend.apps.products.models import Product, Category
from backend.apps.domains.models import VendorDomain
from backend.apps.vendors.models import Vendor
from datetime import datetime

router = APIRouter(prefix="/storefront", tags=["storefront"])

@router.get("/")
async def storefront_home(request: Request, db: Session = Depends(get_db)):
    vendor = getattr(request.state, 'vendor', None)
    if not vendor:
        raise HTTPException(status_code=404, detail="Store not found")
    # Registrar visita
    domain = db.query(VendorDomain).filter(VendorDomain.vendor_id == vendor.id).first()
    if domain:
        domain.hits += 1
        domain.last_hit = datetime.utcnow()
        db.commit()
    # Datos de tienda
    return {
        "vendor": {
            "id": vendor.id,
            "store_name": vendor.store_name,
            "description": vendor.description,
            "logo": vendor.logo_url if hasattr(vendor, 'logo_url') else None,
            "theme": vendor.store_theme if hasattr(vendor, 'store_theme') else {},
        },
        "is_custom_domain": getattr(request.state, 'is_custom_domain', False),
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "slug": p.slug,
                "price": p.price,
                "image": p.primary_image
            }
            for p in db.query(Product).filter(Product.vendor_id == vendor.id, Product.status == 'published').limit(12)
        ],
        "categories": [
            {
                "id": c.id,
                "name": c.name,
                "slug": c.slug
            }
            for c in db.query(Category).join(Product, Product.category_id == Category.id)
                .filter(Product.vendor_id == vendor.id, Product.status == 'published')
                .distinct().order_by(Category.name)
        ]
    }

@router.get("/products/")
async def storefront_products(request: Request, db: Session = Depends(get_db)):
    vendor = getattr(request.state, 'vendor', None)
    if not vendor:
        raise HTTPException(status_code=404, detail="Store not found")
    products = db.query(Product).filter(Product.vendor_id == vendor.id, Product.status == 'published').all()
    return [{
        "id": p.id,
        "name": p.name,
        "slug": p.slug,
        "price": p.price,
        "image": p.primary_image
    } for p in products]

@router.get("/products/{slug}/")
async def storefront_product_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    vendor = getattr(request.state, 'vendor', None)
    if not vendor:
        raise HTTPException(status_code=404, detail="Store not found")
    product = db.query(Product).filter(Product.vendor_id == vendor.id, Product.slug == slug, Product.status == 'published').first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    # Related products
    related = db.query(Product).filter(Product.vendor_id == vendor.id, Product.category_id == product.category_id, Product.id != product.id, Product.status == 'published').limit(6).all()
    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "description": product.description,
        "price": product.price,
        "image": product.primary_image,
        "category": product.category_id,
        "related_products": [
            {
                "id": r.id,
                "name": r.name,
                "slug": r.slug,
                "price": r.price,
                "image": r.primary_image
            } for r in related
        ]
    }

@router.get("/categories/")
async def storefront_categories(request: Request, db: Session = Depends(get_db)):
    vendor = getattr(request.state, 'vendor', None)
    if not vendor:
        raise HTTPException(status_code=404, detail="Store not found")
    categories = db.query(Category).join(Product, Product.category_id == Category.id)
    categories = categories.filter(Product.vendor_id == vendor.id, Product.status == 'published').distinct().order_by(Category.name).all()
    return [{
        "id": c.id,
        "name": c.name,
        "slug": c.slug
    } for c in categories]

@router.get("/categories/{slug}/")
async def storefront_category_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    vendor = getattr(request.state, 'vendor', None)
    if not vendor:
        raise HTTPException(status_code=404, detail="Store not found")
    category = db.query(Category).filter(Category.slug == slug).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    products = db.query(Product).filter(Product.vendor_id == vendor.id, Product.category_id == category.id, Product.status == 'published').all()
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "slug": p.slug,
                "price": p.price,
                "image": p.primary_image
            } for p in products
        ]
    }

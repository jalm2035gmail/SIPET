from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from apps.products.models import Product, ProductImage
from apps.vendors.models import VendorStore
from apps.products.schemas import ProductCreate, ProductUpdate, ProductRead
from core.db import get_db
from apps.users.routes import require_role

def get_current_vendor(user=Depends(require_role("vendor")), db: Session = Depends(get_db)):
    store = db.query(VendorStore).filter_by(vendor_id=user.id).first()
    if not store:
        raise HTTPException(status_code=403, detail="Vendor store not found")
    return store

router = APIRouter(prefix="/api/vendor/products", tags=["vendor-products"])

@router.get("/", response_model=List[ProductRead])
def get_vendor_products(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_vendor: VendorStore = Depends(get_current_vendor)
):
    query = db.query(Product).filter(Product.vendor_id == current_vendor.id)
    if status:
        query = query.filter(Product.status == status)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    products = query.order_by(Product.created_at.desc())\
                   .offset((page - 1) * limit)\
                   .limit(limit)\
                   .all()
    return products

@router.post("/", response_model=ProductRead)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_vendor: VendorStore = Depends(get_current_vendor)
):
    product = Product(
        vendor_id=current_vendor.id,
        **product_data.dict(exclude={'images'})
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

@router.put("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_vendor: VendorStore = Depends(get_current_vendor)
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.vendor_id == current_vendor.id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    for field, value in product_data.dict(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product

@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_vendor: VendorStore = Depends(get_current_vendor)
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.vendor_id == current_vendor.id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.status = 'archived'
    db.commit()
    return {"message": "Product archived"}

@router.get("/inventory/low-stock", response_model=List[ProductRead])
def get_low_stock_products(
    db: Session = Depends(get_db),
    current_vendor: VendorStore = Depends(get_current_vendor)
):
    low_stock = db.query(Product).filter(
        Product.vendor_id == current_vendor.id,
        Product.manage_stock == True,
        Product.stock_quantity <= Product.low_stock_threshold,
        Product.status == 'published'
    ).all()
    return low_stock

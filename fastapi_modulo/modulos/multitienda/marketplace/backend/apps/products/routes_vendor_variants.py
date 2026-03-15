from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
from apps.products.models import Product, ProductVariant
from apps.vendors.models import VendorStore
from apps.products.schemas import ProductVariantRead
from core.db import get_db
from apps.users.routes import require_role

def get_current_vendor(user=Depends(require_role("vendor")), db: Session = Depends(get_db)):
    store = db.query(VendorStore).filter_by(vendor_id=user.id).first()
    if not store:
        raise HTTPException(status_code=403, detail="Vendor store not found")
    return store

router = APIRouter(prefix="/api/vendor/products", tags=["vendor-products"])

@router.get("/{product_id}/variants", response_model=List[ProductVariantRead])
def list_variants(
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
    return product.variants

@router.post("/{product_id}/variants", response_model=ProductVariantRead)
def create_variant(
    product_id: int,
    variant_data: Dict,
    db: Session = Depends(get_db),
    current_vendor: VendorStore = Depends(get_current_vendor)
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.vendor_id == current_vendor.id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    variant = ProductVariant(
        product_id=product_id,
        **variant_data
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant

@router.put("/variants/{variant_id}", response_model=ProductVariantRead)
def update_variant(
    variant_id: int,
    variant_data: Dict,
    db: Session = Depends(get_db),
    current_vendor: VendorStore = Depends(get_current_vendor)
):
    variant = db.query(ProductVariant).join(Product).filter(
        ProductVariant.id == variant_id,
        Product.vendor_id == current_vendor.id
    ).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    for field, value in variant_data.items():
        setattr(variant, field, value)
    db.commit()
    db.refresh(variant)
    return variant

@router.delete("/variants/{variant_id}")
def delete_variant(
    variant_id: int,
    db: Session = Depends(get_db),
    current_vendor: VendorStore = Depends(get_current_vendor)
):
    variant = db.query(ProductVariant).join(Product).filter(
        ProductVariant.id == variant_id,
        Product.vendor_id == current_vendor.id
    ).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    db.delete(variant)
    db.commit()
    return {"message": "Variant deleted"}

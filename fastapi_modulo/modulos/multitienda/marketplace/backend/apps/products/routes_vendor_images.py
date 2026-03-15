from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import os, shutil
from apps.products.models import Product, ProductImage
from apps.vendors.models import VendorStore
from core.db import get_db
from apps.users.routes import require_role

def get_current_vendor(user=Depends(require_role("vendor")), db: Session = Depends(get_db)):
    store = db.query(VendorStore).filter_by(vendor_id=user.id).first()
    if not store:
        raise HTTPException(status_code=403, detail="Vendor store not found")
    return store

router = APIRouter(prefix="/api/vendor/products", tags=["vendor-products"])

@router.post("/{product_id}/images")
async def upload_product_images(
    product_id: int,
    images: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_vendor: VendorStore = Depends(get_current_vendor)
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.vendor_id == current_vendor.id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    uploaded_images = []
    for image_file in images:
        file_dir = f"uploads/products/{product_id}/"
        os.makedirs(file_dir, exist_ok=True)
        file_path = os.path.join(file_dir, image_file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)
        product_image = ProductImage(
            product_id=product_id,
            image=file_path,
            alt_text=image_file.filename,
            is_primary=False
        )
        db.add(product_image)
        uploaded_images.append({
            "id": product_image.id,
            "image": file_path,
            "alt_text": image_file.filename,
            "is_primary": False
        })
    db.commit()
    return {"images": uploaded_images}

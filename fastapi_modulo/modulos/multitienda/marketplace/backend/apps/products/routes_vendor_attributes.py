from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from apps.products.models import ProductAttribute
from apps.products.schemas import ProductAttributeRead, ProductAttributeCreate
from core.db import get_db
from apps.users.routes import require_role

router = APIRouter(prefix="/api/vendor/products/attributes", tags=["vendor-products"])

@router.get("/", response_model=List[ProductAttributeRead])
def list_attributes(db: Session = Depends(get_db), user=Depends(require_role("vendor"))):
    return db.query(ProductAttribute).all()

@router.post("/", response_model=ProductAttributeRead)
def create_attribute(data: ProductAttributeCreate, db: Session = Depends(get_db), user=Depends(require_role("vendor"))):
    attr = ProductAttribute(**data.dict())
    db.add(attr)
    db.commit()
    db.refresh(attr)
    return attr

@router.put("/{attribute_id}", response_model=ProductAttributeRead)
def update_attribute(attribute_id: int, data: ProductAttributeCreate, db: Session = Depends(get_db), user=Depends(require_role("vendor"))):
    attr = db.query(ProductAttribute).filter_by(id=attribute_id).first()
    if not attr:
        raise HTTPException(status_code=404, detail="Attribute not found")
    for field, value in data.dict().items():
        setattr(attr, field, value)
    db.commit()
    db.refresh(attr)
    return attr

@router.delete("/{attribute_id}")
def delete_attribute(attribute_id: int, db: Session = Depends(get_db), user=Depends(require_role("vendor"))):
    attr = db.query(ProductAttribute).filter_by(id=attribute_id).first()
    if not attr:
        raise HTTPException(status_code=404, detail="Attribute not found")
    db.delete(attr)
    db.commit()
    return {"message": "Attribute deleted"}

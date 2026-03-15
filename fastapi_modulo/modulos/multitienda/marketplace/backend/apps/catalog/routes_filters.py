from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from apps.products.models import Category, ProductAttribute
from core.db import get_db

router = APIRouter(prefix="/api/catalog", tags=["catalog"])

@router.get("/filters")
def get_category_filters(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Devuelve los atributos configurables para filtrar productos en una categoría.
    """
    if not category:
        return []
    cat = db.query(Category).filter(Category.slug == category).first()
    if not cat:
        return []
    # Aquí puedes extender para ProductFilter si tienes ese modelo
    # Por ahora, devuelve todos los atributos
    attrs = db.query(ProductAttribute).all()
    return [
        {"id": attr.id, "name": attr.name, "slug": attr.slug}
        for attr in attrs
    ]

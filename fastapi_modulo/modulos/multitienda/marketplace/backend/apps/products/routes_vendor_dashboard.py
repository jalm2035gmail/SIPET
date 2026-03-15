from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from apps.products.models import Product
from apps.vendors.models import VendorStore
from core.db import get_db
from apps.users.routes import require_role

router = APIRouter(prefix="/api/vendor/dashboard", tags=["vendor-dashboard"])

def get_current_vendor(user=Depends(require_role("vendor")), db: Session = Depends(get_db)):
    store = db.query(VendorStore).filter_by(vendor_id=user.id).first()
    if not store:
        raise HTTPException(status_code=403, detail="Vendor store not found")
    return store

@router.get("/stats")
def vendor_dashboard_stats(
    db: Session = Depends(get_db),
    current_vendor: VendorStore = Depends(get_current_vendor)
):
    # Total productos
    total_products = db.query(Product).filter(Product.vendor_id == current_vendor.id).count()
    # Total ventas (requiere modelo de órdenes/pagos, aquí ejemplo dummy)
    total_sales = float(getattr(current_vendor, "total_sales", 0.0))
    # Total órdenes (requiere modelo de órdenes, aquí ejemplo dummy)
    total_orders = 0  # Reemplaza con query real si tienes modelo Order
    # Vistas de tienda (requiere tracking, aquí ejemplo dummy)
    store_views = 0
    return {
        "total_products": total_products,
        "total_sales": total_sales,
        "total_orders": total_orders,
        "store_views": store_views
    }



from fastapi import APIRouter, Depends, HTTPException, Query, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from datetime import datetime, timedelta
import secrets
import hashlib
import hmac
import json
from backend.core.dependencies import get_db
from .models_api import VendorAPIKey
from backend.apps.products.models import Product
from .schemas_api import ProductCreate, ProductUpdate

router = APIRouter(prefix="/api/v1/vendor", tags=["vendor-api"])
security = HTTPBearer()

async def get_api_client(
	authorization: HTTPAuthorizationCredentials = Depends(security),
	x_forwarded_for: Optional[str] = Header(None),
	db: Session = Depends(get_db)
):
	api_key_hash = hashlib.sha256(authorization.credentials.encode()).hexdigest()
	api_key = db.query(VendorAPIKey).filter(
		VendorAPIKey.key == api_key_hash,
		VendorAPIKey.is_active == True
	).first()
	if not api_key:
		raise HTTPException(status_code=401, detail="Invalid API key")
	if api_key.expires_at and api_key.expires_at < datetime.utcnow():
		raise HTTPException(status_code=401, detail="API key expired")
	client_ip = x_forwarded_for.split(',')[0] if x_forwarded_for else "127.0.0.1"
	if api_key.allowed_ips and client_ip not in api_key.allowed_ips:
		raise HTTPException(status_code=403, detail="IP address not allowed")
	# TODO: Implementar rate limit y usage_count si es necesario
	return api_key


# --- PRODUCT ENDPOINTS ---
@router.get("/products", response_model=List[ProductCreate])
def list_products(
	db: Session = Depends(get_db),
	api_key=Depends(get_api_client),
	status: Optional[str] = Query(None),
	q: Optional[str] = Query(None),
	skip: int = 0,
	limit: int = 50
):
	query = db.query(Product).filter(Product.vendor_id == api_key.vendor_id)
	if status:
		query = query.filter(Product.status == status)
	if q:
		query = query.filter(Product.name.ilike(f"%{q}%"))
	products = query.offset(skip).limit(limit).all()
	return products


@router.post("/products", response_model=ProductCreate)
def create_product(
	product_in: ProductCreate,
	db: Session = Depends(get_db),
	api_key=Depends(get_api_client)
):
	product = Product(
		vendor_id=api_key.vendor_id,
		name=product_in.name,
		description=product_in.description or "",
		price=product_in.price,
		stock_quantity=product_in.stock_quantity,
		status=product_in.status or "draft",
		# TODO: add more fields as needed
		slug=product_in.name.lower().replace(" ", "-")
	)
	db.add(product)
	db.commit()
	db.refresh(product)
	return product


@router.put("/products/{product_id}", response_model=ProductCreate)
def update_product(
	product_id: int,
	product_in: ProductUpdate,
	db: Session = Depends(get_db),
	api_key=Depends(get_api_client)
):
	product = db.query(Product).filter(Product.id == product_id, Product.vendor_id == api_key.vendor_id).first()
	if not product:
		raise HTTPException(status_code=404, detail="Product not found")
	for field, value in product_in.dict(exclude_unset=True).items():
		setattr(product, field, value)
	db.commit()
	db.refresh(product)
	return product

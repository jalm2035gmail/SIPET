from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from apps.vendors import models, schemas
from core.db import SessionLocal
from apps.users.models import User, UserType
from apps.users.routes import require_role
from typing import List, Optional
import bcrypt
import os
import shutil

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ADMIN ENDPOINTS ---

# Listar vendedores con filtros (solo superadmin)
@router.get("/admin/vendors/", response_model=List[schemas.VendorStoreRead])
def admin_list_vendors(
    status: Optional[str] = None,
    country: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(require_role("superadmin"))
):
    query = db.query(models.VendorStore)
    if status:
        query = query.filter(models.VendorStore.status == status)
    if country:
        query = query.filter(models.VendorStore.country == country)
    return query.all()

# Aprobar vendedores (masivo)
@router.post("/admin/vendors/approve/")
def approve_vendors(
    vendor_ids: List[int],
    db: Session = Depends(get_db),
    user=Depends(require_role("superadmin"))
):
    vendors = db.query(models.VendorStore).filter(models.VendorStore.id.in_(vendor_ids)).all()
    for vendor in vendors:
        vendor.status = "approved"
        vendor.is_active = True
        if vendor.vendor:
            vendor.vendor.is_active = True
        # TODO: enviar email de aprobación
    db.commit()
    return {"success": True, "count": len(vendors)}

# Rechazar vendedores (masivo)
@router.post("/admin/vendors/reject/")
def reject_vendors(
    vendor_ids: List[int],
    db: Session = Depends(get_db),
    user=Depends(require_role("superadmin"))
):
    vendors = db.query(models.VendorStore).filter(models.VendorStore.id.in_(vendor_ids)).all()
    for vendor in vendors:
        vendor.status = "rejected"
        vendor.is_active = False
        # TODO: enviar email de rechazo
    db.commit()
    return {"success": True, "count": len(vendors)}

# Ver documentos de un vendedor
@router.get("/admin/vendors/{vendor_id}/documents/", response_model=List[schemas.VendorDocumentRead])
def list_vendor_documents(
    vendor_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("superadmin"))
):
    docs = db.query(models.VendorDocument).filter_by(vendor_id=vendor_id).all()
    return docs

# Registro de vendedor (usuario + tienda, desactivados hasta aprobación)
@router.post("/register-vendor/")
def register_vendor(data: schemas.VendorRegistrationRequest, db: Session = Depends(get_db)):
    if db.query(User).filter_by(username=data.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    if db.query(User).filter_by(email=data.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    hashed_password = bcrypt.hashpw(data.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hashed_password,
        user_type=UserType.vendor,
        two_factor_enabled=data.two_factor_enabled,
        # first_name=data.first_name,  # Si tu modelo User lo soporta
        # last_name=data.last_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    store = models.VendorStore(
        vendor_id=user.id,
        store_name=data.store_name,
        phone=data.phone,
        address=data.address,
        country=data.country,
        status="pending",
        is_active=False
    )
    db.add(store)
    db.commit()
    return {"success": True, "message": "Vendor registered, pending approval"}

# Crear tienda (solo vendor)
@router.post("/", response_model=schemas.VendorStoreRead)
def create_store(store: schemas.VendorStoreCreate, db: Session = Depends(get_db), user=Depends(require_role("vendor"))):
    if db.query(models.VendorStore).filter_by(vendor_id=user.id).first():
        raise HTTPException(status_code=400, detail="Vendor already has a store")
    if db.query(models.VendorStore).filter_by(store_slug=store.store_slug).first():
        raise HTTPException(status_code=400, detail="Slug already exists")
    db_store = models.VendorStore(
        vendor_id=user.id,
        store_name=store.store_name,
        store_slug=store.store_slug,
        store_theme=store.store_theme,
        commission_rate=store.commission_rate,
        is_active=store.is_active
    )
    db.add(db_store)
    db.commit()
    db.refresh(db_store)
    return db_store

# Obtener tienda propia (solo vendor)
@router.get("/me", response_model=schemas.VendorStoreRead)
def get_my_store(db: Session = Depends(get_db), user=Depends(require_role("vendor"))):
    store = db.query(models.VendorStore).filter_by(vendor_id=user.id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store

# Listar todas las tiendas (público)
@router.get("/", response_model=list[schemas.VendorStoreRead])
def list_stores(db: Session = Depends(get_db)):
    return db.query(models.VendorStore).all()

# Obtener tienda por slug (público)
@router.get("/slug/{store_slug}", response_model=schemas.VendorStoreRead)
def get_store_by_slug(store_slug: str, db: Session = Depends(get_db)):
    store = db.query(models.VendorStore).filter_by(store_slug=store_slug).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store

# Actualizar tienda (solo vendor dueño)
@router.put("/me", response_model=schemas.VendorStoreRead)
def update_my_store(update: schemas.VendorStoreCreate, db: Session = Depends(get_db), user=Depends(require_role("vendor"))):
    store = db.query(models.VendorStore).filter_by(vendor_id=user.id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    for field, value in update.dict(exclude_unset=True).items():
        setattr(store, field, value)
    db.commit()
    db.refresh(store)
    return store

# Eliminar tienda (solo vendor dueño)
@router.delete("/me", status_code=204)
def delete_my_store(db: Session = Depends(get_db), user=Depends(require_role("vendor"))):
    store = db.query(models.VendorStore).filter_by(vendor_id=user.id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    db.delete(store)
    db.commit()

# Carga de documento KYC para vendedor autenticado
@router.post("/upload-document/")
async def upload_vendor_document(
    document_type: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor"))
):
    # Busca la tienda del usuario actual
    store = db.query(models.VendorStore).filter_by(vendor_id=user.id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Vendor store not found")
    # Guardar archivo localmente (puedes adaptar a S3/MinIO)
    file_dir = f"uploads/vendors/{store.id}/documents/"
    os.makedirs(file_dir, exist_ok=True)
    file_path = os.path.join(file_dir, f"{document_type}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    # Guardar registro en base de datos
    document = models.VendorDocument(
        vendor_id=store.id,
        document_type=document_type,
        file=file_path
    )
    db.add(document)
    db.commit()
    return {"message": "Document uploaded successfully"}

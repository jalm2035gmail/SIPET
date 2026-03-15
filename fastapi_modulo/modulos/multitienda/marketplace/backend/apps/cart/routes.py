from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from backend.core.db import get_db
from backend.apps.cart.models import Cart, CartItem
from backend.apps.products.models import Product, ProductVariant
from backend.apps.vendors.models import VendorStore
from backend.apps.users.models import User
from backend.apps.cart.schemas import CartItemCreate, CartItemUpdate
from backend.core.auth import get_current_user_or_none
from decimal import Decimal
import secrets

router = APIRouter(prefix="/api/cart", tags=["cart"])

def get_or_create_cart(request: Request, db: Session, user: Optional[User] = None):
    cart = None
    if user and getattr(user, 'id', None):
        cart = db.query(Cart).filter(Cart.user_id == user.id).first()
    if not cart:
        session_key = request.cookies.get('session_id')
        if session_key:
            cart = db.query(Cart).filter(Cart.session_key == session_key).first()
    if not cart:
        cart = Cart()
        if user and getattr(user, 'id', None):
            cart.user_id = user.id
        else:
            session_key = request.cookies.get('session_id') or secrets.token_urlsafe(32)
            cart.session_key = session_key
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart

def calculate_shipping_cost(vendor, items):
    # Simplificado: flat rate por vendedor
    return Decimal('5.00')

@router.get("/")
async def get_cart(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_or_none)
):
    cart = get_or_create_cart(request, db, current_user)
    items = db.query(CartItem).filter(CartItem.cart_id == cart.id).options(
        joinedload(CartItem.product).joinedload(Product.vendor),
        joinedload(CartItem.variant),
        joinedload(CartItem.product).joinedload(Product.images)
    ).all()
    subtotal = sum(item.get_total() for item in items)
    items_by_vendor = {}
    for item in items:
        vendor_id = item.product.vendor_id
        if vendor_id not in items_by_vendor:
            items_by_vendor[vendor_id] = {
                'vendor': item.product.vendor,
                'items': [],
                'subtotal': Decimal('0.00'),
                'shipping_cost': Decimal('0.00')
            }
        items_by_vendor[vendor_id]['items'].append(item)
        items_by_vendor[vendor_id]['subtotal'] += item.get_total()
    shipping_total = 0
    for vendor_data in items_by_vendor.values():
        vendor_data['shipping_cost'] = calculate_shipping_cost(
            vendor_data['vendor'],
            vendor_data['items']
        )
        shipping_total += vendor_data['shipping_cost']
    total = subtotal + shipping_total
    return {
        "cart": {
            "id": cart.id,
            "items_count": len(items),
            "subtotal": float(subtotal),
            "shipping_total": float(shipping_total),
            "total": float(total)
        },
        "items": [
            {
                "id": item.id,
                "product": {
                    "id": item.product.id,
                    "name": item.product.name,
                    "slug": item.product.slug,
                    "image": getattr(item.product, 'primary_image', None),
                    "vendor": {
                        "id": item.product.vendor.id,
                        "name": item.product.vendor.store_name,
                        "slug": item.product.vendor.store_slug
                    }
                },
                "variant": item.variant_id,
                "quantity": item.quantity,
                "price": float(item.price),
                "total": float(item.get_total()),
                "is_available": item.is_available()
            }
            for item in items
        ],
        "grouped_by_vendor": [
            {
                "vendor": {
                    "id": data['vendor'].id,
                    "name": data['vendor'].store_name,
                    "slug": data['vendor'].store_slug
                },
                "items": [
                    {
                        "id": item.id,
                        "product_name": item.product.name,
                        "quantity": item.quantity,
                        "price": float(item.price)
                    }
                    for item in data['items']
                ],
                "subtotal": float(data['subtotal']),
                "shipping_cost": float(data['shipping_cost']),
                "vendor_total": float(data['subtotal'] + data['shipping_cost'])
            }
            for vendor_id, data in items_by_vendor.items()
        ]
    }

@router.post("/items")
async def add_to_cart(
    request: Request,
    response: Response,
    item_data: CartItemCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_or_none)
):
    cart = get_or_create_cart(request, db, current_user)
    product = db.query(Product).filter(
        Product.id == item_data.product_id,
        Product.status == 'published'
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    variant = None
    if item_data.variant_id:
        variant = db.query(ProductVariant).filter(
            ProductVariant.id == item_data.variant_id,
            ProductVariant.product_id == product.id
        ).first()
        if not variant:
            raise HTTPException(status_code=404, detail="Variant not found")
    if product.manage_stock:
        if variant:
            if variant.stock_quantity < item_data.quantity:
                raise HTTPException(status_code=400, detail="Insufficient stock")
        else:
            if product.stock_quantity < item_data.quantity:
                raise HTTPException(status_code=400, detail="Insufficient stock")
    existing_item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == product.id,
        CartItem.variant_id == (variant.id if variant else None)
    ).first()
    if existing_item:
        existing_item.quantity += item_data.quantity
        if product.manage_stock:
            total_quantity = existing_item.quantity
            if variant:
                if variant.stock_quantity < total_quantity:
                    raise HTTPException(status_code=400, detail="Insufficient stock")
            elif product.stock_quantity < total_quantity:
                raise HTTPException(status_code=400, detail="Insufficient stock")
    else:
        existing_item = CartItem(
            cart_id=cart.id,
            product_id=product.id,
            variant_id=variant.id if variant else None,
            quantity=item_data.quantity,
            price=variant.price if variant else product.price
        )
        db.add(existing_item)
    db.commit()
    db.refresh(existing_item)
    if not current_user and not request.cookies.get('session_id'):
        response.set_cookie(
            key='session_id',
            value=cart.session_key,
            httponly=True,
            max_age=30 * 24 * 60 * 60
        )
    return {"message": "Item added to cart", "item_id": existing_item.id}

@router.put("/items/{item_id}")
async def update_cart_item(
    item_id: int,
    update_data: CartItemUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_or_none)
):
    cart = get_or_create_cart(request, db, current_user)
    item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.cart_id == cart.id
    ).options(joinedload(CartItem.product)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found in cart")
    if update_data.quantity > item.quantity:
        if item.product.manage_stock:
            if item.variant:
                variant = db.query(ProductVariant).get(item.variant_id)
                if variant.stock_quantity < update_data.quantity:
                    raise HTTPException(status_code=400, detail="Insufficient stock")
            elif item.product.stock_quantity < update_data.quantity:
                raise HTTPException(status_code=400, detail="Insufficient stock")
    if update_data.quantity <= 0:
        db.delete(item)
    else:
        item.quantity = update_data.quantity
    db.commit()
    return {"message": "Cart updated"}

@router.delete("/items/{item_id}")
async def remove_cart_item(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_or_none)
):
    cart = get_or_create_cart(request, db, current_user)
    item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.cart_id == cart.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found in cart")
    db.delete(item)
    db.commit()
    return {"message": "Item removed from cart"}

@router.delete("/")
async def clear_cart(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_or_none)
):
    cart = get_or_create_cart(request, db, current_user)
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()
    return {"message": "Cart cleared"}

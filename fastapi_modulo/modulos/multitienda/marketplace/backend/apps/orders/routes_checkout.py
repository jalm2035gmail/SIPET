from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from backend.core.db import get_db
from backend.apps.cart.models import Cart, CartItem
from backend.apps.orders.models import Order, OrderItem, ShippingGroup
from backend.apps.cart.routes import get_or_create_cart
from backend.apps.users.models import User
from backend.core.auth import get_current_user_or_none
from backend.apps.cart.schemas import AddressSchema, PaymentIntentCreate, OrderCreate
from backend.core.settings import settings
from backend.apps.orders.notifications import send_order_confirmation_email, notify_vendors_new_order, update_vendor_sales_stats
from backend.apps.commissions.utils import calculate_order_item_commission
import stripe
import json
from decimal import Decimal

router = APIRouter(prefix="/api/checkout", tags=["checkout"])

# --- Utilidades simplificadas ---
def calculate_shipping_options(cart, db):
    # Devuelve opciones dummy por vendor
    items_by_vendor = cart.get_items_by_vendor()
    return [
        {
            "vendor_id": v_id,
            "methods": [
                {"id": "standard", "label": "Standard Shipping", "cost": 5.0},
                {"id": "express", "label": "Express Shipping", "cost": 15.0}
            ]
        }
        for v_id in items_by_vendor.keys()
    ]

def get_vendor_shipping_methods(vendor, address, items):
    return [
        {"id": "standard", "label": "Standard Shipping", "cost": 5.0},
        {"id": "express", "label": "Express Shipping", "cost": 15.0}
    ]

def calculate_shipping_total(shipping_methods):
    return sum(m.get('cost', 0) for m in shipping_methods.values())

def calculate_tax(amount, shipping_address):
    return round(amount * 0.16, 2)  # 16% ejemplo

def requires_shipping(product):
    return True  # Simplificado

# --- Endpoints ---
@router.post("/validate")
async def validate_cart(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_or_none)
):
    cart = get_or_create_cart(request, db, current_user)
    items = db.query(CartItem).filter(CartItem.cart_id == cart.id).options(
        joinedload(CartItem.product),
        joinedload(CartItem.variant)
    ).all()
    if not items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    validation_errors = []
    cart_total = 0
    for item in items:
        if not item.is_available():
            validation_errors.append({
                "item_id": item.id,
                "product_name": item.product.name,
                "error": "Out of stock"
            })
            continue
        current_price = item.variant.price if item.variant else item.product.price
        if current_price != item.price:
            validation_errors.append({
                "item_id": item.id,
                "product_name": item.product.name,
                "error": "Price has changed",
                "old_price": float(item.price),
                "new_price": float(current_price)
            })
        cart_total += float(item.get_total())
    shipping_options = calculate_shipping_options(cart, db)
    return {
        "valid": len(validation_errors) == 0,
        "cart_total": cart_total,
        "shipping_options": shipping_options,
        "errors": validation_errors,
        "requires_shipping": any(requires_shipping(item.product) for item in items)
    }

@router.post("/shipping-methods")
async def get_shipping_methods(
    address: AddressSchema,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_or_none)
):
    cart = get_or_create_cart(request, db, current_user)
    items_by_vendor = cart.get_items_by_vendor()
    shipping_methods = []
    for vendor_id, vendor_data in items_by_vendor.items():
        vendor = vendor_data['vendor']
        methods = get_vendor_shipping_methods(vendor, address, vendor_data['items'])
        shipping_methods.append({
            "vendor": {
                "id": vendor.id,
                "name": vendor.store_name
            },
            "methods": methods
        })
    return shipping_methods

@router.post("/create-payment-intent")
async def create_payment_intent(
    payment_data: PaymentIntentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_or_none)
):
    cart = get_or_create_cart(request, db, current_user)
    validation = await validate_cart(request, db, current_user)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail="Cart validation failed")
    cart_items = db.query(CartItem).filter(CartItem.cart_id == cart.id).all()
    subtotal = sum(float(item.get_total()) for item in cart_items)
    shipping_total = calculate_shipping_total(payment_data.shipping_methods)
    tax_amount = calculate_tax(subtotal + shipping_total, payment_data.shipping_address)
    total_amount = subtotal + shipping_total + tax_amount
    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(total_amount * 100),
            currency='usd',
            payment_method_types=['card'],
            metadata={
                'cart_id': str(cart.id),
                'user_id': str(current_user.id) if current_user else 'guest',
                'shipping_address': json.dumps(payment_data.shipping_address)
            }
        )
        # Aquí deberías guardar la sesión de checkout temporal
        return {
            "client_secret": intent.client_secret,
            "amount": total_amount,
            "payment_intent_id": intent.id
        }
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/create-order")
async def create_order(
    checkout_data: OrderCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_or_none)
):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        payment_intent = stripe.PaymentIntent.retrieve(
            checkout_data.payment_intent_id
        )
        if payment_intent.status != 'succeeded':
            raise HTTPException(status_code=400, detail="Payment not succeeded")

        # Obtener carrito y items
        cart = get_or_create_cart(checkout_data.request, db, current_user)
        cart_items = db.query(CartItem).filter(CartItem.cart_id == cart.id).options(
            joinedload(CartItem.product),
            joinedload(CartItem.variant)
        ).all()
        if not cart_items:
            raise HTTPException(status_code=400, detail="Cart is empty")

        # Calcular totales
        subtotal = sum(float(item.get_total()) for item in cart_items)
        shipping_total = calculate_shipping_total(checkout_data.shipping_methods)
        tax_amount = calculate_tax(subtotal + shipping_total, checkout_data.shipping_address)
        total_amount = subtotal + shipping_total + tax_amount

        # Crear la orden
        order = Order(
            order_number=f"ORD-{str(payment_intent.id)[-8:]}",
            customer_id=current_user.id if current_user else None,
            guest_email=checkout_data.guest_email if not current_user else None,
            billing_address=checkout_data.billing_address,
            shipping_address=checkout_data.shipping_address,
            status="pending",
            payment_status="paid",
            subtotal=subtotal,
            tax_amount=tax_amount,
            shipping_total=shipping_total,
            discount_amount=0,
            total=total_amount,
            payment_method="stripe",
            payment_transaction_id=payment_intent.id,
            shipping_method=", ".join([m['id'] for m in checkout_data.shipping_methods.values()]) if hasattr(checkout_data.shipping_methods, 'values') else '',
            customer_note=getattr(checkout_data, 'customer_note', ''),
        )
        db.add(order)
        db.flush()  # Para obtener order.id

        # Crear OrderItems con cálculo de comisión
        for item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                vendor_id=item.product.vendor_id,
                product_id=item.product_id,
                variant_id=item.variant_id,
                product_name=item.product.name,
                product_sku=getattr(item.variant, 'sku', '') if item.variant else getattr(item.product, 'sku', ''),
                price=item.price,
                compare_price=getattr(item.variant, 'compare_price', None) if item.variant else getattr(item.product, 'compare_price', None),
                quantity=item.quantity,
                total=item.get_total(),
                item_status="pending",
                platform_commission=0,  # Se calcula abajo
                vendor_amount=0,        # Se calcula abajo
            )
            # Cálculo de comisión
            commission = calculate_order_item_commission(db, order_item)
            order_item.platform_commission = commission
            order_item.vendor_amount = order_item.total - commission
            db.add(order_item)

        # Crear ShippingGroups por vendor
        items_by_vendor = {}
        for item in cart_items:
            v_id = item.product.vendor_id
            if v_id not in items_by_vendor:
                items_by_vendor[v_id] = []
            items_by_vendor[v_id].append(item)
        for vendor_id, items in items_by_vendor.items():
            sg = ShippingGroup(
                order_id=order.id,
                vendor_id=vendor_id,
                shipping_method=checkout_data.shipping_methods[str(vendor_id)]["id"] if str(vendor_id) in checkout_data.shipping_methods else "standard",
                shipping_cost=checkout_data.shipping_methods[str(vendor_id)]["cost"] if str(vendor_id) in checkout_data.shipping_methods else 5.0,
                status="pending"
            )
            db.add(sg)

        # Crear Payment
        payment = Payment(
            order_id=order.id,
            payment_method="stripe",
            transaction_id=payment_intent.id,
            amount=total_amount,
            status="paid",
            payment_details={"stripe": payment_intent.id}
        )
        db.add(payment)

        # Limpiar carrito
        db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()

        db.commit()
        db.refresh(order)

        # Notificaciones y stats
        background_tasks.add_task(send_order_confirmation_email, order)
        background_tasks.add_task(notify_vendors_new_order, order)
        background_tasks.add_task(update_vendor_sales_stats, order)

        return {
            "order_number": order.order_number,
            "order_id": order.id,
            "total": float(order.total),
            "message": "Order created successfully"
        }
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

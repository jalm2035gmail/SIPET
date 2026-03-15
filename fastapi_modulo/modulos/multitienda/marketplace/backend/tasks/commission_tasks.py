from celery import shared_task
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, exists
from decimal import Decimal
import logging

from backend.core.db import get_db_session
from backend.apps.orders.models import Order, OrderItem
from backend.apps.vendors.models import VendorStore as Vendor
from backend.apps.commissions.models import Payout, PayoutItem, VendorBalance
#from backend.apps.commissions.notifications import send_vendor_payout_notification

logger = logging.getLogger(__name__)

@shared_task
def generate_monthly_payouts():
    """Tarea programada para generar pagos mensuales"""
    today = datetime.now().date()
    first_day_of_current_month = today.replace(day=1)
    last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
    first_day_of_previous_month = last_day_of_previous_month.replace(day=1)
    logger.info(f"Generating payouts for period: {first_day_of_previous_month} to {last_day_of_previous_month}")
    db: Session = get_db_session()
    vendors = db.query(Vendor).filter(
        Vendor.status == 'approved',
        Vendor.is_active == True
    ).all()
    for vendor in vendors:
        order_items = db.query(OrderItem).join(Order).filter(
            OrderItem.vendor_id == vendor.id,
            Order.status == 'completed',
            Order.payment_status == 'paid',
            Order.completed_at >= first_day_of_previous_month,
            Order.completed_at <= last_day_of_previous_month,
            ~exists().where(and_(
                PayoutItem.order_item_id == OrderItem.id,
                PayoutItem.payout.has(Payout.status.in_(['pending', 'processing', 'paid']))
            ))
        ).all()
        if not order_items:
            continue
        total_sales = sum(item.total for item in order_items)
        total_commission = sum(item.platform_commission for item in order_items)
        payout = Payout(
            vendor_id=vendor.id,
            payout_period_start=first_day_of_previous_month,
            payout_period_end=last_day_of_previous_month,
            payout_date=today,
            total_sales=total_sales,
            total_commission=total_commission,
            payment_method=getattr(vendor, 'default_payment_method', 'bank_transfer'),
            status='pending'
        )
        db.add(payout)
        db.commit()
        for item in order_items:
            payout_item = PayoutItem(
                payout_id=payout.id,
                order_id=item.order_id,
                order_item_id=item.id,
                item_amount=item.total,
                commission_amount=item.platform_commission,
                net_amount=item.vendor_amount
            )
            db.add(payout_item)
        db.commit()
        logger.info(f"Created payout {payout.reference_number} for vendor {vendor.store_name}")
        #send_vendor_payout_notification.delay(vendor.id, payout.id)
    logger.info("Monthly payouts generation completed")

@shared_task
def update_vendor_balances():
    """Actualizar balances de vendedores basado en órdenes completadas"""
    db: Session = get_db_session()
    order_items = db.query(OrderItem).join(Order).filter(
        Order.status == 'completed',
        Order.payment_status == 'paid',
        getattr(OrderItem, 'balance_recorded', False) == False
    ).all()
    for item in order_items:
        VendorBalance.record_transaction(
            db=db,
            vendor=item.vendor,
            transaction_type='sale',
            amount=item.total,
            description=f"Sale from order {item.order.order_number}",
            order=item.order
        )
        VendorBalance.record_transaction(
            db=db,
            vendor=item.vendor,
            transaction_type='commission',
            amount=-item.platform_commission,
            description=f"Platform commission from order {item.order.order_number}",
            order=item.order
        )
        item.balance_recorded = True
        db.add(item)
    db.commit()
    logger.info(f"Updated balances for {len(order_items)} order items")

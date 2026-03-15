from decimal import Decimal
from backend.apps.commissions.models import CommissionPlan, VendorCommission

def calculate_order_item_commission(db, order_item):
    vendor = order_item.vendor
    commission_settings = getattr(vendor, 'commission_settings', None)
    if commission_settings:
        return commission_settings.calculate_commission_for_order(order_item)
    # Fallback: buscar plan global
    plan = db.query(CommissionPlan).filter_by(is_active=True).first()
    if plan:
        return plan.calculate_commission(order_item.total)
    # Default 10%
    return (Decimal('10.00') * order_item.total) / 100

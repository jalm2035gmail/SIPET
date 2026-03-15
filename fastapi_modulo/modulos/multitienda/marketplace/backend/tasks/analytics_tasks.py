from celery import shared_task
from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session
from backend.core.db import get_db_session
from backend.apps.analytics.models import VendorAnalytics, CustomerBehavior, PerformanceGoal
from backend.apps.orders.models import Order, OrderItem
from backend.apps.vendors.models import VendorStore as Vendor
from backend.apps.products.models import Product
from backend.apps.reviews.models import ProductReview
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)

@shared_task
def update_vendor_analytics():
    """Actualizar métricas diarias de todos los vendedores (ventas, productos, clientes, etc.)"""
    db: Session = get_db_session()
    today = date.today()
    vendors = db.query(Vendor).all()
    for vendor in vendors:
        # Buscar o crear registro de analytics para hoy
        analytics = db.query(VendorAnalytics).filter_by(vendor_id=vendor.id, date=today).first()
        if not analytics:
            analytics = VendorAnalytics(vendor_id=vendor.id, date=today)
            db.add(analytics)
        # Ventas y órdenes
        order_items = db.query(OrderItem).join(Order).filter(
            OrderItem.vendor_id == vendor.id,
            Order.status == 'completed',
            func.date(Order.completed_at) == today
        ).all()
        analytics.total_orders = len(set([item.order_id for item in order_items]))
        analytics.total_revenue = sum(item.total for item in order_items)
        analytics.total_commission = sum(item.platform_commission for item in order_items)
        analytics.net_earnings = analytics.total_revenue - analytics.total_commission
        analytics.products_sold = sum(item.quantity for item in order_items)
        analytics.unique_customers = len(set([item.order.customer_id for item in order_items if item.order.customer_id]))
        analytics.average_order_value = (analytics.total_revenue / analytics.total_orders) if analytics.total_orders > 0 else 0
        # Productos top
        top_products = {}
        for item in order_items:
            pid = item.product_id
            if pid not in top_products:
                top_products[pid] = {"sales": 0, "quantity": 0}
            top_products[pid]["sales"] += float(item.total)
            top_products[pid]["quantity"] += item.quantity
        analytics.top_products = [{"product_id": k, **v} for k, v in top_products.items()]
        # Por categoría
        category_data = {}
        for item in order_items:
            product = db.query(Product).get(item.product_id)
            if product and getattr(product, 'category_id', None):
                cat_id = product.category_id
                if cat_id not in category_data:
                    category_data[cat_id] = {"sales": 0, "orders": 0, "quantity": 0}
                category_data[cat_id]["sales"] += float(item.total)
                category_data[cat_id]["orders"] += 1
                category_data[cat_id]["quantity"] += item.quantity
        analytics.category_breakdown = category_data
        # Inventario
        analytics.low_stock_alerts = db.query(Product).filter(
            Product.vendor_id == vendor.id,
            Product.manage_stock == True,
            Product.stock_quantity <= getattr(Product, 'low_stock_threshold', 5),
            Product.stock_quantity > 0
        ).count()
        analytics.out_of_stock_products = db.query(Product).filter(
            Product.vendor_id == vendor.id,
            Product.manage_stock == True,
            Product.stock_quantity == 0
        ).count()
        # Satisfacción
        reviews = db.query(ProductReview).join(Product).filter(
            Product.vendor_id == vendor.id,
            ProductReview.is_approved == True,
            func.date(ProductReview.created_at) == today
        ).all()
        analytics.total_reviews = len(reviews)
        analytics.average_rating = sum([r.rating for r in reviews]) / len(reviews) if reviews else 0
        analytics.updated_at = datetime.now()
    db.commit()
    logger.info("Vendor analytics updated for all vendors.")

@shared_task
def update_customer_behaviors():
    """Actualizar comportamientos de clientes"""
    db: Session = get_db_session()
    vendors = db.query(Vendor).all()
    for vendor in vendors:
        customer_orders = db.query(Order.customer_id).filter(
            Order.vendor_id == vendor.id,
            Order.status == 'completed'
        ).distinct()
        for row in customer_orders:
            customer_id = row.customer_id
            if not customer_id:
                continue
            behavior = db.query(CustomerBehavior).filter_by(vendor_id=vendor.id, customer_id=customer_id).first()
            if not behavior:
                behavior = CustomerBehavior(vendor_id=vendor.id, customer_id=customer_id)
                db.add(behavior)
            behavior.calculate_metrics(db)
        logger.info(f"Updated customer behaviors for vendor {vendor.store_name}")
    db.commit()
    db.close()
    logger.info("Completed customer behavior updates")

@shared_task
def check_and_update_goals():
    """Verificar y actualizar progreso de metas"""
    db: Session = get_db_session()
    today = date.today()
    active_goals = db.query(PerformanceGoal).filter(
        PerformanceGoal.end_date >= today,
        PerformanceGoal.is_completed == False
    ).all()
    for goal in active_goals:
        goal.update_progress(db)
        if goal.is_completed:
            logger.info(f"Goal {goal.id} for vendor {goal.vendor_id} completed!")
    db.commit()
    db.close()
    logger.info(f"Updated {len(active_goals)} goals")

@shared_task
def generate_performance_insights():
    """Generar insights de rendimiento para vendedores"""
    db: Session = get_db_session()
    today = date.today()
    last_week = today - timedelta(days=7)
    vendors = db.query(Vendor).all()
    for vendor in vendors:
        weekly_analytics = db.query(VendorAnalytics).filter(
            VendorAnalytics.vendor_id == vendor.id,
            VendorAnalytics.date >= last_week,
            VendorAnalytics.date <= today
        )
        total_revenue = sum(a.total_revenue for a in weekly_analytics)
        total_orders = sum(a.total_orders for a in weekly_analytics)
        avg_conversion = sum(a.conversion_rate for a in weekly_analytics) / (len(weekly_analytics) or 1)
        previous_week_start = last_week - timedelta(days=7)
        previous_week_end = last_week - timedelta(days=1)
        previous_analytics = db.query(VendorAnalytics).filter(
            VendorAnalytics.vendor_id == vendor.id,
            VendorAnalytics.date >= previous_week_start,
            VendorAnalytics.date <= previous_week_end
        )
        prev_total_revenue = sum(a.total_revenue for a in previous_analytics)
        revenue_change = 0
        if prev_total_revenue and total_revenue:
            revenue_change = ((total_revenue - prev_total_revenue) / prev_total_revenue) * 100
        insights = []
        if revenue_change > 20:
            insights.append(f"🎉 Great week! Revenue increased by {revenue_change:.1f}% compared to last week.")
        elif revenue_change < -10:
            insights.append(f"⚠️ Revenue decreased by {abs(revenue_change):.1f}%. Consider reviewing your pricing or promotions.")
        if avg_conversion and avg_conversion < 2:
            insights.append("📊 Low conversion rate detected. Consider optimizing your product pages.")
        if insights:
            logger.info(f"Insights for vendor {vendor.store_name}: {insights}")
    db.close()
    logger.info("Completed performance insights generation")

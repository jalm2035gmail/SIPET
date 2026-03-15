from fastapi import BackgroundTasks
from backend.apps.orders.models import Order
from backend.apps.vendors.models import VendorStore
from backend.apps.users.models import User
from backend.core.settings import settings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Utilidad simple para enviar emails (puedes reemplazar por SendGrid, Mailgun, etc.)
def send_email(subject, to_email, html_body, from_email=None):
    from_email = from_email or settings.DEFAULT_FROM_EMAIL
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        if getattr(settings, 'SMTP_USE_TLS', False):
            server.starttls()
        if getattr(settings, 'SMTP_USER', None):
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(from_email, to_email, msg.as_string())

# Email a cliente
async def send_order_confirmation_email(order: Order):
    subject = f"Order Confirmation - {order.order_number}"
    to_email = order.customer.email if order.customer else order.guest_email
    html_body = f"""
    <h2>Thank you for your order!</h2>
    <p>Your order <b>{order.order_number}</b> has been received.</p>
    <p>Total: <b>${{order.total}}</b></p>
    <p>We'll notify you when your items ship.</p>
    """
    send_email(subject, to_email, html_body)

# Email a cada vendedor
async def notify_vendors_new_order(order: Order):
    vendors = set(item.vendor for item in order.items)
    for vendor in vendors:
        subject = f"New Order Received - {order.order_number}"
        to_email = vendor.contact_email
        html_body = f"""
        <h2>New Order for your store</h2>
        <p>Order <b>{order.order_number}</b> includes items for your store <b>{vendor.store_name}</b>.</p>
        <p>Check your dashboard for details.</p>
        """
        send_email(subject, to_email, html_body)

# Actualizar stats de ventas (dummy)
def update_vendor_sales_stats(order: Order):
    # Aquí podrías actualizar stats, rankings, etc.
    pass

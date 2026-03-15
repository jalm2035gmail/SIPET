from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Numeric, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal
from backend.apps.products.models import Product, ProductVariant
from backend.apps.vendors.models import VendorStore
from backend.apps.users.models import User
from backend.core.db import Base

class Cart(Base):
    __tablename__ = 'cart'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    session_key = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship('User', back_populates='cart')
    items = relationship('CartItem', back_populates='cart', cascade='all, delete-orphan')

    def get_total(self):
        return sum(item.get_total() for item in self.items)

    def get_items_by_vendor(self):
        items_by_vendor = {}
        for item in self.items:
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
        return items_by_vendor

    def clear(self):
        self.items.clear()

class CartItem(Base):
    __tablename__ = 'cart_item'
    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey('cart.id'))
    product_id = Column(Integer, ForeignKey('product.id'))
    variant_id = Column(Integer, ForeignKey('product_variant.id'), nullable=True)
    quantity = Column(Integer, default=1)
    price = Column(Numeric(10, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    cart = relationship('Cart', back_populates='items')
    product = relationship('Product')
    variant = relationship('ProductVariant')

    __table_args__ = (
        # Unique constraint for (cart, product, variant)
    )

    def get_total(self):
        return self.price * self.quantity

    def is_available(self):
        if self.variant:
            return self.variant.stock_quantity >= self.quantity
        return self.product.is_in_stock() and self.product.stock_quantity >= self.quantity

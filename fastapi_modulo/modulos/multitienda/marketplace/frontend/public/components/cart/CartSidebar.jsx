import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import Link from 'next/link';
import Image from 'next/image';
import { 
  ShoppingCart, X, Plus, Minus, Trash2, Package, 
  Truck, CreditCard, AlertCircle 
} from 'lucide-react';

const CartSidebar = ({ isOpen, onClose }) => {
  const [cart, setCart] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState({});
  const router = useRouter();

  useEffect(() => {
    if (isOpen) {
      fetchCart();
    }
  }, [isOpen]);

  const fetchCart = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/cart');
      setCart(response.data.cart);
      setItems(response.data.items);
    } catch (error) {
      console.error('Error fetching cart:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateQuantity = async (itemId, newQuantity) => {
    setUpdating(prev => ({ ...prev, [itemId]: true }));
    try {
      await axios.put(`/api/cart/items/${itemId}`, {
        quantity: newQuantity
      });
      await fetchCart();
    } catch (error) {
      console.error('Error updating quantity:', error);
      alert(error.response?.data?.detail || 'Error updating cart');
    } finally {
      setUpdating(prev => ({ ...prev, [itemId]: false }));
    }
  };

  const removeItem = async (itemId) => {
    if (!confirm('Remove item from cart?')) return;
    try {
      await axios.delete(`/api/cart/items/${itemId}`);
      await fetchCart();
    } catch (error) {
      console.error('Error removing item:', error);
    }
  };

  const proceedToCheckout = () => {
    onClose();
    router.push('/checkout');
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Overlay */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 z-40"
        onClick={onClose}
      />
      {/* Sidebar */}
      <div className="fixed top-0 right-0 h-full w-full md:w-96 bg-white z-50 shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <ShoppingCart className="h-6 w-6" />
            <h2 className="text-xl font-bold">Your Cart</h2>
            {cart && (
              <span className="bg-blue-100 text-blue-800 text-sm px-2 py-1 rounded-full">
                {cart.items_count} items
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        {/* Content */}
        <div className="h-full flex flex-col">
          {/* Items List */}
          <div className="flex-1 overflow-y-auto p-4">
            {loading ? (
              <div className="space-y-4">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="flex gap-3 animate-pulse">
                    <div className="w-20 h-20 bg-gray-200 rounded"></div>
                    <div className="flex-1 space-y-2">
                      <div className="h-4 bg-gray-200 rounded"></div>
                      <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                    </div>
                  </div>
                ))}
              </div>
            ) : items.length === 0 ? (
              <div className="text-center py-12">
                <ShoppingCart className="h-16 w-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">Your cart is empty</h3>
                <p className="text-gray-600 mb-6">Add some products to get started</p>
                <button
                  onClick={onClose}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Continue Shopping
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {items.map(item => (
                  <div key={item.id} className="flex gap-3 p-3 border rounded-lg">
                    {/* Product Image */}
                    <Link 
                      href={`/store/${item.product.vendor.slug}/product/${item.product.slug}`}
                      onClick={onClose}
                      className="flex-shrink-0"
                    >
                      <div className="w-20 h-20 bg-gray-100 rounded overflow-hidden">
                        {item.product.image ? (
                          <Image
                            src={item.product.image}
                            alt={item.product.name}
                            width={80}
                            height={80}
                            className="object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-gray-400">
                            <Package className="h-8 w-8" />
                          </div>
                        )}
                      </div>
                    </Link>
                    {/* Product Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between">
                        <Link
                          href={`/store/${item.product.vendor.slug}/product/${item.product.slug}`}
                          onClick={onClose}
                          className="font-medium hover:text-blue-600 truncate"
                        >
                          {item.product.name}
                        </Link>
                        <button
                          onClick={() => removeItem(item.id)}
                          className="text-gray-400 hover:text-red-500"
                          disabled={updating[item.id]}
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                      <div className="text-sm text-gray-500 mb-2">
                        By {item.product.vendor.name}
                      </div>
                      {item.variant && (
                        <div className="text-sm text-gray-600 mb-2">
                          {Object.entries(item.variant.attributes || {}).map(([key, value]) => (
                            <span key={key} className="mr-2">
                              {key}: {value}
                            </span>
                          ))}
                        </div>
                      )}
                      {/* Quantity Controls */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center border rounded-lg">
                          <button
                            onClick={() => updateQuantity(item.id, item.quantity - 1)}
                            disabled={item.quantity <= 1 || updating[item.id]}
                            className="p-2 hover:bg-gray-100 disabled:opacity-50"
                          >
                            <Minus className="h-3 w-3" />
                          </button>
                          <span className="px-3 py-1">{item.quantity}</span>
                          <button
                            onClick={() => updateQuantity(item.id, item.quantity + 1)}
                            disabled={updating[item.id]}
                            className="p-2 hover:bg-gray-100 disabled:opacity-50"
                          >
                            <Plus className="h-3 w-3" />
                          </button>
                        </div>
                        <div className="font-bold">
                          ${item.total.toFixed(2)}
                        </div>
                      </div>
                      {/* Stock Warning */}
                      {!item.is_available && (
                        <div className="mt-2 flex items-center gap-1 text-sm text-amber-600">
                          <AlertCircle className="h-4 w-4" />
                          Out of stock
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          {/* Summary & Checkout */}
          {cart && items.length > 0 && (
            <div className="border-t p-4 bg-gray-50">
              {/* Totals */}
              <div className="space-y-2 mb-4">
                <div className="flex justify-between">
                  <span className="text-gray-600">Subtotal</span>
                  <span className="font-semibold">${cart.subtotal.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Shipping</span>
                  <span className="font-semibold">${cart.shipping_total.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-lg font-bold border-t pt-2">
                  <span>Total</span>
                  <span>${cart.total.toFixed(2)}</span>
                </div>
              </div>
              {/* Checkout Button */}
              <button
                onClick={proceedToCheckout}
                className="w-full py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center justify-center gap-2 font-semibold"
              >
                <CreditCard className="h-5 w-5" />
                Proceed to Checkout
              </button>
              {/* Continue Shopping */}
              <button
                onClick={onClose}
                className="w-full mt-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Continue Shopping
              </button>
              {/* Trust Badges */}
              <div className="mt-4 pt-4 border-t border-gray-200">
                <div className="flex justify-center gap-4 text-gray-400">
                  <div className="text-center">
                    <Truck className="h-6 w-6 mx-auto mb-1" />
                    <div className="text-xs">Free Shipping</div>
                  </div>
                  <div className="text-center">
                    <Package className="h-6 w-6 mx-auto mb-1" />
                    <div className="text-xs">Easy Returns</div>
                  </div>
                  <div className="text-center">
                    <CreditCard className="h-6 w-6 mx-auto mb-1" />
                    <div className="text-xs">Secure Payment</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
};

// Componente para el ícono del carrito en el header
export const CartIcon = ({ onClick, itemCount = 0 }) => {
  return (
    <button
      onClick={onClick}
      className="relative p-2 hover:bg-gray-100 rounded-full"
    >
      <ShoppingCart className="h-6 w-6" />
      {itemCount > 0 && (
        <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
          {itemCount > 99 ? '99+' : itemCount}
        </span>
      )}
    </button>
  );
};

export default CartSidebar;

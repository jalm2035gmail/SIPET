import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import { loadStripe } from '@stripe/stripe-js';
import {
  CreditCard,
  Truck,
  User,
  MapPin,
  Shield,
  AlertCircle,
  CheckCircle
} from 'lucide-react';

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLIC_KEY);

const CheckoutPage = () => {
  const router = useRouter();
  const [step, setStep] = useState(1); // 1: Shipping, 2: Payment, 3: Review
  const [cart, setCart] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [errors, setErrors] = useState({});
  // Form data
  const [formData, setFormData] = useState({
    email: '',
    shippingAddress: {
      firstName: '',
      lastName: '',
      address: '',
      apartment: '',
      city: '',
      country: 'US',
      state: '',
      zipCode: '',
      phone: ''
    },
    billingAddress: {
      sameAsShipping: true,
      firstName: '',
      lastName: '',
      address: '',
      city: '',
      country: 'US',
      state: '',
      zipCode: ''
    },
    shippingMethods: {},
    paymentMethod: 'card'
  });

  useEffect(() => {
    fetchCart();
  }, []);

  const fetchCart = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/cart');
      if (response.data.cart.items_count === 0) {
        router.push('/');
        return;
      }
      setCart(response.data.cart);
      setItems(response.data.items);
    } catch (error) {
      console.error('Error fetching cart:', error);
    } finally {
      setLoading(false);
    }
  };

  const validateStep = (step) => {
    const newErrors = {};
    if (step === 1) {
      if (!formData.email) newErrors.email = 'Email is required';
      if (!formData.shippingAddress.firstName) newErrors['shippingAddress.firstName'] = 'First name is required';
      if (!formData.shippingAddress.lastName) newErrors['shippingAddress.lastName'] = 'Last name is required';
      if (!formData.shippingAddress.address) newErrors['shippingAddress.address'] = 'Address is required';
      if (!formData.shippingAddress.city) newErrors['shippingAddress.city'] = 'City is required';
      if (!formData.shippingAddress.country) newErrors['shippingAddress.country'] = 'Country is required';
      if (!formData.shippingAddress.zipCode) newErrors['shippingAddress.zipCode'] = 'ZIP code is required';
      if (!formData.shippingAddress.phone) newErrors['shippingAddress.phone'] = 'Phone is required';
    }
    if (step === 2) {
      if (!formData.paymentMethod) newErrors.paymentMethod = 'Payment method is required';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNextStep = () => {
    if (validateStep(step)) {
      if (step === 1) {
        calculateShipping();
      }
      setStep(step + 1);
    }
  };

  const handlePrevStep = () => {
    setStep(step - 1);
  };

  const calculateShipping = async () => {
    try {
      const response = await axios.post('/api/checkout/shipping-methods', {
        address: formData.shippingAddress
      });
      const defaultMethods = {};
      response.data.forEach(vendor => {
        if (vendor.methods.length > 0) {
          defaultMethods[vendor.vendor.id] = vendor.methods[0].id;
        }
      });
      setFormData(prev => ({
        ...prev,
        shippingMethods: defaultMethods
      }));
    } catch (error) {
      console.error('Error calculating shipping:', error);
    }
  };

  const handleSubmitOrder = async () => {
    setProcessing(true);
    try {
      const paymentResponse = await axios.post('/api/checkout/create-payment-intent', {
        email: formData.email,
        shipping_address: formData.shippingAddress,
        billing_address: formData.billingAddress.sameAsShipping 
          ? formData.shippingAddress 
          : formData.billingAddress,
        shipping_methods: formData.shippingMethods,
        customer_note: formData.customerNote
      });
      const stripe = await stripePromise;
      // Aquí deberías montar Stripe Elements y obtener el elemento de tarjeta
      // const { error } = await stripe.confirmCardPayment(...)
      // Simulación:
      // if (error) throw new Error(error.message);
      const orderResponse = await axios.post('/api/checkout/create-order', {
        payment_intent_id: paymentResponse.data.payment_intent_id,
        email: formData.email,
        payment_method: formData.paymentMethod
      });
      router.push(`/checkout/confirmation/${orderResponse.data.order_number}`);
    } catch (error) {
      console.error('Error processing order:', error);
      setErrors({ submit: error.message });
    } finally {
      setProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-16">
        <div className="text-center">Loading checkout...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2">Checkout</h1>
          <p className="text-gray-600">Complete your purchase</p>
        </div>
        <div className="max-w-6xl mx-auto">
          {/* Progress Steps */}
          <div className="flex justify-center mb-8">
            <div className="flex items-center">
              {[1, 2, 3].map((stepNum) => (
                <div key={stepNum} className="flex items-center">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    step >= stepNum 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-gray-200 text-gray-600'
                  }`}>
                    {step > stepNum ? <CheckCircle className="h-5 w-5" /> : stepNum}
                  </div>
                  {stepNum < 3 && (
                    <div className={`w-24 h-1 ${
                      step > stepNum ? 'bg-blue-600' : 'bg-gray-200'
                    }`} />
                  )}
                </div>
              ))}
            </div>
          </div>
          <div className="flex flex-col lg:flex-row gap-8">
            {/* Left Column - Forms */}
            <div className="lg:w-2/3">
              {/* ...existing code for steps... */}
            </div>
            {/* Right Column - Order Summary */}
            <div className="lg:w-1/3">
              <div className="bg-white rounded-lg shadow p-6 sticky top-8">
                <h2 className="text-xl font-bold mb-6">Order Summary</h2>
                {/* Items */}
                <div className="space-y-4 mb-6">
                  {items.map(item => (
                    <div key={item.id} className="flex gap-3">
                      <div className="w-16 h-16 bg-gray-100 rounded overflow-hidden flex-shrink-0">
                        {item.product.image && (
                          <img
                            src={item.product.image}
                            alt={item.product.name}
                            className="w-full h-full object-cover"
                          />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium truncate">
                          {item.product.name}
                        </div>
                        <div className="text-sm text-gray-500">
                          Qty: {item.quantity}
                        </div>
                        <div className="font-semibold">
                          ${item.total.toFixed(2)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                {/* Totals */}
                <div className="border-t pt-4 space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Subtotal</span>
                    <span>${cart?.subtotal?.toFixed(2) || '0.00'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Shipping</span>
                    <span>${cart?.shipping_total?.toFixed(2) || '0.00'}</span>
                  </div>
                  <div className="flex justify-between font-bold text-lg border-t pt-2">
                    <span>Total</span>
                    <span>${cart?.total?.toFixed(2) || '0.00'}</span>
                  </div>
                </div>
                {/* Security Badge */}
                <div className="mt-6 pt-6 border-t">
                  <div className="flex items-center gap-2 text-green-600">
                    <Shield className="h-5 w-5" />
                    <span className="text-sm font-medium">
                      Secure SSL Encryption
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CheckoutPage;

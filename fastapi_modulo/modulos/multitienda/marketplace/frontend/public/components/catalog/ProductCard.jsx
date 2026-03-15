import Link from 'next/link';
import Image from 'next/image';
import { Star, ShoppingCart, Eye } from 'lucide-react';
import { useState } from 'react';

const ProductCard = ({ product, viewMode = 'grid', vendorSlug }) => {
  const [isHovered, setIsHovered] = useState(false);
  
  const primaryImage = product.images?.find(img => img.is_primary) || product.images?.[0];
  
  const addToCart = () => {
    // Lógica para añadir al carrito
    console.log('Add to cart:', product.id);
  };
  
  const quickView = () => {
    // Lógica para vista rápida
    console.log('Quick view:', product.id);
  };

  if (viewMode === 'list') {
    return (
      <div className="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow">
        <div className="flex gap-4">
          {/* Image */}
          <div className="w-32 h-32 flex-shrink-0">
            <Link href={`/store/${vendorSlug}/product/${product.slug}`}>
              <div className="relative w-full h-full bg-gray-100 rounded-lg overflow-hidden">
                {primaryImage ? (
                  <Image
                    src={primaryImage.image_url}
                    alt={product.name}
                    fill
                    className="object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-gray-400">
                    No Image
                  </div>
                )}
              </div>
            </Link>
          </div>
          
          {/* Product Info */}
          <div className="flex-1">
            <div className="flex justify-between">
              <div>
                <Link href={`/store/${vendorSlug}/product/${product.slug}`}>
                  <h3 className="font-semibold text-lg hover:text-blue-600">
                    {product.name}
                  </h3>
                </Link>
                <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                  {product.short_description}
                </p>
              </div>
              
              <div className="text-right">
                <div className="text-2xl font-bold">${product.price}</div>
                {product.compare_price && (
                  <div className="text-sm text-gray-500 line-through">
                    ${product.compare_price}
                  </div>
                )}
              </div>
            </div>
            
            <div className="flex items-center justify-between mt-4">
              <div className="flex items-center gap-4">
                {/* Vendor */}
                <Link 
                  href={`/store/${vendorSlug}`}
                  className="text-sm text-gray-600 hover:text-blue-600"
                >
                  By {product.vendor?.store_name}
                </Link>
                
                {/* Rating */}
                <div className="flex items-center gap-1">
                  <Star className="h-4 w-4 text-yellow-400 fill-current" />
                  <span className="text-sm">{product.avg_rating || 0}</span>
                  <span className="text-sm text-gray-500">
                    ({product.review_count || 0})
                  </span>
                </div>
                
                {/* Stock Status */}
                <div className={`text-sm px-2 py-1 rounded ${
                  product.stock_quantity > 0 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-red-100 text-red-800'
                }`}>
                  {product.stock_quantity > 0 ? 'In Stock' : 'Out of Stock'}
                </div>
              </div>
              
              <div className="flex gap-2">
                <button
                  onClick={quickView}
                  className="p-2 border rounded-lg hover:bg-gray-50"
                  title="Quick View"
                >
                  <Eye className="h-5 w-5" />
                </button>
                <button
                  onClick={addToCart}
                  disabled={product.stock_quantity === 0}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Add to Cart
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Grid View (default)
  return (
    <div 
      className="bg-white rounded-lg shadow overflow-hidden hover:shadow-lg transition-shadow"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Image Container */}
      <Link href={`/store/${vendorSlug}/product/${product.slug}`}>
        <div className="relative aspect-square bg-gray-100 overflow-hidden">
          {primaryImage ? (
            <Image
              src={primaryImage.image_url}
              alt={product.name}
              fill
              className={`object-cover transition-transform duration-300 ${
                isHovered ? 'scale-105' : ''
              }`}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-gray-400">
              No Image
            </div>
          )}
          
          {/* Discount Badge */}
          {product.compare_price && product.compare_price > product.price && (
            <div className="absolute top-2 left-2 bg-red-500 text-white text-xs font-bold px-2 py-1 rounded">
              -{Math.round((1 - product.price / product.compare_price) * 100)}%
            </div>
          )}
          
          {/* Stock Badge */}
          <div className="absolute top-2 right-2">
            <span className={`text-xs px-2 py-1 rounded ${
              product.stock_quantity > 0 
                ? 'bg-green-500 text-white' 
                : 'bg-red-500 text-white'
            }`}>
              {product.stock_quantity > 0 ? 'In Stock' : 'Out of Stock'}
            </span>
          </div>
          
          {/* Quick Actions on Hover */}
          {isHovered && (
            <div className="absolute inset-0 bg-black bg-opacity-20 flex items-center justify-center gap-2">
              <button
                onClick={(e) => {
                  e.preventDefault();
                  quickView();
                }}
                className="p-3 bg-white rounded-full shadow-lg hover:shadow-xl"
                title="Quick View"
              >
                <Eye className="h-5 w-5" />
              </button>
              <button
                onClick={(e) => {
                  e.preventDefault();
                  addToCart();
                }}
                disabled={product.stock_quantity === 0}
                className="p-3 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 hover:shadow-xl disabled:opacity-50"
                title="Add to Cart"
              >
                <ShoppingCart className="h-5 w-5" />
              </button>
            </div>
          )}
        </div>
      </Link>
      
      {/* Product Info */}
      <div className="p-4">
        {/* Vendor */}
        <Link 
          href={`/store/${vendorSlug}`}
          className="text-xs text-gray-500 hover:text-blue-600 block mb-1"
        >
          {product.vendor?.store_name}
        </Link>
        
        {/* Product Name */}
        <Link href={`/store/${vendorSlug}/product/${product.slug}`}>
          <h3 className="font-semibold hover:text-blue-600 line-clamp-1">
            {product.name}
          </h3>
        </Link>
        
        {/* Rating */}
        <div className="flex items-center gap-1 my-2">
          <div className="flex">
            {[...Array(5)].map((_, i) => (
              <Star
                key={i}
                className={`h-3 w-3 ${
                  i < Math.floor(product.avg_rating || 0)
                    ? 'text-yellow-400 fill-current'
                    : 'text-gray-300'
                }`}
              />
            ))}
          </div>
          <span className="text-xs text-gray-500">
            ({product.review_count || 0})
          </span>
        </div>
        
        {/* Price */}
        <div className="flex items-center gap-2">
          <span className="text-xl font-bold">${product.price}</span>
          {product.compare_price && (
            <span className="text-sm text-gray-500 line-through">
              ${product.compare_price}
            </span>
          )}
        </div>
        
        {/* Add to Cart Button */}
        <button
          onClick={addToCart}
          disabled={product.stock_quantity === 0}
          className="w-full mt-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {product.stock_quantity === 0 ? 'Out of Stock' : 'Add to Cart'}
        </button>
      </div>
    </div>
  );
};

export default ProductCard;

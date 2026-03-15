import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import axios from 'axios';

const FiltersSidebar = ({ filters, onFilterChange, onClearFilters, isMobile = false }) => {
  const [categories, setCategories] = useState([]);
  const [priceRange, setPriceRange] = useState({ min: 0, max: 1000 });
  const [expandedSections, setExpandedSections] = useState({
    categories: true,
    price: true,
    stock: true
  });

  useEffect(() => {
    fetchFiltersData();
  }, []);

  const fetchFiltersData = async () => {
    try {
      const response = await axios.get('/api/catalog/filters');
      setCategories(response.data.categories);
      setPriceRange(response.data.price_range);
    } catch (error) {
      console.error('Error fetching filters:', error);
    }
  };

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const handlePriceChange = (type, value) => {
    const numValue = parseFloat(value) || '';
    onFilterChange(type === 'min' ? 'minPrice' : 'maxPrice', numValue);
  };

  const FilterSection = ({ title, sectionKey, children }) => (
    <div className="border-b pb-4 mb-4">
      <button
        onClick={() => toggleSection(sectionKey)}
        className="flex justify-between items-center w-full text-left font-semibold mb-2"
      >
        <span>{title}</span>
        {expandedSections[sectionKey] ? (
          <ChevronUp className="h-4 w-4" />
        ) : (
          <ChevronDown className="h-4 w-4" />
        )}
      </button>
      
      {expandedSections[sectionKey] && children}
    </div>
  );

  return (
    <div className={isMobile ? '' : 'bg-white rounded-lg shadow p-4'}>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-bold">Filters</h2>
        <button
          onClick={onClearFilters}
          className="text-sm text-red-600 hover:text-red-800"
        >
          Clear All
        </button>
      </div>

      {/* Categories */}
      <FilterSection title="Categories" sectionKey="categories">
        <div className="space-y-2 max-h-60 overflow-y-auto">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="category"
              value=""
              checked={!filters.category}
              onChange={() => onFilterChange('category', '')}
              className="rounded"
            />
            <span className="text-sm">All Categories</span>
          </label>
          
          {categories.map(category => (
            <label key={category.id} className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="category"
                value={category.slug}
                checked={filters.category === category.slug}
                onChange={(e) => onFilterChange('category', e.target.value)}
                className="rounded"
              />
              <span className="text-sm">
                {category.name} ({category.product_count})
              </span>
            </label>
          ))}
        </div>
      </FilterSection>

      {/* Price Range */}
      <FilterSection title="Price Range" sectionKey="price">
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <span className="text-sm">Min:</span>
            <input
              type="number"
              min="0"
              step="0.01"
              value={filters.minPrice || ''}
              onChange={(e) => handlePriceChange('min', e.target.value)}
              className="w-24 p-1 border rounded text-sm"
              placeholder="Min"
            />
            <span className="text-sm">Max:</span>
            <input
              type="number"
              min="0"
              step="0.01"
              value={filters.maxPrice || ''}
              onChange={(e) => handlePriceChange('max', e.target.value)}
              className="w-24 p-1 border rounded text-sm"
              placeholder="Max"
            />
          </div>
          
          {/* Price Slider (simplificado) */}
          <div className="px-2">
            <input
              type="range"
              min={priceRange.min}
              max={priceRange.max}
              value={filters.maxPrice || priceRange.max}
              onChange={(e) => onFilterChange('maxPrice', e.target.value)}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>${priceRange.min}</span>
              <span>${filters.maxPrice || priceRange.max}</span>
            </div>
          </div>
        </div>
      </FilterSection>

      {/* Stock Status */}
      <FilterSection title="Stock Status" sectionKey="stock">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={filters.inStock}
            onChange={(e) => onFilterChange('inStock', e.target.checked)}
            className="rounded"
          />
          <span className="text-sm">In Stock Only</span>
        </label>
      </FilterSection>

      {/* Vendor Rating */}
      <FilterSection title="Vendor Rating" sectionKey="rating">
        <div className="space-y-2">
          {[5, 4, 3, 2, 1].map(rating => (
            <label key={rating} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                className="rounded"
                // Implementar lógica de rating
              />
              <div className="flex">
                {[...Array(5)].map((_, i) => (
                  <span key={i} className={`text-sm ${
                    i < rating ? 'text-yellow-400' : 'text-gray-300'
                  }`}>
                    ★
                  </span>
                ))}
              </div>
              <span className="text-sm text-gray-500">& up</span>
            </label>
          ))}
        </div>
      </FilterSection>

      {/* Apply Filters Button (Mobile) */}
      {isMobile && (
        <button
          onClick={() => {/* Close modal logic */}}
          className="w-full mt-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Apply Filters
        </button>
      )}
    </div>
  );
};

export default FiltersSidebar;

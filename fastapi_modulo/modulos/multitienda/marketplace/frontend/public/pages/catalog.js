import { useState, useEffect, useRef } from 'react';
import Head from 'next/head';
import FiltersSidebar from '../components/catalog/FiltersSidebar';
import ProductCard from '../components/catalog/ProductCard';
import axios from 'axios';

const initialFilters = {
  category: '',
  minPrice: '',
  maxPrice: '',
  inStock: false,
  // rating: [], // Puedes agregar lógica para rating si lo implementas
};


const CatalogPage = () => {
  const [filters, setFilters] = useState(initialFilters);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState('grid');
  // Paginación
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(12);
  const [totalPages, setTotalPages] = useState(1);
  // Responsive sidebar
  const [sidebarOpen, setSidebarOpen] = useState(false);
  // Búsqueda
  const [search, setSearch] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const searchTimeout = useRef(null);
  const searchBoxRef = useRef(null);

  useEffect(() => {
    fetchProducts();
  }, [filters, search, page, pageSize]);

  const fetchProducts = async () => {
    setLoading(true);
    try {
      const params = {
        category: filters.category,
        min_price: filters.minPrice,
        max_price: filters.maxPrice,
        in_stock: filters.inStock,
        search,
        page,
        limit: pageSize,
        // rating: filters.rating, // Si implementas rating
      };
      const response = await axios.get('/api/catalog/products', { params });
      setProducts(response.data.products);
      setTotalPages(response.data.total_pages || 1);
    } catch (error) {
      console.error('Error fetching products:', error);
    } finally {
      setLoading(false);
    }
  };

  // Sugerencias en tiempo real (productos y vendors)
  const fetchSuggestions = async (q) => {
    if (!q) {
      setSuggestions([]);
      return;
    }
    try {
      const resp = await axios.get('/api/catalog/suggest', { params: { q } });
      setSuggestions(resp.data.suggestions || []);
    } catch (err) {
      setSuggestions([]);
    }
  };

  const handleSearchChange = (e) => {
    const value = e.target.value;
    setSearch(value);
    setShowSuggestions(true);
    if (searchTimeout.current) clearTimeout(searchTimeout.current);
    searchTimeout.current = setTimeout(() => {
      fetchSuggestions(value);
    }, 250);
  };

  const handleSuggestionClick = (s) => {
    setSearch(s.label);
    setShowSuggestions(false);
    setFilters(prev => ({ ...prev, category: '', minPrice: '', maxPrice: '', inStock: false }));
    // Opcional: podrías filtrar por vendor/producto según tipo
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPage(1); // Resetear a la primera página al cambiar filtros
  };

  const handleClearFilters = () => {
    setFilters(initialFilters);
    setPage(1);
  };

  // Cerrar sugerencias al hacer click fuera
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchBoxRef.current && !searchBoxRef.current.contains(event.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // SEO dinámico
  const pageTitle = search
    ? `Search results for "${search}" | Catalog`
    : 'Product Catalog | Marketplace';
  const pageDescription = search
    ? `Find products and vendors matching "${search}" in our marketplace.`
    : 'Browse the best products from multiple vendors in our marketplace.';
  const canonicalUrl = typeof window !== 'undefined' ? window.location.href : '';

  return (
    <>
      <Head>
        <title>{pageTitle}</title>
        <meta name="description" content={pageDescription} />
        <link rel="canonical" href={canonicalUrl} />
        <meta property="og:title" content={pageTitle} />
        <meta property="og:description" content={pageDescription} />
        <meta property="og:type" content="website" />
        <meta property="og:url" content={canonicalUrl} />
      </Head>
      <div className="flex flex-col md:flex-row gap-4 md:gap-8 px-2 md:px-0">
        {/* Sidebar (desktop) */}
        <div className="hidden md:block w-72 flex-shrink-0">
          <FiltersSidebar
            filters={filters}
            onFilterChange={handleFilterChange}
            onClearFilters={handleClearFilters}
          />
        </div>
        {/* Sidebar (mobile) */}
        <div className="md:hidden mb-2">
          <button
            className="w-full py-2 bg-blue-600 text-white rounded-lg font-semibold mb-2"
            onClick={() => setSidebarOpen(o => !o)}
          >
            {sidebarOpen ? 'Hide Filters' : 'Show Filters'}
          </button>
          {sidebarOpen && (
            <div className="bg-white rounded-lg shadow p-4 mb-2">
              <FiltersSidebar
                filters={filters}
                onFilterChange={handleFilterChange}
                onClearFilters={handleClearFilters}
                isMobile={true}
              />
            </div>
          )}
        </div>
        {/* Main Content */}
        <div className="flex-1 min-w-0">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center mb-4 gap-4">
            <h1 className="text-2xl font-bold">Product Catalog</h1>
            {/* Barra de búsqueda */}
            <div className="relative w-full sm:w-96" ref={searchBoxRef}>
              <input
                type="text"
                className="w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring"
                placeholder="Search products or vendors..."
                value={search}
                onChange={handleSearchChange}
                onFocus={() => setShowSuggestions(true)}
              />
              {showSuggestions && suggestions.length > 0 && (
                <div className="absolute z-10 left-0 right-0 bg-white border rounded-lg shadow mt-1 max-h-60 overflow-y-auto">
                  {suggestions.map((s, idx) => (
                    <div
                      key={idx}
                      className="px-4 py-2 hover:bg-blue-50 cursor-pointer flex items-center gap-2"
                      onClick={() => handleSuggestionClick(s)}
                    >
                      <span className="font-medium">{s.label}</span>
                      <span className="text-xs text-gray-500">{s.type === 'vendor' ? 'Vendor' : 'Product'}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="flex gap-2">
              <button
                className={`px-3 py-1 rounded ${viewMode === 'grid' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
                onClick={() => setViewMode('grid')}
              >
                Grid
              </button>
              <button
                className={`px-3 py-1 rounded ${viewMode === 'list' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
                onClick={() => setViewMode('list')}
              >
                List
              </button>
            </div>
          </div>
          {loading ? (
            <div className="text-center py-12 text-gray-500">Loading products...</div>
          ) : products.length === 0 ? (
            <div className="text-center py-12 text-gray-500">No products found.</div>
          ) : (
            <>
              <div className={viewMode === 'grid' ? 'grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6' : 'space-y-4'}>
                {products.map(product => (
                  <ProductCard
                    key={product.id}
                    product={product}
                    viewMode={viewMode}
                    vendorSlug={product.vendor?.slug || 'vendor'}
                  />
                ))}
              </div>
              {/* Controles de paginación */}
              <div className="flex flex-col sm:flex-row items-center justify-between mt-8 gap-4">
                <div className="flex gap-2 items-center">
                  <button
                    className="px-3 py-1 rounded border disabled:opacity-50"
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    Previous
                  </button>
                  <span className="text-sm">Page {page} of {totalPages}</span>
                  <button
                    className="px-3 py-1 rounded border disabled:opacity-50"
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                  >
                    Next
                  </button>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm">Products per page:</span>
                  <select
                    className="border rounded px-2 py-1 text-sm"
                    value={pageSize}
                    onChange={e => { setPageSize(Number(e.target.value)); setPage(1); }}
                  >
                    {[6, 12, 24, 48].map(size => (
                      <option key={size} value={size}>{size}</option>
                    ))}
                  </select>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
      </div>
    </>
};

export default CatalogPage;

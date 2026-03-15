# Frontend MultiTiendApp

### Estructura recomendada
- `public/`: aplicación Next.js que sirve las tiendas públicas (`/storeSlug`).
- `vendor-admin/`: dashboard moderno para vendedores (React/Vue) con gestión de inventario y pedidos.
- `super-admin/`: panel de control global que revisa comisiones, tiendas y métricas.

### Pasos siguientes
1. Crear proyecto Next.js dentro de `public/` y configurar rutas dinámicas por tienda.
2. Añadir autenticación con OAuth/JWT para vendedores y clientes.
3. Centrarse en componentes compartidos (botones, tarjetas de productos, modales de checkout).
4. Usar `vendor-admin/` y `super-admin/` para páginas SPA independientes que consumen la API Django.

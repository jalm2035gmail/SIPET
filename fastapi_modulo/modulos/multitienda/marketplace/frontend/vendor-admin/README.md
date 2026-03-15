# Panel de Vendedores

Servicios esperados:
- Autenticación JWT y autorización de vendedores.
- Gestión de catálogo, inventario, pedidos y envíos.
- Dashboard de métricas (ventas, comisiones, mensajes).
- Comunicación con APIs del backend (`/api/v1/vendors`, `/api/v1/orders`).

Esquema sugerido:
```
vendor-admin/
├── src/
│   ├── components/
│   ├── hooks/
│   ├── routes/
│   └── services/api.js
└── package.json
```

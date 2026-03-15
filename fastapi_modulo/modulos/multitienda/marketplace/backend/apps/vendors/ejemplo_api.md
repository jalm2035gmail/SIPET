# Ejemplo de uso de endpoints VendorStore (FastAPI)

# 1. Registrar usuario vendedor
POST /users/register
{
  "username": "vendedor1",
  "email": "vendedor1@email.com",
  "password": "123456",
  "user_type": "vendor"
}

# 2. Login para obtener token
POST /users/login
Content-Type: application/x-www-form-urlencoded
username=vendedor1&password=123456

# Respuesta:
{
  "access_token": "<TOKEN>",
  "token_type": "bearer"
}

# 3. Crear tienda (con token de vendedor)
POST /vendors/
Authorization: Bearer <TOKEN>
{
  "store_name": "Tienda de Juan",
  "store_slug": "tienda-juan",
  "store_theme": {"color": "blue"},
  "commission_rate": 10.0,
  "is_active": true
}

# 4. Consultar tienda propia
GET /vendors/me
Authorization: Bearer <TOKEN>

# 5. Listar todas las tiendas (público)
GET /vendors/

# 6. Buscar tienda por slug (público)
GET /vendors/slug/tienda-juan

# 7. Actualizar tienda propia
PUT /vendors/me
Authorization: Bearer <TOKEN>
{
  "store_name": "Tienda de Juan Actualizada",
  "commission_rate": 12.5
}

# 8. Eliminar tienda propia
DELETE /vendors/me
Authorization: Bearer <TOKEN>

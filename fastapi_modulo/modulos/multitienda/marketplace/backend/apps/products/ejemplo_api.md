# Ejemplo de uso de endpoints Productos (FastAPI)

# 1. Registrar usuario vendedor (si no existe)
POST /users/register
{
  "username": "vendedor2",
  "email": "vendedor2@email.com",
  "password": "123456",
  "user_type": "vendor"
}

# 2. Login para obtener token
POST /users/login
Content-Type: application/x-www-form-urlencoded
username=vendedor2&password=123456

# Respuesta:
{
  "access_token": "<TOKEN>",
  "token_type": "bearer"
}

# 3. Crear producto (con token de vendedor)
POST /products/
Authorization: Bearer <TOKEN>
{
  "name": "Producto 1",
  "description": "Descripción del producto",
  "price": 100.0,
  "stock": 10
}

# 4. Listar productos propios (vendedor)
GET /products/mine
Authorization: Bearer <TOKEN>

# 5. Listar todos los productos (público)
GET /products/

# 6. Consultar producto por id
GET /products/1

# 7. Actualizar producto propio
PUT /products/1
Authorization: Bearer <TOKEN>
{
  "name": "Producto 1 actualizado",
  "price": 120.0
}

# 8. Eliminar producto propio
DELETE /products/1
Authorization: Bearer <TOKEN>

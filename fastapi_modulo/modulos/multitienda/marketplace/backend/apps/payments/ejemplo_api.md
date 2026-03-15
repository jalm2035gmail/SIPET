# Ejemplo de uso de endpoints VendorPayout (FastAPI)

# 1. Crear payout (admin o sistema)
POST /payments/
{
  "vendor_id": 1,
  "order_id": 10,
  "vendor_amount": 500.00,
  "platform_commission": 50.00,
  "status": "pending"
}

# 2. Listar todos los payouts (admin)
GET /payments/

# 3. Listar payouts de un vendedor
GET /payments/vendor/1

# 4. Consultar payout por id
GET /payments/1

# 5. Actualizar estado de payout (admin)
PUT /payments/1
{
  "status": "paid"
}

# 6. Eliminar payout (admin)
DELETE /payments/1

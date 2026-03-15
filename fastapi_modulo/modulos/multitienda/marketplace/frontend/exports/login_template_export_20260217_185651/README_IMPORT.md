# Importar template de login en otra app

## 1) Copiar archivos
Copia `pages/login.js`, `styles/login.module.css` y `static/imagenes/` al proyecto destino respetando la estructura.

## 2) Dependencias y variable de entorno
- Debes tener `axios` instalado.
- Define `NEXT_PUBLIC_API_BASE_URL` (si no existe, usa `http://127.0.0.1:8000`).

## 3) Contrato esperado del backend
El login hace `POST` a:
- `${NEXT_PUBLIC_API_BASE_URL}/avan/users/login`

Formato enviado:
- `application/x-www-form-urlencoded`
- campos: `username`, `password`

Respuesta esperada:
- `access_token`
- `token_type` (opcional)

## 4) Resultado en frontend
Si login es correcto, guarda en `localStorage`:
- `access_token`
- `token_type`

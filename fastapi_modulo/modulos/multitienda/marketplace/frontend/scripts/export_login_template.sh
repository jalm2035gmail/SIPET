#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/marketplace/frontend"
PUBLIC_APP_DIR="$FRONTEND_DIR/public"
STATIC_DIR="$ROOT_DIR/static"

STAMP="$(date +%Y%m%d_%H%M%S)"
PKG_NAME="login_template_export_${STAMP}"
BUILD_DIR="$FRONTEND_DIR/exports/$PKG_NAME"

mkdir -p "$BUILD_DIR/pages" "$BUILD_DIR/styles" "$BUILD_DIR/static/imagenes"

cp "$PUBLIC_APP_DIR/pages/login.js" "$BUILD_DIR/pages/login.js"
cp "$PUBLIC_APP_DIR/styles/login.module.css" "$BUILD_DIR/styles/login.module.css"
cp "$STATIC_DIR/imagenes/login.png" "$BUILD_DIR/static/imagenes/login.png"
cp "$STATIC_DIR/imagenes/tu-negocio.png" "$BUILD_DIR/static/imagenes/tu-negocio.png"

cat > "$BUILD_DIR/README_IMPORT.md" <<'DOC'
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
DOC

(
  cd "$FRONTEND_DIR/exports"
  zip -rq "${PKG_NAME}.zip" "$PKG_NAME"
)

echo "Export listo: $FRONTEND_DIR/exports/${PKG_NAME}.zip"

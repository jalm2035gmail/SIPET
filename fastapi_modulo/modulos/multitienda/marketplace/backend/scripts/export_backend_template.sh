#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/marketplace/backend"
STATIC_DIR="$ROOT_DIR/static"

STAMP="$(date +%Y%m%d_%H%M%S)"
PKG_NAME="backend_template_export_${STAMP}"
BUILD_DIR="$BACKEND_DIR/exports/$PKG_NAME"

mkdir -p "$BUILD_DIR/templates" "$BUILD_DIR/static/js" "$BUILD_DIR/static/icons" "$BUILD_DIR/static/imagenes"

cp "$BACKEND_DIR/templates/base.html" "$BUILD_DIR/templates/base.html"
cp "$BACKEND_DIR/templates/backend_template.html" "$BUILD_DIR/templates/backend_template.html"

cp "$STATIC_DIR/js/backend-navbar.js" "$BUILD_DIR/static/js/backend-navbar.js"
cp "$STATIC_DIR/js/backend-sidebar-core.js" "$BUILD_DIR/static/js/backend-sidebar-core.js"
cp "$STATIC_DIR/js/sidebar-theme-editor.js" "$BUILD_DIR/static/js/sidebar-theme-editor.js"

cp "$STATIC_DIR/icons/configuracion.svg" "$BUILD_DIR/static/icons/configuracion.svg"
cp "$STATIC_DIR/icons/personalizar.svg" "$BUILD_DIR/static/icons/personalizar.svg"
cp "$STATIC_DIR/imagenes/tu-negocio.png" "$BUILD_DIR/static/imagenes/tu-negocio.png"

cat > "$BUILD_DIR/README_IMPORT.md" <<'DOC'
# Importar template backend en otro modulo

## 1) Copiar archivos
Copia `templates/` y `static/` al modulo destino respetando la estructura.

## 2) Contexto minimo para renderizar `backend_template.html`
Debes enviar estas variables al template:
- `blank_path`
- `add_user_path`
- `config_path`
- `template_path`
- `template_frontend_path`

Opcionales:
- `title`
- `page_heading`
- `page_subtitle`
- `is_config_shell` (`True` para vista de configuracion)

## 3) Ejemplo FastAPI
```python
return templates.TemplateResponse(
    request=request,
    name="backend_template.html",
    context={
        "title": "Template Backend",
        "blank_path": "/gestion",
        "add_user_path": "/agregar-usuario",
        "config_path": "/configuracion",
        "template_path": "/template",
        "template_frontend_path": "/template-frontend",
    },
)
```
DOC

(
  cd "$BACKEND_DIR/exports"
  zip -rq "${PKG_NAME}.zip" "$PKG_NAME"
)

echo "Export listo: $BACKEND_DIR/exports/${PKG_NAME}.zip"

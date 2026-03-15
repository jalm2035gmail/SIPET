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

## 4) Variables de entorno recomendadas
- `DJANGO_MAIN_URL` (ej: `http://localhost:8010`)
- `FASTAPI_MAIN_URL` (ej: `http://localhost:8001`)
- `FRONTEND_MAIN_URL` (ej: `http://localhost:3010`)

Rutas sugeridas en este proyecto:
- Template backend: `/admin/template-backend`
- Shell de configuración: `/admin/template-backend/config`

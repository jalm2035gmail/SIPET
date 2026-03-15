# MultiTiendApp

Esqueleto inicial para una plataforma multitienda con roles de superadmin, vendedores y clientes. Esta carpeta ordena la arquitectura propuesta:

```
marketplace/
├── backend/      # Django/FastAPI para APIs, lógica de negocio, autorizaciones y pagos
├── frontend/     # Aplicaciones separadas para público, vendedores y admin global
├── docker-compose.yml  # Orquestación local de servicios (base, cache, broker, etc.)
```

## Objetivos inmediatos
1. Garantizar módulos bien separados para `vendors`, `products`, `orders`, `payments` y `reviews`.
2. Documentar los roles y políticas básicas: comisiones, tiendas independientes, personalización y aislamiento de datos.
3. Crear un punto único para arrancar base de datos (PostgreSQL), cache (Redis), broker (Celery/Redis) y frontend (Next.js o similar).

## Cómo continuar
- Entrar en `backend/` para inicializar el framework escogido (Django + apps) y definir `requirements.txt`.
- Desarrollar el flujo público/vendedor/admin dentro de `frontend/` (Next.js/Vue) usando subdirectorios.
- Usar `docker-compose.yml` para poner en marcha servicios y exponer puertos.
- Mantener este README actualizado con decisiones de stack, comandos útiles y rutas clave.

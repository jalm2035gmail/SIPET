# Contratos API Versionados - Punto 4 de 8 (Fase 5)

Fecha ejecucion UTC: 2026-02-18T13:46:06.947869+00:00

## Contrato OpenAPI
- Esquema OpenAPI v1 publicado: `/Users/jalm/Dropbox/Apps/intelicoop/docs/mineria/fase5/04_openapi_v1.json`
- Modo de generacion: `fallback_minimo`.
- Compatibilidad retroactiva mantenida en rutas legacy `/api/...`.
- Rutas versionadas disponibles en `/api/v1/...`.

## Politicas de seguridad API
- Autenticacion por defecto: `rest_framework_simplejwt.authentication.JWTAuthentication`
- Autorizacion por rol: `IsAuditorOrHigher` y derivados por modulo.
- Rate limit `anon`: 60/min
- Rate limit `user`: 300/min

## Integracion con consumidores
- Matriz de compatibilidad publicada en CSV.

## Estado
- Punto 4 de 8 completado tecnicamente.
- Contratos versionados y politicas de consumo documentadas.

## Artefactos
- Matriz CSV: `/Users/jalm/Dropbox/Apps/intelicoop/docs/mineria/fase5/04_integracion_consumidores.csv`

# Seguridad de la Informacion - Punto 4 de 8 (Fase 6)

Fecha ejecucion UTC: 2026-02-18T14:23:19.572742+00:00

## Resumen
- Controles evaluados: 9
- Controles en cumple: 4
- Controles en revision: 5
- Estado global: Seguridad con brechas por remediar

| Dimension | Control | Estado | Detalle | Severidad |
|---|---|---|---|---|
| cifrado_transito | https_redirect_global | En revision | SECURE_SSL_REDIRECT=no | Alta |
| cifrado_transito | autenticacion_jwt_en_api | Cumple | auth_classes=1 | Alta |
| cifrado_reposo | credenciales_hash_robusto | En revision | usuarios_hash_robusto=0/3 | Alta |
| segregacion_rol | roles_MAIN_definidos | Cumple | roles_detectados=4 | Alta |
| segregacion_rol | endpoints_analitica_con_role_permission | Cumple | endpoints_protegidos=15 | Alta |
| control_acceso | cobertura_2fa_en_perfiles_activos | En revision | 2fa_activos=0/3 (0.00%) | Media |
| control_acceso | throttling_api_habilitado | Cumple | anon=60/min, user=300/min | Media |
| credenciales | expiracion_tokens_configurada | En revision | ACCESS_TOKEN_LIFETIME=no | Alta |
| credenciales | rotacion_tokens_refresh_configurada | En revision | ROTATE+BLACKLIST=no | Alta |

## Remediaciones recomendadas
- Activar HTTPS estricto (`SECURE_SSL_REDIRECT`, HSTS y cookies seguras) en ambiente productivo.
- Configurar expiracion y rotacion de JWT (`SIMPLE_JWT`) con blacklist de refresh tokens.
- Elevar cobertura de 2FA para usuarios con privilegios altos.

## Estado
- Punto 4 de 8 completado tecnicamente.
- Matriz MAIN de seguridad de la informacion generada con evidencia reproducible.

## Artefactos
- Reporte CSV: `/Users/jalm/Dropbox/Apps/intelicoop/docs/mineria/fase6/04_seguridad_informacion.csv`

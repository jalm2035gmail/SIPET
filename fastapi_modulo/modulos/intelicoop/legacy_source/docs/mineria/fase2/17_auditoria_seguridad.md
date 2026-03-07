# Auditoria de Seguridad y Cumplimiento - Fase 2

Fecha de generacion: 2026-02-18T03:37:51.268057+00:00

## Controles evaluados

| Control | Resultado | Detalle | Severidad |
|---|---|---|---|
| JWT habilitado en DRF | Cumple | DEFAULT_AUTHENTICATION_CLASSES configurado | Alta |
| Roles definidos (auditor/jefe/admin/superadmin) | Cumple | roles_detectados=4 | Alta |
| Perfiles activos | Cumple | activos=2, total=2 | Media |
| 2FA disponible y usuarios con 2FA | Cumple | usuarios_2fa=0 | Media |
| Cache configurado para soporte 2FA/OTP | Cumple | django.core.cache.backends.locmem.LocMemCache | Media |
| Superadministrador semilla existente | Cumple | superadmins=1 | Alta |
| Logging de aplicacion configurado | Cumple | log_level=INFO | Media |

## Resumen
- Controles en cumplimiento: 7
- Controles con atencion: 0

## Estado para checklist Fase 2 (Punto 7 de 8)
- Estado sugerido: `En revision`.
- Cierre requerido: resolver controles en atencion y adjuntar evidencia operativa.

# 2.3 Estandarizacion y Homologacion

## Estandares de formato
- Fechas: `YYYY-MM-DD` (UTC para procesos batch).
- Moneda: decimal con 2 posiciones.
- IDs tecnicos: enteros o UUID sin transformaciones ambiguas.

## Catalogos a homologar
- Estado de credito: `solicitado`, `aprobado`, `rechazado`.
- Segmentos socio: `hormiga`, `gran_ahorrador`, `inactivo`.
- Roles: `superadmin`, `administrador`, `jefe_departamento`, `auditor`.

## Reglas de deduplicacion iniciales
- Socio duplicado por `email` o documento oficial (cuando exista).
- Credito duplicado por combinacion `id_socio + fecha_creacion + monto + plazo`.

## Politica de resolucion
- Fuente oficial transaccional (Django DB) prevalece sobre copias locales.
- Registros conflictivos pasan a cola de remediacion manual.

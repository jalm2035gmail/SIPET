# Contratos Funcionales - Fase 1.6

## Contrato Scoring (tiempo real)

### Endpoint
- `POST /api/ml/scoring`

### Entrada minima
- `ingreso_mensual` (number > 0)
- `deuda_actual` (number >= 0)
- `antiguedad_meses` (int >= 0)

### Salida minima
- `score` (0..1)
- `recomendacion` (`aprobar|evaluar|rechazar`)
- `riesgo` (`bajo|medio|alto`)

### Consumidores
- Frontend de originacion de credito.
- Backend para persistencia de solicitud.

## Contrato Segmentacion (batch)

### Ejecucion
- Job batch diario/mensual segun motor.

### Salida minima
- `id_socio`
- `segmento`
- `fecha_ejecucion`

### Consumidores
- Dashboard de ahorros.
- Vista de socios.

## Roles y permisos (resumen)
- Superadministrador: acceso total.
- Administrador: acceso completo a operacion.
- Jefe de departamento: acceso acotado a su dominio.
- Auditor: solo lectura.

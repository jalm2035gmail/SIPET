# 2.5 Reglas de Negocio para Datos

## Rangos permitidos (inicial)
- `monto`: > 0
- `plazo`: > 0
- `ingreso_mensual`: > 0
- `deuda_actual`: >= 0
- `antiguedad_meses`: >= 0
- `dias_atraso`: >= 0

## Reglas de consistencia
- `deuda_actual` no debe exceder limites definidos por politica de riesgo.
- `fecha_pago` no puede ser anterior a `fecha_desembolso` cuando exista.
- `id_credito` y `id_socio` deben existir en maestros.

## Imputacion inicial
- Campos criticos de modelo: sin imputacion automatica (si falta, excluir).
- Campos no criticos: imputacion por mediana o categoria `desconocido`.

## Exclusion de registros
- Registros sin llave de integracion.
- Valores fuera de rango critico.
- Inconsistencias temporales no resolubles.

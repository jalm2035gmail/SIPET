# Casos de Uso y KPIs - Fase 1

## Caso 1: Scoring en originacion (tiempo real)
### Objetivo de negocio
Reducir incumplimiento y mejorar tiempo de respuesta en evaluacion de solicitudes.

### Entrada minima
- ingreso_mensual
- deuda_actual
- antiguedad_meses

### Salida minima
- score
- recomendacion
- riesgo

### KPIs
- KPI modelo: AUC, recall, precision.
- KPI operativo: latencia p95 del endpoint scoring.
- KPI negocio: tasa de aprobacion y tasa de incumplimiento por cohortes.

## Caso 2: Segmentacion de socios (batch)
### Objetivo de negocio
Mejorar acciones de captacion, retencion y oferta de productos.

### Entrada minima
- saldo total por socio
- total/cantidad de movimientos
- dias desde ultimo movimiento

### Salida minima
- segmento asignado por socio
- fecha de ejecucion

### KPIs
- Cobertura de segmentacion (% socios segmentados).
- Estabilidad mensual de segmentos.
- Conversion comercial por segmento.

## Caso 3: Mora temprana (batch diario)
### Objetivo de negocio
Priorizar gestion de cobranza y anticipar deterioro.

### Entrada esperada
- historial de pagos por credito
- atrasos por cuota
- estado y saldo del credito

### Salida esperada
- prob_mora_30d
- prob_mora_60d
- prob_mora_90d
- nivel_alerta

### KPIs
- Recall en mora temprana.
- Lift en priorizacion de cobranza.
- Recuperacion efectiva sobre cartera en alerta.

## Caso 4: Reglas de asociacion comercial
### Objetivo de negocio
Aumentar cross-sell y uso de productos.

### KPIs
- Soporte, confianza y lift por regla.
- Conversion de campanas basadas en reglas.

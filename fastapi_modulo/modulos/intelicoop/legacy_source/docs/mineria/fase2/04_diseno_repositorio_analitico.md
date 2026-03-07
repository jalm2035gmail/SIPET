# 2.4 Diseno del Repositorio Analitico

## Objetivo
Definir estructura minima para analitica y modelos de riesgo.

## Esquema propuesto (capa analitica)

### Dimensiones
- `dim_socio`
- `dim_credito_producto`
- `dim_fecha`

### Hechos
- `fact_credito_origen`
- `fact_pago_credito`
- `fact_ahorro_movimiento`
- `fact_scoring_inferencia` (fase 3)

## Granularidad
- Scoring: por solicitud/inferencia.
- Mora: por credito y fecha de corte.
- Segmentacion: por socio y fecha de ejecucion.

## Particionado sugerido
- Por `fecha_corte` mensual para historicos.
- Subparticion por dominio (`credito`, `ahorro`, `socio`) si aplica.

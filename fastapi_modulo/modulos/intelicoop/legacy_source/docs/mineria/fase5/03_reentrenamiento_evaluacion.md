# Evaluacion y Seleccion de Modelo - Punto 3 de 8 (Fase 3)

Fecha: 2026-02-18T13:41:39.084648+00:00
Fuente de datos: `synthetic`
Muestras de validacion: 52

## Metricas globales

- Modelo desplegado: brier=0.405636, acc=0.288462, auc=0.138393
- Benchmark: brier=0.435419, acc=0.153846, auc=0.047619

## Estabilidad por segmentos

- Segmentos elegibles (>= 10 muestras): 7
- Segmentos estables: 7
- Proporcion estable: 100.00%
- Umbral estabilidad: abs(delta brier vs global) <= 0.12

## Decision de seleccion

- Mejora global vs benchmark: si
- Estabilidad suficiente: si
- Decision: `mantener_modelo_desplegado`

## Artefactos
- Modelo evaluado: `/Users/jalm/Dropbox/Apps/intelicoop/backend/fastapi_service/app/core/modelo_scoring.pkl`
- Reporte CSV: `/Users/jalm/Dropbox/Apps/intelicoop/docs/mineria/fase5/03_reentrenamiento_evaluacion.csv`

## Estado
- Punto 3 de 8 completado tecnicamente.

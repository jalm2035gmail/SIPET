# Priorizacion de Submodulos Complementarios - Punto 1 de 7 (Fase 4)

Fecha: 2026-02-18T12:25:21.143489+00:00

## Base de datos evaluada
- Socios: 0
- Creditos: 0
- Historial de pagos: 0
- Cuentas: 0
- Transacciones: 0

## Criterio de priorizacion
- score_prioridad = 60% impacto_negocio + 40% disponibilidad_datos
- El orden final privilegia valor operativo inmediato con factibilidad tecnica.

## Orden recomendado de implementacion
- 1. `mora_temprana` (score=0.5700, impacto=0.95, datos=0.00)
  - Objetivo: Riesgo y cobranzas.
  - Alcance MVP: alertas 30/60/90 con clasificacion bajo/medio/alto por credito.
- 2. `segmentacion_socios` (score=0.4680, impacto=0.78, datos=0.00)
  - Objetivo: Comercial y retencion.
  - Alcance MVP: segmentacion mensual y perfil descriptivo por socio.
- 3. `reglas_asociacion` (score=0.4320, impacto=0.72, datos=0.00)
  - Objetivo: Cross-sell y campanas.
  - Alcance MVP: top reglas soporte/confianza/lift para oportunidades comerciales.

## Resultado
- Punto 1 de 7 completado tecnicamente.
- Submodulos listos para ejecucion secuencial en Fase 4.

## Artefactos
- Reporte CSV: `/Users/jalm/Dropbox/Apps/intelicoop/docs/mineria/fase4/01_priorizacion_submodulos.csv`

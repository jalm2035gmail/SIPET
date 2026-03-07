# Servicio de Inferencia MVP - Punto 4 de 8 (Fase 3)

Fecha: 2026-02-18

## Endpoint operativo

- `POST /api/analitica/ml/scoring/evaluar/`

## Contrato de entrada validado

- `ingreso_mensual` (decimal > 0)
- `deuda_actual` (decimal >= 0 y no mayor a `ingreso_mensual`)
- `antiguedad_meses` (entero >= 0)
- `persist` (opcional)
- `solicitud_id`, `credito`, `socio`, `model_version` (opcionales)

## Contrato de salida

- `request_id` (uuid para trazabilidad)
- `score`
- `recomendacion`
- `riesgo`
- `persisted`
- `resultado_id`
- `latency_ms` (tiempo de respuesta observado por request)

## Manejo de errores controlados

- `400`: validaciones de entrada.
- `502`: servicio externo no disponible o respuesta invalida de scoring.
- En errores `502` se devuelve `request_id` para seguimiento.

## Evidencia tecnica

- Archivo de endpoint: `backend/django_project/apps/analitica/views.py`
- Validaciones: `backend/django_project/apps/analitica/serializers.py`
- Pruebas: `backend/django_project/apps/analitica/tests.py`
- Resultado de pruebas: `manage.py test apps.analitica.tests` -> `OK (12 tests)`

## Estado

- Punto 4 de 8 completado tecnicamente.

# Persistencia y Trazabilidad de Scoring - Punto 5 de 8 (Fase 3)

Fecha: 2026-02-18

## Implementacion de persistencia historica

- Cada inferencia con `persist=true` se guarda en `resultados_scoring`.
- Se conserva timestamp de registro con `fecha_creacion`.
- Se registra `model_version` para trazabilidad de version de modelo.
- Se guardan variables de entrada usadas en inferencia:
  - `ingreso_mensual`
  - `deuda_actual`
  - `antiguedad_meses`

## Trazabilidad por solicitud y socio

- Consulta por solicitud:
  - `GET /api/analitica/ml/scoring/<solicitud_id>/`
- Consulta por socio:
  - `GET /api/analitica/ml/scoring/socio/<socio_id>/`
- Consulta historica filtrable:
  - `GET /api/analitica/ml/scoring-resultados/?solicitud_id=&socio=&credito=&model_version=&fecha_desde=&fecha_hasta=`

## Mejora aplicada

- `request_id` ahora se persiste en la tabla y coincide con el `request_id` de respuesta del endpoint de inferencia.

## Evidencia tecnica

- Endpoint y filtros: `backend/django_project/apps/analitica/views.py`
- Rutas: `backend/django_project/apps/analitica/urls.py`
- Pruebas: `backend/django_project/apps/analitica/tests.py`
- Resultado pruebas: `manage.py test apps.analitica.tests` -> `OK (14 tests)`

## Estado

- Punto 5 de 8 completado tecnicamente.

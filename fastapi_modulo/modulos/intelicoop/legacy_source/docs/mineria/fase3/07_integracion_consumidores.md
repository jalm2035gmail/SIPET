# Integracion con Sistemas Consumidores - Punto 6 de 8 (Fase 3)

Fecha: 2026-02-18

## Integracion con originacion de credito

- La vista de alta de credito consume scoring en linea:
  - `POST /api/analitica/ml/scoring/evaluar/` (preview de score).
- Al crear credito, persiste resultado de scoring asociado:
  - `persist=true`, con `credito`, `socio`, `solicitud_id`, `model_version`.
- Archivo: `frontend/src/pages/CreditoForm.jsx`.

## Exposicion para consumo operativo y riesgo

- Endpoint de resumen agregado:
  - `GET /api/analitica/ml/scoring/resumen/`
- Respuesta incluye:
  - `total_inferencias`
  - `score_promedio`
  - `por_riesgo` (bajo/medio/alto)
  - `por_recomendacion` (aprobar/evaluar/rechazar)
  - `recientes` (ultimas inferencias)
- Archivos:
  - `backend/django_project/apps/analitica/views.py`
  - `backend/django_project/apps/analitica/urls.py`

## Integracion frontend consumidora

- `CreditosList` ahora consulta y muestra resumen de riesgo/scoring.
- Archivo: `frontend/src/pages/CreditosList.jsx`.

## Validacion de contrato API

- Prueba automatica del endpoint de resumen:
  - `test_scoring_resumen_endpoint`
- Suite ejecutada:
  - `manage.py test apps.analitica.tests` -> `OK (15 tests)`.

## Estado

- Punto 6 de 8 completado tecnicamente.

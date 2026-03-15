# MVP Scoring - Persistencia Inicial

Fecha: 2026-02-18

## Implementado
- Modelo `ResultadoScoring` en Django (`apps.analitica.models`).
- Migracion `0002_resultadoscoring.py`.
- API de persistencia/listado:
  - `GET/POST /api/analitica/ml/scoring-resultados/`
  - `GET /api/analitica/ml/scoring/<solicitud_id>/`
- Endpoint unificado de evaluacion de scoring en Django:
  - `POST /api/analitica/ml/scoring/evaluar/`
  - consume servicio FastAPI y opcionalmente persiste (`persist=true`).
- Integracion en frontend `CreditoForm.jsx`:
  - scoring en vivo via endpoint Django.
  - al crear credito, persiste scoring por endpoint unificado.
- Pruebas API actualizadas en `apps.analitica.tests` (incluye endpoint evaluar).

## Objetivo cubierto
- Fase 3.5 Persistencia de resultados.
- MAIN para Fase 3.6 Integracion con consumidores.

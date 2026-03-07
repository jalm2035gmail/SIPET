# Pruebas del MVP - Punto 7 de 8 (Fase 3)

Fecha: 2026-02-18

## Cobertura ejecutada

- Pruebas unitarias/API analitica:
  - `manage.py test apps.analitica.tests`
  - Resultado: `OK (17 tests)`.
- Prueba de integracion del flujo analitica:
  - `manage.py test apps.analitica.tests_integration`
  - Resultado: `OK (1 test)`.
- Prueba de carga ligera:
  - `manage.py probar_carga_scoring_mvp --requests 120 --warmup 10`
  - Resultado: `HTTP 200=120/120`, `error_rate=0.00%`, `p95=16.56 ms`.

## Validaciones clave

- Seguridad por rol:
  - Auditor no puede ejecutar `POST` en inferencia (403 esperado).
  - Administrador si puede ejecutar inferencia (200 esperado).
- Consistencia funcional:
  - Flujo completo evaluar->persistir->consultar por solicitud/socio->resumen operativo.
- Rendimiento del endpoint:
  - Objetivo p95 <= 500 ms cumplido en benchmark local.

## Evidencia

- Tests: `backend/django_project/apps/analitica/tests.py`
- Integracion: `backend/django_project/apps/analitica/tests_integration.py`
- Comando de carga: `backend/django_project/apps/analitica/management/commands/probar_carga_scoring_mvp.py`
- Reporte carga:
  - `docs/mineria/fase3/08_prueba_carga_scoring_mvp.md`
  - `docs/mineria/fase3/08_prueba_carga_scoring_mvp.csv`

## Estado

- Punto 7 de 8 completado tecnicamente.

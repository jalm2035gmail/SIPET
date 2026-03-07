# Fase 3 - Punto 1 de 8
# Diseno Funcional y Tecnico del Scoring MVP

Fecha: 2026-02-18
Estado: En revision

## 1. Objetivo
Definir el diseno funcional y tecnico del MVP de scoring para originacion de credito, incluyendo entrada, salida, reglas de decision, manejo de errores y versionado.

## 2. Alcance funcional
- Calculo de score de riesgo para solicitudes de credito.
- Clasificacion de recomendacion: `aprobar`, `evaluar`, `rechazar`.
- Persistencia opcional del resultado para trazabilidad.
- Consumo desde frontend en tiempo real y al guardar solicitud.

## 3. Contratos API

### 3.1 Endpoint de evaluacion (Django)
- `POST /api/analitica/ml/scoring/evaluar/`

Entrada:
- `ingreso_mensual` (decimal > 0)
- `deuda_actual` (decimal >= 0)
- `antiguedad_meses` (entero >= 0)
- `persist` (bool opcional)
- `solicitud_id` (string opcional)
- `credito` (id opcional)
- `socio` (id opcional)
- `model_version` (string opcional)

Salida:
- `score` (0..1)
- `recomendacion` (`aprobar|evaluar|rechazar`)
- `riesgo` (`bajo|medio|alto`)
- `persisted` (bool)
- `resultado_id` (id nullable)

Errores:
- `400`: validacion de datos de entrada.
- `401/403`: auth/permiso por rol.
- `502`: servicio de scoring no disponible o respuesta invalida.

### 3.2 Endpoint de persistencia/listado
- `GET/POST /api/analitica/ml/scoring-resultados/`
- `GET /api/analitica/ml/scoring/<solicitud_id>/`

## 4. Reglas de decision
- `score >= 0.80` -> `recomendacion=aprobar`, `riesgo=bajo`
- `0.60 <= score < 0.80` -> `recomendacion=evaluar`, `riesgo=medio`
- `score < 0.60` -> `recomendacion=rechazar`, `riesgo=alto`

## 5. Arquitectura tecnica (MVP)
- Frontend (`CreditoForm.jsx`) consume endpoint Django.
- Django (`apps.analitica`) valida request y orquesta llamada.
- FastAPI (`/api/ml/scoring`) calcula score.
- Django persiste en `ResultadoScoring` cuando `persist=true`.

## 6. Versionado y trazabilidad
- Version de modelo en payload (`model_version`) con default `weighted_score_v1`.
- Campo `request_id` UUID en `ResultadoScoring`.
- Relacion opcional a `credito` y `socio`.
- Identificacion funcional por `solicitud_id`.

## 7. Seguridad y permisos
- Acceso protegido por `IsAuditorOrHigher`.
- Auditor solo lectura para endpoints que modifiquen datos segun reglas globales.
- Registro de usuario autenticado en trazas de servidor.

## 8. Criterios de aceptacion del punto 1
- Contrato de endpoint definido y documentado.
- Reglas de decision documentadas.
- Manejo de errores definido.
- Estrategia de versionado y trazabilidad documentada.

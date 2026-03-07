# Fase 6: Reubicacion de datos, modelos ML y pipelines

## Objetivo

Cerrar la decision tecnica sobre que activos de datos y analitica de `intelicoop` viven dentro de SIPET y cuales quedan fuera del runtime principal.

## Decision final de Fase 6

### 1. Datos operativos y analiticos que se quedan en SIPET

Se quedan dentro del backend principal de SIPET, usando la persistencia ya integrada del proyecto:

- socios
- creditos
- historial de pagos
- cuentas y transacciones
- campanas
- prospectos
- resultados de scoring

La persistencia activa del modulo queda en las tablas SQLAlchemy definidas en:

- `intelicoop_db_models.py`

No se conserva como almacenamiento activo la base SQLite ni ninguna persistencia propia de la app original.

## 2. Modelo ML que se queda activo

El scoring crediticio sigue vivo en el MVP y queda oficialmente reubicado dentro del modulo SIPET.

Ubicacion estable aprobada:

- modelo: `fastapi_modulo/modulos/intelicoop/assets/modelo_scoring.pkl`
- servicio de inferencia: `fastapi_modulo/modulos/intelicoop/intelicoop_scoring.py`
- endpoints consumidores: `fastapi_modulo/modulos/intelicoop/intelicoop.py`

Con esto se da por cerrada la migracion del scoring desde el servicio FastAPI standalone a una capacidad interna del backend principal.

## 3. Versionado del modelo

Para esta fase se aprueba el siguiente esquema minimo:

- version activa: `intelicoop_scoring_v1`
- el archivo `.pkl` actual es la unica version operativa del MVP
- cualquier recalibracion o reemplazo futuro debe actualizar:
  - el archivo del modelo en `assets/`
  - la constante `MODEL_VERSION`
  - la evidencia documental correspondiente

No entra en esta fase automatizar entrenamiento, registry de modelos ni despliegue continuo de artefactos ML.

## 4. Pipelines de mineria y procesos batch

Los pipelines heredados no se integran al runtime principal de SIPET en esta fase.

Decision aprobada:

- `legacy_source/data_pipelines/*` queda como referencia tecnica
- su ejecucion, si todavia se necesita, se considera proceso offline documentado
- no se conectan cron jobs, spark jobs ni orquestadores al backend principal de SIPET en el MVP

Esto incluye procesos asociados a:

- segmentacion automatizada
- mora temprana batch
- reglas de asociacion
- automatizaciones de mineria
- jobs historicos de experimentacion o gobierno del modelo

## 5. Alcance operativo resultante

### Activo dentro de SIPET

- CRUD operativo del modulo
- scoring en linea
- persistencia historica de inferencias de scoring
- dashboard simplificado alimentado por datos del modulo

### Fuera del runtime principal

- pipelines spark heredados
- cron jobs heredados
- procesos batch de mineria no MVP
- servicios externos standalone del proyecto original

## 6. Criterio de salida de Fase 6

La fase queda cerrada cuando queda explicitamente definido que:

- los datos activos del modulo viven en la persistencia principal de SIPET
- el modelo ML activo vive en `assets/modelo_scoring.pkl`
- el servicio de scoring vive en `intelicoop_scoring.py`
- los pipelines heredados quedan fuera del runtime principal y solo como proceso offline documentado

## Fase 6 cerrada

Con esta decision:

- el scoring queda oficialmente reubicado en una ubicacion estable del modulo
- los datos activos del modulo quedan consolidados en SIPET
- los pipelines heredados dejan de ser una dependencia operativa del MVP

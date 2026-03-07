# Intelicoop en SIPET

## Estado actual

`intelicoop` ya funciona como modulo SIPET con backend y frontend propios del proyecto principal.

## Codigo activo del modulo

- `intelicoop.py`
- `intelicoop.html`
- `intelicoop.js`
- `intelicoop_models.py`
- `intelicoop_db_models.py`
- `intelicoop_store.py`
- `intelicoop_scoring.py`
- `assets/modelo_scoring.pkl`

## Documentacion activa

- `fase_1_alcance_sipet.md`
- `fase_2_mapa_migracion_sipet.md`
- `fase_6_reubicacion_datos_modelos_pipelines.md`
- `fase_7_pruebas_integracion_regresion.md`
- `OPERACION_ESTRUCTURA.md`

## Referencia heredada

El codigo de la aplicacion independiente original se conserva en:

- `legacy_source/backend`
- `legacy_source/frontend`
- `legacy_source/docs`
- `legacy_source/data_pipelines`
- `legacy_source/imagenes`
- `legacy_source/descripcion.txt`
- `legacy_source/mineria.txt`

Ese material ya no es el punto de entrada del modulo. Sirve solo como referencia para seguir migrando funcionalidad faltante.

## Limpieza final

Los restos standalone que estaban fuera del modulo activo fueron retirados en Fase 8.
El unico punto de entrada vigente de Intelicoop en SIPET es `fastapi_modulo/modulos/intelicoop`.

## Regla de trabajo

Si una funcionalidad ya existe en los archivos activos del modulo SIPET, cualquier cambio nuevo debe hacerse ahi y no en `legacy_source`.

## Decision operativa vigente

- Los datos activos del modulo viven en las tablas SQLAlchemy de SIPET.
- El scoring activo usa `assets/modelo_scoring.pkl` e `intelicoop_scoring.py`.
- Los pipelines heredados en `legacy_source/data_pipelines` no forman parte del runtime principal; quedan como referencia offline documentada.

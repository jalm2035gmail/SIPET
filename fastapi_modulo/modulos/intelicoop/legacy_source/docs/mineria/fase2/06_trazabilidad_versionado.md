# 2.6 Trazabilidad y Versionado

## Convenciones de version
- Dataset: `ds_YYYYMMDD_vN`
- Feature set: `fs_YYYYMMDD_vN`
- Modelo: `ml_<tipo>_vN`

## Metadatos minimos por corrida
- `fecha_corte`
- `origen_datos`
- `reglas_aplicadas`
- `version_feature_set`
- `version_modelo` (si aplica)
- `usuario/servicio_ejecutor`

## Lineage requerido
- Origen -> Transformacion -> Resultado.
- Guardar hash o identificador de corrida para auditoria.

## Evidencia
- Log tecnico por corrida.
- Resumen de calidad por tabla.
- Trazabilidad de inferencias (fase 3).

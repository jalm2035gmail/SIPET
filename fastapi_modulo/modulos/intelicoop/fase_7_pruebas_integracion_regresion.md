# Fase 7: Pruebas de integracion y regresion

## Objetivo

Validar el modulo `intelicoop` ya absorbido por SIPET sobre los flujos realmente activos:

- rutas
- vistas
- permisos
- persistencia
- endpoints
- flujos clave
- dependencias reales del runtime

## Cobertura activa definida para Fase 7

La regresion minima del modulo queda cubierta por pruebas sobre el modulo SIPET activo, no sobre `legacy_source`.

Casos cubiertos:

- acceso denegado a vista HTML sin permiso `Intelicoop`
- acceso permitido a vista HTML con permiso `Intelicoop`
- acceso denegado a endpoints API sin permiso
- acceso permitido para admin aunque no tenga checkbox explicito
- flujo operativo clave:
  - alta de socio
  - alta de credito
  - scoring automatico al crear credito
  - registro de pago
  - consulta de detalle del credito
  - apertura de cuenta
  - registro de transaccion
  - alta de campana
  - alta de prospecto
  - resumen de scoring
  - resumen de dashboard

Archivo de pruebas activo:

- `test_intelicoop_phase7.py`

## Resultado esperado de Fase 7

Si esta suite pasa, se considera validado que:

- la navegacion principal del modulo responde
- los permisos del modulo se aplican
- la persistencia principal del modulo funciona
- los endpoints MAIN del MVP siguen operativos
- el flujo de scoring continua funcionando dentro de SIPET

## Dependencias reales del modulo absorbido

### Dependencias directas del modulo activo

- FastAPI
- SQLAlchemy
- Pydantic
- `pickle` de la libreria estandar

### Dependencias de scoring realmente activas

El artefacto actual `assets/modelo_scoring.pkl` es un `dict` serializado y no requiere `scikit-learn`, `pandas`, `numpy` ni `joblib` para su carga basica.

Por lo tanto, despues de absorber `intelicoop`, el MVP activo no depende de:

- frontend React/Vite heredado
- servicio FastAPI standalone de scoring
- jobs Spark heredados
- dependencias de entrenamiento offline para ejecutar el scoring actual

## Dependencias que siguen siendo externas al runtime MVP

Estas piezas pueden seguir existiendo como referencia o para procesos offline, pero no son necesarias para operar el modulo activo dentro de SIPET:

- `legacy_source/frontend/*`
- `legacy_source/backend/fastapi_service/*`
- `legacy_source/data_pipelines/*`
- comandos heredados de entrenamiento, recalibracion o mineria

## Criterio de salida de Fase 7

La fase queda cerrada cuando:

- existe una suite activa de regresion para el modulo SIPET
- los permisos del modulo quedan validados
- los flujos clave del MVP quedan validados
- queda documentado que dependencias son realmente necesarias para operar Intelicoop dentro de SIPET

## Fase 7 cerrada

Con esta fase:

- Intelicoop deja de depender de pruebas del legado para validar el MVP actual
- SIPET tiene una MAIN minima de regresion del modulo absorbido
- queda explicitado que dependencias siguen siendo operativas y cuales ya no

# Operacion y Estructura de Intelicoop

## Punto de entrada

- vista principal: `/inicio/intelicoop`
- APIs del modulo: `/api/intelicoop/*`
- router activo: `intelicoop.py`

## Reglas de acceso

- el modulo usa autenticacion y sesion de SIPET
- solo entra quien tenga acceso `Intelicoop` en usuarios
- admin y superadmin tambien pueden entrar

## Archivos activos

- `intelicoop.py`
  - rutas HTML y endpoints JSON
- `intelicoop.html`
  - vista principal del modulo
- `intelicoop.js`
  - interacciones frontend del MVP
- `intelicoop_db_models.py`
  - tablas SQLAlchemy del modulo
- `intelicoop_store.py`
  - persistencia y agregados
- `intelicoop_scoring.py`
  - scoring activo del modulo
- `assets/modelo_scoring.pkl`
  - artefacto ML activo
- `test_intelicoop_phase7.py`
  - regresion minima del modulo

## Flujos operativos cubiertos

- socios
- creditos
- pagos
- ahorros
- campanas
- prospectos
- scoring
- dashboard simplificado

## Referencia historica

El codigo heredado que se conserva solo como referencia vive en:

- `legacy_source/*`

No se deben hacer cambios nuevos fuera de los archivos activos del modulo.

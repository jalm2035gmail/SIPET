# Evolucion tecnica del modulo

## Objetivo

Mantener una evolucion incremental del modulo `cartera_prestamos` sin rehacer frontend, backend y datos en una sola iteracion.

## Fases

### Fase 1. Estilos desacoplados

- Mover estilos de las vistas a `static/css`.
- Consolidar estilos base y estilos por vista.
- Reducir acoplamiento entre estructura HTML y presentacion.

### Fase 2. Interaccion cliente

- Incorporar `static/js` con utilidades compartidas y scripts por subdominio.
- Habilitar filtros, exportaciones, refresh, busqueda y eventos de UI.
- Evitar logica inline en templates.

### Fase 3. Integracion de APIs

- Exponer endpoints FastAPI por subdominio.
- Conectar las vistas a snapshots y exportables reales.
- Mantener permisos por seccion y por rol desde dependencias comunes.

### Fase 4. Componentizacion UI

- Extraer patrones reutilizables de layout, topbar, rail, cards KPI y tablas.
- Centralizar clases base en CSS compartido y hooks en templates.
- Preparar la migracion a parciales HTML si el modulo sigue creciendo.

### Fase 5. Datos operativos y filtros avanzados

- Alimentar el modulo con repositorios, servicios y persistencia real.
- Incorporar filtros por sucursal, asesor, producto, tramo y periodo.
- Ampliar drill-down, exportables y consultas operativas.

## Estado actual

- Fase 1: completada.
- Fase 2: completada.
- Fase 3: completada.
- Fase 4: completada en base CSS compartida; parciales HTML quedan como siguiente paso natural.
- Fase 5: iniciada con KPIs, exportables y permisos; faltan filtros avanzados y mas fuentes operativas.

## Criterios de continuidad

- Todo cambio visual nuevo debe reutilizar `static/css/cartera_components.css` antes de crear estilos aislados.
- Toda interaccion nueva debe vivir en `static/js` y no en scripts inline.
- Toda vista nueva debe tener endpoint o placeholder formalizado dentro de `MODULE_SECTIONS`.
- Toda capacidad operativa nueva debe incluir prueba en `tests/`.

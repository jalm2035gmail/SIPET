# Fase 2: Mapa de migracion de Intelicoop a modulo SIPET

## Objetivo

Traducir la estructura actual de `intelicoop` a la forma real de SIPET:

- routers FastAPI integrados en `fastapi_modulo/main.py`
- vistas HTML simples o parciales renderizadas por SIPET
- JS puntual para interaccion
- almacenamiento y modelos alineados al backend principal

Esta fase no implementa todavia toda la migracion. Define exactamente que archivo se convierte en que cosa.

## Estructura actual

`intelicoop` hoy conserva cuatro bloques:

- `backend/django_project`: modelos, serializers, vistas y urls de negocio
- `backend/fastapi_service`: scoring y algunos assets de backend
- `frontend/src`: paginas React que muestran los flujos funcionales
- `docs` y `data_pipelines`: referencia funcional y analitica

## Estructura objetivo en SIPET

La estructura objetivo para el modulo es esta:

- `fastapi_modulo/modulos/intelicoop/intelicoop.py`
- `fastapi_modulo/modulos/intelicoop/intelicoop.html`
- `fastapi_modulo/modulos/intelicoop/intelicoop.js`
- `fastapi_modulo/modulos/intelicoop/intelicoop_store.py`
- `fastapi_modulo/modulos/intelicoop/intelicoop_models.py`
- `fastapi_modulo/modulos/intelicoop/intelicoop_scoring.py`
- `fastapi_modulo/modulos/intelicoop/assets/*`

Si el modulo crece, se pueden agregar archivos internos por dominio, pero el punto de entrada debe seguir siendo claro y compatible con SIPET.

## Decision de organizacion interna

Para no meter toda la complejidad en un solo archivo, `intelicoop` debe quedar asi:

### Entrada del modulo

- `intelicoop.py`
  - crea el `APIRouter`
  - registra rutas HTML y endpoints JSON
  - compone los subservicios internos

### Modelos y persistencia

- `intelicoop_models.py`
  - modelos SQLAlchemy o estructuras persistentes equivalentes en SIPET
  - entidades base del MVP: socios, creditos, pagos, cuentas, transacciones, campanas, prospectos, resultados de scoring

- `intelicoop_store.py`
  - funciones CRUD y consultas
  - agregados para dashboard
  - helpers de persistencia

### Analitica

- `intelicoop_scoring.py`
  - logica de scoring
  - carga del modelo `modelo_scoring.pkl`
  - endpoints o helpers para inferencia
  - persistencia de resultados de scoring

### Vista

- `intelicoop.html`
  - shell HTML principal del modulo dentro del layout SIPET
  - tabs o secciones para socios, creditos, ahorros, campanas y dashboard

- `intelicoop.js`
  - consumo de endpoints internos
  - renderizacion dinamica
  - formularios y tablas del MVP

### Assets

- `assets/`
  - iconos e imagenes puntuales que realmente use el modulo

## Mapeo archivo por archivo

### Backend Django a modulo SIPET

#### Socios

- `backend/django_project/apps/socios/models.py`
  - migrar a `intelicoop_models.py`
- `backend/django_project/apps/socios/views.py`
  - migrar a `intelicoop.py`
- `backend/django_project/apps/socios/urls.py`
  - no se migra como archivo; sus rutas se redefinen en `intelicoop.py`

#### Creditos

- `backend/django_project/apps/creditos/models.py`
  - migrar a `intelicoop_models.py`
- `backend/django_project/apps/creditos/views.py`
  - migrar a `intelicoop.py`
- `backend/django_project/apps/creditos/urls.py`
  - no se migra como archivo

#### Ahorros

- `backend/django_project/apps/ahorros/models.py`
  - migrar a `intelicoop_models.py`
- `backend/django_project/apps/ahorros/views.py`
  - migrar a `intelicoop.py`
- `backend/django_project/apps/ahorros/urls.py`
  - no se migra como archivo

#### Analitica

- `backend/django_project/apps/analitica/models.py`
  - migrar parcialmente:
  - `Campania`, `Prospecto`, `ResultadoScoring` entran al MVP y pasan a `intelicoop_models.py`
  - `ResultadoMoraTemprana`, `ResultadoSegmentacionSocio`, `ReglaAsociacionProducto`, `AlertaMonitoreo`, `EjecucionPipeline` quedan diferidos o solo como referencia

- `backend/django_project/apps/analitica/views.py`
  - migrar parcialmente:
  - entran al MVP los endpoints de campanas, prospectos, resumen de scoring y dashboard simplificado
  - se difieren endpoints de mora, pipelines, exportaciones avanzadas y drill-downs complejos

- `backend/django_project/apps/analitica/urls.py`
  - no se migra como archivo

#### Authentication

- `backend/django_project/apps/authentication/models.py`
  - no se migra como subsistema
  - usar solo como referencia de roles y capacidades
- `backend/django_project/apps/authentication/views.py`
  - no se migra
- `backend/django_project/apps/authentication/urls.py`
  - no se migra

### FastAPI scoring a modulo SIPET

- `backend/fastapi_service/app/core/scoring_model.py`
  - migrar a `intelicoop_scoring.py`
- `backend/fastapi_service/app/core/modelo_scoring.pkl`
  - conservar y reubicar en `assets` o ruta interna estable del modulo
- `backend/fastapi_service/app/api/scoring.py`
  - fusionar en `intelicoop.py` o `intelicoop_scoring.py`
- `backend/fastapi_service/app/main.py`
  - no se migra como app separada
- `backend/fastapi_service/tests/test_scoring_api.py`
  - usar como base para nuevas pruebas SIPET

### Frontend React a vista SIPET

#### Paginas que si se migran

- `frontend/src/pages/SociosList.jsx`
  - migrar a seccion de `intelicoop.html` + consumo en `intelicoop.js`
- `frontend/src/pages/CreditosList.jsx`
  - migrar a seccion de `intelicoop.html` + `intelicoop.js`
- `frontend/src/pages/CreditoForm.jsx`
  - migrar a formulario dentro de `intelicoop.html`
- `frontend/src/pages/CreditoDetail.jsx`
  - migrar a panel o modal dentro de `intelicoop.html`
- `frontend/src/pages/AhorrosDashboard.jsx`
  - migrar a seccion dashboard de captacion
- `frontend/src/pages/CampaniasList.jsx`
  - migrar a seccion campañas
- `frontend/src/pages/ProspectosList.jsx`
  - migrar a seccion prospectos
- `frontend/src/pages/Dashboards18.jsx`
  - migrar parcialmente a dashboard simplificado del MVP

#### Paginas que no se migran

- `frontend/src/pages/Login.jsx`
  - no se migra
- `frontend/src/pages/Register.jsx`
  - no se migra
- `frontend/src/pages/ForgotPassword.jsx`
  - no se migra
- `frontend/src/pages/Home.jsx`
  - no se migra como pagina propia; puede servir como referencia visual
- `frontend/src/pages/SociosInactivos.jsx`
  - se difiere

#### Componentes React

- `frontend/src/components/*`
  - no se migran 1:1
  - sirven como referencia de comportamiento, columnas y layout

#### Servicios frontend

- `frontend/src/services/api_django.js`
  - referencia para contratos API
- `frontend/src/services/api_fastapi.js`
  - no se migra como cliente separado
- `frontend/src/services/auth_storage.js`
  - no se migra
- `frontend/src/services/token_refresh.js`
  - no se migra

## Assets y referencias

### Se conservan

- `imagenes/iconos/*.svg`
- `imagenes/cc.png`
- `imagenes/login.png` solo si alguna vista final la reutiliza
- `docs/mineria/dashboards/*` como referencia de KPIs y contratos del dashboard
- `docs/mineria/growth_engine/*` como referencia funcional de campanas y colocacion
- `docs/mineria/customer_intelligence/*` como referencia de segmentacion futura

### Se archivan como referencia documental

- `docs/mineria/fase1` a `fase7`
- `data_pipelines/spark_jobs/*`
- `descripcion.txt`
- `mineria.txt`

No deben bloquear el MVP del modulo.

## Registro en SIPET

Para que el modulo funcione dentro de SIPET, Fase 3 debera hacer estas integraciones:

1. Crear `router` en `intelicoop.py`.
2. Importarlo en `fastapi_modulo/main.py`.
3. Registrarlo con `app.include_router(...)` o el patron actual que use SIPET.
4. Exponer una ruta HTML principal.
5. Exponer endpoints JSON del modulo.
6. Agregar acceso desde el menu o desde una ruta backend visible.

## Contratos iniciales del MVP

Estas son las rutas objetivo recomendadas:

- `GET /inicio/intelicoop`
- `GET /api/intelicoop/socios`
- `POST /api/intelicoop/socios`
- `GET /api/intelicoop/creditos`
- `POST /api/intelicoop/creditos`
- `GET /api/intelicoop/creditos/{id}`
- `GET /api/intelicoop/ahorros/resumen`
- `GET /api/intelicoop/campanas`
- `POST /api/intelicoop/campanas`
- `GET /api/intelicoop/prospectos`
- `POST /api/intelicoop/scoring/evaluar`
- `GET /api/intelicoop/scoring/resumen`
- `GET /api/intelicoop/dashboard/resumen`

## Orden de implementacion recomendado

### Paso 1

Crear esqueleto SIPET del modulo:

- `intelicoop.py`
- `intelicoop.html`
- `intelicoop.js`

### Paso 2

Migrar entidades base:

- socios
- creditos
- ahorros

### Paso 3

Migrar scoring:

- modelo
- servicio
- resumen

### Paso 4

Migrar campanas y prospectos

### Paso 5

Migrar dashboard simplificado

### Paso 6

Conectar al menu y layout SIPET

## Dependencias y bloqueos detectados

- los modelos de Django deben traducirse a la capa de persistencia real de SIPET
- las vistas React dependen de endpoints REST que habra que rehacer bajo el router FastAPI principal
- el dashboard 1.8 es muy grande para migrarlo literal; conviene recortarlo desde el inicio
- hay que decidir durante implementacion si `intelicoop` persistira en SQLite, JSON store o tablas SQLAlchemy ya manejadas por SIPET

## Criterio de salida de Fase 2

La fase queda cerrada cuando ya este decidido:

- que archivo fuente migra a que archivo destino
- que piezas entran al MVP
- que piezas se difieren
- cual sera la estructura final del modulo en SIPET
- cuales rutas y contratos iniciales tendra el modulo

## Siguiente fase

Fase 3: crear el esqueleto real del modulo `intelicoop` dentro de SIPET y empezar la migracion del backend MVP.

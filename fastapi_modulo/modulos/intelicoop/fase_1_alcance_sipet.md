# Fase 1: Alcance de Intelicoop como modulo SIPET

## Objetivo

Convertir `intelicoop` de aplicacion independiente a modulo integrado de SIPET, reutilizando solo la funcionalidad de negocio y descartando infraestructura propia duplicada.

## Diagnostico actual

El codigo disponible mezcla tres capas:

1. Operacion cooperativa:
   - socios
   - creditos
   - ahorros
   - campanas y prospectos
2. Analitica aplicada:
   - scoring crediticio
   - mora temprana
   - segmentacion de socios
   - reglas de asociacion de productos
   - dashboards ejecutivos y operativos
3. Infraestructura de app standalone:
   - autenticacion propia
   - frontend React/Vite completo
   - servicio FastAPI separado
   - despliegue Docker

## Inventario funcional detectado

### Dominio operativo

- `socios`: catalogo base de personas con segmento simple.
- `creditos`: solicitudes, estados y pagos.
- `ahorros`: cuentas y transacciones.
- `campanias`: campanas comerciales y prospectos.

### Dominio analitico

- `resultado_scoring`: inferencias de riesgo para credito.
- `resultado_mora_temprana`: alertas preventivas para cartera.
- `resultado_segmentacion_socio`: clasificacion comercial de socios.
- `regla_asociacion_producto`: recomendaciones de cross-sell.
- tableros ejecutivos y operativos.

### Dominio tecnico

- usuarios, roles y 2FA propios.
- JWT y endpoints de autenticacion.
- frontend aislado con rutas `/web`.
- servicio FastAPI para scoring.

## Decision de alcance para SIPET

### Entra al MVP del modulo SIPET

- catalogo de socios
- catalogo y flujo basico de creditos
- vista de ahorros/captacion
- campanas y prospectos
- scoring crediticio
- dashboard ejecutivo-operativo

### Entra despues del MVP

- mora temprana
- segmentacion inteligente programada
- reglas de asociacion de productos
- pipelines de mineria y procesos batch
- exportaciones avanzadas y drill-downs complejos

### No se migra como parte del modulo

- autenticacion propia de `intelicoop`
- registro publico, login, forgot password y JWT propios
- layouts y shell de frontend independientes
- docker y despliegue separado
- base de datos SQLite local de la app original

## Estructura objetivo en SIPET

Intelicoop debe quedar como modulo SIPET, no como sistema paralelo. La forma objetivo es:

- `intelicoop.py`: rutas, servicios y orquestacion del modulo
- `intelicoop.html`: vista principal del modulo
- `intelicoop.js`: interacciones del frontend
- `assets` minimos solo si son necesarios
- endpoints JSON integrados al backend principal de SIPET

Si el modulo crece, se puede dividir por archivos internos, pero siempre bajo el runtime y navegacion de SIPET.

## Reglas de integracion

- usar autenticacion y sesion de SIPET
- usar permisos y roles de SIPET; no conservar `authentication` como subsistema aparte
- usar layout base y menu de SIPET
- evitar mantener React/Vite como frontend independiente salvo que una parte concreta sea imposible de simplificar
- si el scoring sigue existiendo, exponerlo como servicio interno del modulo o como funcion del backend principal

## Mapeo inicial de componentes

### Conservar como fuente de migracion

- `backend/django_project/apps/socios`
- `backend/django_project/apps/creditos`
- `backend/django_project/apps/ahorros`
- `backend/django_project/apps/analitica`
- `backend/fastapi_service/app/core/scoring_model.py`
- `backend/fastapi_service/app/core/modelo_scoring.pkl`
- `frontend/src/pages/SociosList.jsx`
- `frontend/src/pages/CreditosList.jsx`
- `frontend/src/pages/AhorrosDashboard.jsx`
- `frontend/src/pages/CampaniasList.jsx`
- `frontend/src/pages/ProspectosList.jsx`
- `frontend/src/pages/Dashboards18.jsx`

### Conservar solo como referencia, no como destino final

- `frontend/src/App.jsx`
- `frontend/src/components/*`
- `frontend/src/pages/Login.jsx`
- `frontend/src/pages/Register.jsx`
- `frontend/src/pages/ForgotPassword.jsx`
- `backend/django_project/apps/authentication`
- `backend/fastapi_service/app/main.py`
- `data_pipelines/*`

## Riesgos detectados

- `intelicoop` trae modelos y roles propios que pueden chocar con entidades existentes de SIPET.
- parte del frontend actual depende de endpoints REST y estructura JWT que no deben sobrevivir tal cual.
- el dashboard 1.8 combina logica analitica y presentacion; conviene separarlo antes de migrarlo.
- hay funcionalidad de analitica avanzada que puede retrasar el MVP si se intenta portar completa desde el inicio.

## Entregables de Fase 1

- alcance funcional aprobado
- lista de funcionalidades MVP
- lista de funcionalidades diferidas
- lista de componentes que se eliminan o no se migran
- estructura objetivo del modulo SIPET

## Criterio de salida de Fase 1

La fase termina cuando quede aprobado que `intelicoop` en SIPET sera:

- un modulo de negocio y analitica
- sin autenticacion propia
- sin frontend independiente
- sin despliegue independiente
- con un MVP centrado en socios, creditos, ahorros, campanas, scoring y dashboard ejecutivo

## Fase 1 aprobada

Queda aprobado el siguiente alcance para continuar con Fase 2.

### Decision 1: alcance MVP

El MVP del modulo `intelicoop` en SIPET incluira:

- socios
- creditos
- ahorros
- campanas
- prospectos
- scoring crediticio
- dashboard ejecutivo-operativo en version simplificada

### Decision 2: alcance diferido

Se difiere para una etapa posterior:

- mora temprana
- segmentacion automatizada de socios
- reglas de asociacion de productos
- pipelines batch y automatizaciones de mineria
- exportaciones avanzadas
- drill-downs complejos por sucursal o ambito

### Decision 3: autenticacion y permisos

- no se migran login, register, forgot password ni JWT propios
- `intelicoop` usara autenticacion, sesion y menu de SIPET
- los roles propios de `authentication` se toman solo como referencia funcional, no como subsistema a conservar

### Decision 4: entidades de negocio

Para arrancar la migracion:

- `socios`, `creditos` y `ahorros` se manejaran primero como entidades propias del modulo `intelicoop`
- en Fase 2 se revisara si deben enlazarse con estructuras existentes de SIPET
- no se intentara unificar modelos con otros modulos en esta fase porque eso ampliaria demasiado el alcance

### Decision 5: scoring

- el scoring se conserva en `intelicoop` como capacidad propia del modulo
- no se movera todavia a una capa compartida de SIPET
- se migrara como servicio interno del backend principal, usando el modelo y la logica ya existentes como base

### Decision 6: dashboard

- el dashboard si entra al MVP
- entra en version simplificada
- se incluiran solo KPIs y vistas ejecutivas clave
- se excluyen en el MVP exportaciones complejas, filtros avanzados y drill-downs extensos

### Decision 7: frontend

- no se conserva el frontend React como aplicacion independiente
- las vistas se migraran al patron SIPET
- React queda solo como referencia de comportamiento y estructura visual

### Decision 8: criterio de congelamiento

Desde este punto, para Fase 2 se asume que:

- `intelicoop` sera un modulo SIPET
- no sera una app separada embebida
- el objetivo inmediato es migrar funcionalidad, no preservar su arquitectura original

## Siguiente fase

Fase 2: mapear archivo por archivo la migracion desde la estructura actual hacia la estructura final del modulo SIPET.

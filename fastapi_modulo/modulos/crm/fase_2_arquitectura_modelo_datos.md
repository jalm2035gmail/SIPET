# Fase 2: Arquitectura y Modelo de Datos — CRM SIPET

## Objetivo

Diseñar la arquitectura del módulo CRM dentro de SIPET, definir entidades, relaciones, endpoints y puntos de integración con el sistema existente.

---

## Estructura de archivos del módulo

```
fastapi_modulo/modulos/crm/
├── crm_db_models.py        # Modelos SQLAlchemy
├── crm_models.py           # Schemas Pydantic
├── crm_store.py            # Capa de acceso a datos (CRUD)
├── crm.py                  # Router FastAPI + lógica de rutas
├── crm.html                # Vista principal (patrón SIPET)
├── crm.js                  # Lógica JS del frontend
└── fase_2_arquitectura_modelo_datos.md
```

---

## Entidades principales y relaciones

### 1. `CrmContacto`
Persona física o moral que puede ser prospecto, cliente o excliente.

| Campo            | Tipo        | Descripción                              |
|------------------|-------------|------------------------------------------|
| id               | Integer PK  |                                          |
| nombre           | String(150) | Nombre completo o razón social           |
| email            | String(150) | Correo electrónico (único)               |
| telefono         | String(30)  |                                          |
| empresa          | String(150) | Empresa o institución                    |
| puesto           | String(100) | Cargo o rol del contacto                 |
| tipo             | String(20)  | prospecto / cliente / inactivo           |
| fuente           | String(50)  | Origen: web, referido, campaña, manual   |
| notas            | Text        | Notas generales                          |
| creado_en        | DateTime    |                                          |
| actualizado_en   | DateTime    |                                          |

---

### 2. `CrmOportunidad`
Proceso de venta o negociación asociado a un contacto.

| Campo            | Tipo        | Descripción                              |
|------------------|-------------|------------------------------------------|
| id               | Integer PK  |                                          |
| contacto_id      | FK → CrmContacto |                                     |
| nombre           | String(200) | Título de la oportunidad                 |
| etapa            | String(30)  | prospecto / negociacion / propuesta / cerrado_ganado / cerrado_perdido |
| valor_estimado   | Float       | Valor monetario estimado                 |
| probabilidad     | Integer     | % de cierre (0–100)                      |
| fecha_cierre_est | Date        | Fecha estimada de cierre                 |
| responsable      | String(100) | Usuario SIPET asignado                   |
| descripcion      | Text        |                                          |
| creado_en        | DateTime    |                                          |
| actualizado_en   | DateTime    |                                          |

---

### 3. `CrmActividad`
Registro de interacciones: llamadas, reuniones, correos, visitas.

| Campo            | Tipo        | Descripción                              |
|------------------|-------------|------------------------------------------|
| id               | Integer PK  |                                          |
| contacto_id      | FK → CrmContacto (nullable) |                       |
| oportunidad_id   | FK → CrmOportunidad (nullable) |                    |
| tipo             | String(30)  | llamada / reunion / email / visita / tarea |
| titulo           | String(200) |                                          |
| descripcion      | Text        |                                          |
| fecha            | DateTime    | Fecha/hora de la actividad               |
| completada       | Boolean     | default False                            |
| responsable      | String(100) | Usuario SIPET asignado                   |
| creado_en        | DateTime    |                                          |

---

### 4. `CrmNota`
Nota libre asociada a un contacto u oportunidad.

| Campo            | Tipo        | Descripción                              |
|------------------|-------------|------------------------------------------|
| id               | Integer PK  |                                          |
| contacto_id      | FK → CrmContacto (nullable) |                       |
| oportunidad_id   | FK → CrmOportunidad (nullable) |                    |
| contenido        | Text        |                                          |
| autor            | String(100) | Usuario SIPET que la creó                |
| creado_en        | DateTime    |                                          |

---

### 5. `CrmCampania`
Campaña comercial o de comunicación.

| Campo            | Tipo        | Descripción                              |
|------------------|-------------|------------------------------------------|
| id               | Integer PK  |                                          |
| nombre           | String(150) |                                          |
| tipo             | String(50)  | email / llamada / evento / promocion     |
| estado           | String(20)  | borrador / activa / finalizada           |
| fecha_inicio     | Date        |                                          |
| fecha_fin        | Date        |                                          |
| descripcion      | Text        |                                          |
| creado_en        | DateTime    |                                          |

---

### 6. `CrmContactoCampania` (relación N:M)
Contactos asociados a una campaña.

| Campo            | Tipo        | Descripción                              |
|------------------|-------------|------------------------------------------|
| id               | Integer PK  |                                          |
| contacto_id      | FK → CrmContacto |                                     |
| campania_id      | FK → CrmCampania |                                     |
| estado           | String(20)  | pendiente / contactado / convertido      |

---

## Diagrama de relaciones

```
CrmContacto (1) ──────< CrmOportunidad (N)
CrmContacto (1) ──────< CrmActividad   (N)
CrmContacto (1) ──────< CrmNota        (N)
CrmOportunidad (1) ───< CrmActividad   (N)
CrmOportunidad (1) ───< CrmNota        (N)
CrmContacto (N) >────< CrmCampania     (N)  [via CrmContactoCampania]
```

---

## Endpoints planeados

### Contactos
| Método | Ruta                          | Acción                  |
|--------|-------------------------------|-------------------------|
| GET    | /crm/                         | Vista principal HTML    |
| GET    | /crm/api/contactos            | Listar contactos        |
| POST   | /crm/api/contactos            | Crear contacto          |
| PUT    | /crm/api/contactos/{id}       | Actualizar contacto     |
| DELETE | /crm/api/contactos/{id}       | Eliminar contacto       |

### Oportunidades
| Método | Ruta                            | Acción                  |
|--------|---------------------------------|-------------------------|
| GET    | /crm/api/oportunidades          | Listar oportunidades    |
| POST   | /crm/api/oportunidades          | Crear oportunidad       |
| PUT    | /crm/api/oportunidades/{id}     | Actualizar oportunidad  |
| DELETE | /crm/api/oportunidades/{id}     | Eliminar oportunidad    |

### Actividades
| Método | Ruta                          | Acción                  |
|--------|-------------------------------|-------------------------|
| GET    | /crm/api/actividades          | Listar actividades      |
| POST   | /crm/api/actividades          | Crear actividad         |
| PUT    | /crm/api/actividades/{id}     | Actualizar actividad    |
| DELETE | /crm/api/actividades/{id}     | Eliminar actividad      |

### Notas
| Método | Ruta                          | Acción                  |
|--------|-------------------------------|-------------------------|
| POST   | /crm/api/notas                | Crear nota              |
| DELETE | /crm/api/notas/{id}           | Eliminar nota           |

### Campañas
| Método | Ruta                          | Acción                  |
|--------|-------------------------------|-------------------------|
| GET    | /crm/api/campanias            | Listar campañas         |
| POST   | /crm/api/campanias            | Crear campaña           |
| PUT    | /crm/api/campanias/{id}       | Actualizar campaña      |

---

## Integración con SIPET

- **Autenticación**: usa `auth_session` cookie y helpers de sesión existentes en `main.py`.
- **Permisos**: se integrará al sistema de roles (DEFAULT_SYSTEM_ROLES) con permiso `crm_acceso`.
- **Base de datos**: hereda de `fastapi_modulo.db.Base`, usa `SessionLocal` para sesiones.
- **Layout**: extiende `base.html` SIPET con los estilos y componentes DaisyUI existentes.
- **Menú**: se registrará como ítem de navegación en el sidebar principal.
- **Migraciones**: se añadirán en `alembic/versions/` con prefijo de fecha.

---

## Convenciones de nomenclatura

- Tablas: `crm_*` (ej. `crm_contactos`, `crm_oportunidades`)
- Clases SQLAlchemy: `Crm*` (ej. `CrmContacto`, `CrmOportunidad`)
- Schemas Pydantic: `Crm*Schema` / `Crm*Create` / `Crm*Update`
- Router prefix: `/crm`
- Archivos: `crm_*.py`

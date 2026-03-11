# Módulo CRM — SIPET

## Descripción

Gestión de relaciones con clientes: contactos, oportunidades, actividades, notas y campañas de comunicación.

---

## Estructura de archivos

```
fastapi_modulo/modulos/crm/
├── crm_db_models.py        # Modelos SQLAlchemy (6 tablas)
├── crm_models.py           # Esquemas Pydantic (validación de entrada)
├── crm_store.py            # Capa de acceso a datos (CRUD)
├── crm.py                  # Router FastAPI (24 rutas)
├── crm.html                # Vista principal (plantilla Jinja2)
├── crm.js                  # Lógica frontend (IIFE, Vanilla JS)
└── test_crm_phase6.py      # Suite de tests (25 casos)
```

---

## Entidades y tablas

| Tabla               | Descripción                                    |
|---------------------|------------------------------------------------|
| `crm_contactos`     | Personas o empresas (prospecto/cliente/inactivo)|
| `crm_oportunidades` | Deals en pipeline (5 etapas)                   |
| `crm_actividades`   | Llamadas, reuniones, tareas — con flag completada |
| `crm_notas`         | Texto libre asociado a contacto u oportunidad  |
| `crm_campanias`     | Campañas de email/SMS/push                     |
| `crm_contacto_campania` | Relación N:M contacto ↔ campaña           |

Las tablas se crean automáticamente en el primer uso via `ensure_crm_schema()`.

---

## Permisos

| Rol                              | Acceso |
|----------------------------------|--------|
| `administrador` / `superadmin`   | Sí (bypass automático) |
| Usuario con acceso `CRM`         | Sí |
| Cualquier otro usuario           | 403 |

Para otorgar acceso a un colaborador: **Empleados → perfil → Acceso a módulos → activar CRM**.

---

## Rutas HTTP

### Vista
| Método | Ruta   | Descripción              |
|--------|--------|--------------------------|
| GET    | `/crm` | Vista principal del módulo |

### API — Resumen
| GET | `/api/crm/resumen` | KPIs generales del dashboard |

### API — Contactos
| GET    | `/api/crm/contactos`         | Lista (filtro opcional `?tipo=`) |
| GET    | `/api/crm/contactos/{id}`    | Detalle |
| POST   | `/api/crm/contactos`         | Crear (201) — email único (409 si duplicado) |
| PUT    | `/api/crm/contactos/{id}`    | Actualizar (campos parciales) |
| DELETE | `/api/crm/contactos/{id}`    | Eliminar |

### API — Oportunidades
| GET    | `/api/crm/oportunidades`       | Lista (filtro `?etapa=`) |
| GET    | `/api/crm/oportunidades/{id}`  | Detalle |
| POST   | `/api/crm/oportunidades`       | Crear |
| PUT    | `/api/crm/oportunidades/{id}`  | Actualizar etapa / valor |
| DELETE | `/api/crm/oportunidades/{id}`  | Eliminar |

### API — Actividades
| GET    | `/api/crm/actividades`        | Lista (filtro `?completada=false`) |
| POST   | `/api/crm/actividades`        | Crear |
| PUT    | `/api/crm/actividades/{id}`   | Actualizar / marcar completada |
| DELETE | `/api/crm/actividades/{id}`   | Eliminar |

### API — Notas
| GET    | `/api/crm/notas`        | Lista (filtro `?contacto_id=` / `?oportunidad_id=`) |
| POST   | `/api/crm/notas`        | Crear |
| DELETE | `/api/crm/notas/{id}`   | Eliminar |

### API — Campañas
| GET    | `/api/crm/campanias`                      | Lista |
| POST   | `/api/crm/campanias`                      | Crear |
| PUT    | `/api/crm/campanias/{id}`                | Actualizar |
| DELETE | `/api/crm/campanias/{id}`                | Eliminar |
| GET    | `/api/crm/campanias/{id}/contactos`      | Contactos de una campaña |
| POST   | `/api/crm/campanias/contactos`           | Asociar contacto a campaña |

---

## Etapas de oportunidad

`prospecto` → `negociacion` → `propuesta` → `cerrado_ganado` / `cerrado_perdido`

## Estados de campaña

`borrador` → `activa` → `finalizada`

---

## Tests

```bash
python -m pytest fastapi_modulo/modulos/crm/test_crm_phase6.py -v
```

25 casos: permisos, CRUD por entidad, resumen/dashboard, filtros, relaciones.

---

## Deploy

El módulo se incluye automáticamente en el `rsync` de `deploy-polo.sh` — no requiere pasos adicionales.

Las 6 tablas CRM se crean en el primer request que llega al módulo (`ensure_crm_schema()` en `crm_store._db()`), por lo que no hay migración Alembic requerida.

```bash
# Verificar en servidor tras deploy
ssh administrator@38.247.146.242 "sqlite3 /var/lib/sipet/data/strategic_planning.db '.tables' | tr ' ' '\n' | grep crm"
# Debe listar: crm_actividades, crm_campanias, crm_contacto_campania, crm_contactos, crm_notas, crm_oportunidades
```

## Monitoreo

Puntos a revisar en operación:

| Indicador | Cómo verificarlo |
|-----------|-----------------|
| Módulo accesible | GET `/crm` devuelve 200 con sesión válida |
| Tablas creadas | Query `.tables` en SQLite (ver arriba) |
| Tests pasan post-deploy | `python -m pytest fastapi_modulo/modulos/crm/test_crm_phase6.py -v` |
| Errores 500 en duplicados | Deben retornar 409, no stack trace |

---

## Registro de cambios

| Fecha      | Descripción                                   |
|------------|-----------------------------------------------|
| 2026-03-06 | Implementación completa (fases 1–8) — 24 rutas, 25 tests |

# 2.1 Inventario Formal de Fuentes

## Fuentes internas actuales (detectadas en la app)

| Dominio | Entidad/Tabla | Ubicacion en codigo | Owner propuesto | Criticidad |
|---|---|---|---|---|
| Socios | `socios` | `backend/django_project/apps/socios/models.py` | Lider Comercial | Alta |
| Creditos | `creditos` | `backend/django_project/apps/creditos/models.py` | Lider Credito | Alta |
| Pagos | `historial_pagos` | `backend/django_project/apps/creditos/models.py` | Lider Cobranza | Alta |
| Ahorros | `cuentas` | `backend/django_project/apps/ahorros/models.py` | Lider Ahorros | Media |
| Transacciones | `transacciones` | `backend/django_project/apps/ahorros/models.py` | Lider Ahorros | Media |
| Usuarios/roles | `user_profiles` | `backend/django_project/apps/authentication/models.py` | Seguridad TI | Media |

## Fuentes externas (pendientes de integracion)

| Fuente | Uso objetivo | Estado |
|---|---|---|
| Buro de credito | Variables de riesgo y score externo | Pendiente |
| Datos demograficos | Variables de contexto | Pendiente |
| Indicadores sectoriales | Ajuste de politicas | Pendiente |

## Campos clave de integracion
- `id_socio`
- `id_credito`
- `fecha_corte`

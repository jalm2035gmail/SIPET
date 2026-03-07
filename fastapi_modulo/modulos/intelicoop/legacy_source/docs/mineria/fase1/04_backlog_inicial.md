# Backlog Inicial Priorizado - Fase 1

## Prioridad Alta

### US-ML-001 - Definir contrato de scoring
- Como equipo de originacion, quiero un contrato API estable de scoring para consumirlo en el flujo de credito.
- Criterios:
  - Definir request/response oficial.
  - Definir codigos de error.
  - Definir version inicial del contrato.

### US-ML-002 - Definir diccionario de variables minimas
- Como equipo de riesgo, quiero un diccionario de variables para asegurar consistencia de datos.
- Criterios:
  - Variable, tipo, rango, obligatoriedad.
  - Regla de validacion por variable.

### US-ML-003 - Definir etiqueta de incumplimiento
- Como equipo de riesgo, quiero una definicion oficial de incumplimiento (30/60/90) para entrenar modelos.
- Criterios:
  - Regla de negocio documentada.
  - Ventana temporal aprobada.

### US-ML-004 - Definir permisos y consumidores
- Como equipo tecnico, quiero mapear consumidores y permisos por rol para proteger datos.
- Criterios:
  - Mapa de endpoints por rol.
  - Restricciones para auditor (solo lectura) y superadmin (total).

## Prioridad Media

### US-ML-005 - Definir criterio de exito del MVP
- Criterios:
  - KPI tecnico minimo (latencia y disponibilidad).
  - KPI negocio minimo (incumplimiento, aprobacion).

### US-ML-006 - Definir estrategia de trazabilidad
- Criterios:
  - Campos para version de modelo.
  - Campos para identificar solicitud y socio.
  - Politica de retencion de logs.

## Prioridad Baja

### US-ML-007 - Definir lineamientos de reglas de asociacion
- Criterios:
  - Umbrales objetivo de soporte/confianza/lift.
  - Casos de uso comerciales objetivo.

### US-ML-008 - Definir lineamientos iniciales de monitoreo de drift
- Criterios:
  - Variables a monitorear.
  - Frecuencia de revision.
  - Umbrales de alerta.

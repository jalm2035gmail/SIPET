# Documento de Alcance - Modulo Mineria de Datos

## 1. Objetivo
Definir el alcance funcional y tecnico del modulo de Mineria de Datos enfocado en cartera de credito, para habilitar decisiones operativas sobre riesgo, cobranza y segmentacion comercial.

## 2. Alcance inicial (Fase 1 a Fase 3)
- Caso 1: Scoring de originacion (tiempo real).
- Caso 2: Segmentacion de socios (batch).
- Integracion con front de credito para consulta de score.
- Integracion con backend para almacenamiento de solicitudes de credito.

## 3. Fuera de alcance inicial
- Motor completo de mora temprana 30/60/90.
- Reglas de asociacion (Apriori/FP-Growth) en produccion.
- Reentrenamiento automatico y monitoreo de drift operativo.

## 4. Stakeholders
- Patrocinador: Direccion general / Comite de riesgo.
- Product owner: Lider funcional de credito.
- Responsables funcionales: credito, cobranza, comercial.
- Responsables tecnicos: backend Django, servicio ML FastAPI, datos/pipelines.

## 5. Restricciones
- Seguridad: acceso por roles (auditor, jefe_departamento, administrador, superadmin).
- Cumplimiento: datos personales y financieros deben tratarse con minimo privilegio.
- Operacion: el scoring de originacion debe responder en linea para no bloquear flujo comercial.

## 6. Supuestos de trabajo
- Las fuentes internas principales estan disponibles en el backend actual: socios, creditos, pagos, ahorros, transacciones.
- El endpoint de scoring seguira operando en FastAPI con consumo desde frontend.
- Las decisiones finales de aprobacion se mantienen en negocio.

## 7. Criterios de aceptacion de Fase 1
- Alcance validado por negocio y tecnologia.
- Casos de uso y KPIs acordados.
- RACI aprobado.
- Backlog inicial priorizado y estimado en alto nivel.

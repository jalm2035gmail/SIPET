# Taller de Arranque - Fase 1.1

## Objetivo
Establecer alcance, responsables y restricciones del modulo de Mineria de Datos para cartera de credito.

## Participantes
- Sponsor (Direccion general)
- Product Owner (Credito)
- Lider de Riesgo
- Lider de Cobranza
- Lider Comercial
- Tech Lead
- Backend (Django/FastAPI)
- Data/Pipelines

## Acuerdos
- Alcance inicial: scoring de originacion y segmentacion de socios.
- Alcance siguiente: mora temprana y reglas de asociacion.
- Prioridad operativa: no frenar originacion por latencia de scoring.

## Restricciones identificadas
- Seguridad por roles y principio de minimo privilegio.
- Trazabilidad obligatoria de inferencias y version de modelo.
- Evitar uso de datos sensibles no necesarios.

## Riesgos
- Calidad de datos historicos insuficiente para mora temprana.
- Falta de versionado formal en artefactos ML.
- Dependencia de fuentes externas (buro) no conectadas.

## Salidas del taller
- Alcance confirmado.
- RACI definido.
- Backlog inicial listo para refinamiento tecnico.

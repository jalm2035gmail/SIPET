# Documento Funcional IA - SIPET
avance (actualizado al 2026-03-01)






## 1. Objetivo
Definir el alcance funcional para incorporar capacidades de IA en SIPET de forma gradual, segura y medible, alineadas al contexto actual del sistema (plan estrategico, POA, presupuesto, reportes, notificaciones y control por roles).

Este documento adapta y aterriza el contenido de [`ia.txt`](./ia.txt) a un plan implementable.

## 2. Alcance inicial
Se implementara IA en tres frentes:

1. Asistencia de redaccion y estructuracion estrategica.
2. Analitica inteligente para riesgo/seguimiento operativo.
3. Generacion automatica de resumentes y reportes ejecutivos.

Fuera de alcance inicial:

1. Modelos de riesgo crediticio/morosidad con datos financieros externos no consolidados.
2. Recomendador comercial de productos para socios.
3. Automatizaciones regulatorias con scraping externo sin gobernanza aprobada.

## 3. Principios funcionales
1. **Humano en control**: la IA sugiere, el usuario decide.
2. **Trazabilidad completa**: toda sugerencia queda auditada.
3. **Seguridad por rol**: IA respetara permisos existentes.
4. **Despliegue incremental**: primero valor rapido, luego capacidades avanzadas.
5. **Sin bloqueo operativo**: si IA falla, SIPET sigue funcionando.

## 4. Mapa de funcionalidades IA (adaptado de ia.txt)

### 4.1 Nivel/Fase Asistencial (alto retorno inmediato)
1. Sugerencia de OKRs/KPIs desde objetivos estrategicos.
2. Mejora de redaccion en:
   - Ejes estrategicos
   - Objetivos
   - Actividades POA
   - Hitos
3. Clasificacion sugerida actividad -> eje/objetivo.
4. Resumen automatico de texto largo (actas/documentos/subidas HTML/PDF).

### 4.2 Nivel/Fase Analitica Operativa
1. Deteccion de riesgo en POA:
   - Actividades sin responsable
   - Actividades atrasadas
   - Entregables pendientes de revision por mas de X dias
2. Recomendaciones de accion:
   - Reasignar responsable
   - Ajustar fechas
   - Escalar aprobaciones pendientes
3. Concentracion de carga por usuario/departamento (complemento de tablero).

### 4.3 Nivel/Fase Ejecutiva y Conversacional
1. Reporte ejecutivo en lenguaje natural por periodo/eje/departamento.
2. Consultas en lenguaje natural sobre datos del plan/POA:
   - "Que actividades vencen esta semana sin responsable?"
   - "Cual eje tiene mayor riesgo?"
3. Asistente contextual (RAG) sobre documentos institucionales.

### 4.4 Nivel/Fase Predictiva Avanzada (condicionada)
1. Predicciones de cumplimiento por objetivo/actividad.
2. Modelos de tendencia presupuestal.
3. Casos de negocio externo (morosidad/churn/recomendador) solo cuando exista dataset unificado y gobernado.

## 5. Roles y permisos IA
La IA debe heredar y respetar el modelo actual de SIPET.

1. `superadministrador` / `administrador`:
   - Configuran parametros IA.
   - Ejecutan funciones globales (resumen ejecutivo, reportes masivos).
   - Habilitan modulos IA por area.
2. Usuarios operativos:
   - Pueden solicitar sugerencias sobre sus formularios permitidos.
   - No pueden modificar configuracion global IA.
3. Restricciones especiales:
   - Estados de actividad y aprobaciones siguen reglas actuales (dueno/lider/admin).
   - IA no fuerza cambios de estatus sin confirmacion humana.

## 6. Flujos funcionales clave

### 6.1 Sugerencia de KPI desde objetivo
1. Usuario abre objetivo estrategico.
2. Clic en "Sugerir con IA".
3. Sistema envia contexto (nombre, descripcion, eje, hito, fechas).
4. IA devuelve propuestas estructuradas:
   - Nombre KPI
   - Proposito
   - Formula
   - Periodicidad
   - Estandar + valor de referencia
5. Usuario puede:
   - Aplicar
   - Editar antes de guardar
   - Descartar
6. Se registra auditoria.

### 6.2 Alerta de riesgo POA
1. Proceso programado analiza actividades/subactividades.
2. Calcula riesgo por reglas + evaluacion IA.
3. Publica alertas en notificaciones y tablero.
4. Usuario responsable ve recomendacion accionable.

### 6.3 Resumen ejecutivo
1. Admin selecciona rango y filtro (eje/departamento/region/usuario).
2. IA genera resumen narrativo con:
   - avance
   - riesgos
   - hitos logrados
   - pendientes criticos
3. Usuario exporta a documento (HTML/PDF/DOC).

## 7. Requerimientos funcionales (RF)
1. RF-IA-01: El sistema debe permitir solicitar sugerencias IA desde formularios de plan y POA.
2. RF-IA-02: Toda respuesta IA debe poder aplicarse parcialmente.
3. RF-IA-03: Debe existir bitacora de interacciones IA por usuario.
4. RF-IA-04: Debe existir control por rol para cada funcionalidad IA.
5. RF-IA-05: Debe existir un modo "solo sugerencia" (sin auto-guardado).
6. RF-IA-06: El sistema debe soportar tareas asincronas para reportes IA pesados.
7. RF-IA-07: Debe mostrarse mensaje claro cuando IA no este disponible.

## 8. Requerimientos no funcionales (RNF)
1. RNF-IA-01: Tiempo respuesta sugerencias cortas <= 8 segundos promedio.
2. RNF-IA-02: Tareas largas en background con estado (pendiente/en proceso/completado/error).
3. RNF-IA-03: Registro de costo estimado por llamada IA.
4. RNF-IA-04: Sanitizacion de contenido para evitar inyeccion en HTML.
5. RNF-IA-05: No exponer secretos/API keys al frontend.

## 9. Arquitectura funcional propuesta
1. Nuevo modulo backend: `fastapi_modulo/modulos/ia/`
2. Componentes:
   - `ia_router.py` (endpoints)
   - `ia_service.py` (orquestacion)
   - `prompt_templates.py` (prompts versionados)
   - `providers/` (ChatGPT/OpenAI, DeepSeek, Claude, local)
   - `audit.py` (bitacora/costos)
3. Procesamiento asincrono:
   - Celery + Redis para tareas pesadas.
4. Persistencia:
   - Tabla `ia_interactions`
   - Tabla `ia_jobs`
   - Tabla `ia_feature_flags`

## 9.1 Implementacion de modelo IA (multi-proveedor)
SIPET debe implementar una capa desacoplada de proveedor para poder usar ChatGPT, DeepSeek u otro modelo sin rehacer logica de negocio.

1. Proveedores objetivo:
   - `chatgpt` (OpenAI API)
   - `deepseek` (API compatible OpenAI o SDK oficial)
   - `otro` (Claude, modelo local, proveedor corporativo)
2. Estrategia:
   - Un contrato unico de entrada/salida en `ia_service.py`.
   - Adaptadores por proveedor en `providers/`.
   - Seleccion de proveedor por configuracion (`.env` + ajustes).
3. Configuracion minima sugerida:
   - `AI_PROVIDER=chatgpt|deepseek|otro`
   - `AI_MODEL=<modelo_default>`
   - `AI_API_KEY=<secreto>`
   - `AI_BASE_URL=<url_opcional_para_proveedores_compatibles>`
   - `AI_TIMEOUT_SECONDS=30`
   - `AI_MAX_TOKENS=1200`
4. Fallback:
   - Si falla proveedor primario, usar secundario configurable.
   - Registrar en auditoria proveedor usado y causa del fallback.
5. Criterios de seleccion de modelo:
   - Calidad de salida (utilidad para negocio)
   - Costo por uso
   - Latencia
   - Capacidad para espanol y contexto institucional
   - Politicas de seguridad y retencion
6. Recomendacion operativa:
   - Empezar con `chatgpt` como baseline y habilitar `deepseek` como opcion alternativa en entorno de pruebas/piloto.
   - Mantener prompts y validaciones iguales para poder comparar resultados entre modelos.

## 10. Endpoints funcionales sugeridos (v1)
1. `POST /api/ia/suggest/kpi`
2. `POST /api/ia/suggest/objective-text`
3. `POST /api/ia/suggest/activity-text`
4. `POST /api/ia/classify/activity`
5. `POST /api/ia/summarize/document`
6. `GET /api/ia/poa/risk-summary`
7. `POST /api/ia/reports/executive`
8. `GET /api/ia/jobs/{job_id}`

## 11. Estructura de datos minima (propuesta)

### 11.1 `ia_interactions`
1. `id`
2. `created_at`
3. `user_id` / `username`
4. `feature_key`
5. `input_payload` (JSON)
6. `output_payload` (JSON)
7. `model_name`
8. `tokens_in`
9. `tokens_out`
10. `estimated_cost`
11. `status`
12. `error_message`

### 11.2 `ia_jobs`
1. `id`
2. `created_at`
3. `created_by`
4. `job_type`
5. `status`
6. `progress_pct`
7. `result_payload`
8. `error_message`

## 12. Fases de desarrollo

## Fase 0 - Preparacion (1 semana)
Objetivo: dejar base tecnica lista.

1. ✅ Definir proveedor IA y variables de entorno (chatgpt/deepseek/otro).
2. ✅ Crear modulo `ia/` y contratos de respuesta.
3. ✅ Crear tablas de auditoria.
4. ✅ Implementar feature flags por rol/modulo.
5. ✅ Implementar adaptadores de proveedor y mecanismo de fallback.

Entregables:
1. ✅ Endpoints mock operativos.
2. ✅ Logging y auditoria basica.
3. ✅ Seleccion dinamica de proveedor IA desde configuracion.

## Fase 1 - Asistencia inteligente (2 a 3 semanas)
Objetivo: valor visible inmediato.

1. Sugerencia/redaccion para ejes, objetivos, actividades, KPIs.
2. Botones "Sugerir con IA" en formularios.
3. Aplicar/editar/descartar sugerencias.

Entregables:
1. Flujo funcional en UI.
2. Auditoria completa por sugerencia.

KPIs fase:
1. >= 50% de usuarios piloto usan sugerencias.
2. Reduccion de tiempo de captura >= 25%.

## Fase 2 - Riesgo y seguimiento POA (2 a 4 semanas)
Objetivo: mejorar control operativo.

1. Motor de riesgo (reglas + IA).
2. Alertas en notificaciones.
3. Resumen de riesgos por eje/departamento/usuario.
4. Recomendaciones de accion.

Entregables:
1. Tablero de riesgo IA en POA/BSC.
2. Alertas priorizadas.

KPIs fase:
1. Reduccion de actividades atrasadas >= 15%.
2. Reduccion de actividades sin responsable >= 30%.

## Fase 3 - Reporte ejecutivo IA (2 a 3 semanas)
Objetivo: acelerar toma de decisiones.

1. Generacion narrativa automatica por filtro.
2. Exportacion a documento.
3. Versionado de reportes generados.

Entregables:
1. ✅ Reporte ejecutivo IA descargable.
2. ✅ Historial de reportes por periodo.

## Fase 4 - Conversacional y RAG (3 a 5 semanas)
Objetivo: consulta inteligente sobre contenido institucional.

1. Indexacion documental (politicas, actas, planes).
2. Chat contextual con fuentes citadas.
3. Control de acceso por documentos.

Entregables:
1. ✅ Asistente contextual funcional.
2. ✅ Evidencia de trazabilidad por respuesta.

## Fase 5 - Predictivo avanzado (condicionado)
Objetivo: modelos de prediccion maduros.

1. Prediccion de cumplimiento POA/objetivos.
2. Tendencias presupuestales.
3. Casos externos (morosidad/churn) solo con data governance aprobado.

Precondiciones:
1. Datos historicos limpios y suficientes.
2. Etiquetado de calidad.
3. Validacion de sesgo y explicabilidad.

## 13. Riesgos y mitigaciones
1. Riesgo: respuestas no confiables.
   - Mitigacion: modo sugerencia + validacion humana obligatoria.
2. Riesgo: costo por uso IA.
   - Mitigacion: cuotas por rol, caching, prompts compactos.
3. Riesgo: fuga de datos sensibles.
   - Mitigacion: anonimizar antes de enviar, politicas de retencion.
4. Riesgo: baja adopcion.
   - Mitigacion: pilotos por area + capacitacion + UX simple.
5. Riesgo: dependencia de un solo proveedor/modelo.
   - Mitigacion: arquitectura multi-proveedor + fallback + comparativas trimestrales.

## 14. Criterios de aceptacion generales
1. Todas las funciones IA respetan permisos actuales.
2. Toda accion IA queda auditada.
3. UI permite confirmar antes de guardar.
4. Falla de proveedor IA no rompe funcionalidad core.
5. Se puede desactivar IA por feature flag sin desplegar de nuevo.

## 15. Backlog sugerido (primer sprint IA)
1. ✅ Crear modulo `ia` + endpoint health IA.
2. ✅ Implementar `suggest/objective-text`.
3. ✅ Agregar boton "Sugerir con IA" en objetivo estrategico.
4. ✅ Guardar auditoria de input/output.
5. ✅ Agregar timeout, reintentos y manejo de errores.
6. ✅ Documentar politicas de uso y costos.

## 16. Evidencia real implementada
1. Multi-proveedor robusto:
   - Contrato unico en `fastsipet_modulo/modulos/ia/providers/base.py`.
   - Adaptadores operativos: OpenAI, DeepSeek, Ollama.
   - Fallback/reintentos/backoff/costos en `fastsipet_modulo/modulos/ia/ia_service.py`.
2. Riesgo POA + alertas IA:
   - Endpoints: `/api/v1/ia/poa/risk-summary`, `/api/v1/ia/poa/risk-alerts/publish`, `/api/v1/ia/poa/risk-alerts`.
3. Reporte ejecutivo versionado:
   - Endpoints: `/api/v1/ia/reports/executive/generate`, `/history`, `/history/{id}`, `/download`.
4. RAG conversacional:
   - Endpoints: `/api/v1/ia/rag/index-documents`, `/index-status`, `/chat`, `/conversations`.
   - UI conectada en `Conversaciones`.
5. Trazabilidad y operacion (frontend):
   - Endpoints: `/api/ia/audit/feed`, `/api/ia/audit/summary`.
   - Panel visible en `Ajustes IA`.
6. Pruebas de integracion (evidencia):
   - `tests/test_ia_audit.py`.
   - Resultado local: `3 passed`.

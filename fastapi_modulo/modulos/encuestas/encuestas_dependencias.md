# Matriz de dependencias del modulo Encuestas

| Dependencia | Estado en Encuestas | Uso actual | Cambio aplicado / criterio |
| --- | --- | --- | --- |
| `fastapi` | Activa | Router HTML/API y respuestas de exportación | Se mantiene como MAIN del módulo |
| `pydantic` | Activa | Modelos de entrada/salida en router | Se mantiene |
| `sqlalchemy` | Activa | Persistencia completa de campañas, respuestas, resultados y automatización | Se mantiene |
| `openpyxl` | Activa | Escritura de libros Excel | Se mantiene en exportación `.xlsx` |
| `pandas` | Activa | `DataFrame` para exportaciones y comparativos/filtros de analytics | Integrada en este ajuste |
| `reportlab` | Activa | Exportación PDF con resumen, filtros, segmentos y comparativo | Integrada en este ajuste |
| `httpx` | Activa | backendhook opcional `response_submitted` | Integrada en este ajuste |
| `celery` | Activa con fallback | Cola de automatización y backendhooks si hay broker configurado | Si no hay broker, el módulo ejecuta localmente |
| `redis` | Activa por configuración | Broker/backend preferente para `Celery` y verificación de disponibilidad | Se detecta por `REDIS_URL` o variables de `ENCUESTAS_CELERY_*` |
| `Chart.js` | Activa | Resumen gráfico de resultados desde vendor local | Se mantiene |
| `@fortawesome/fontawesome-free` | Activa global | Iconografía del sidebar y shell general | Se mantiene |
| `tailwindcss` | Activa global | Build global de estilos del proyecto | `encuestas` usa CSS namespaced propio; no conviene forzarlo aquí |
| `daisyui` | No prioritaria | Sin uso directo en Encuestas | No se integra para evitar mezclar DSL visual con CSS local |
| `grapesjs` | No prioritaria | Sin uso directo en Encuestas | No se integra porque el constructor actual no es WYSIWYG |
| `numpy` | No prioritaria | Sin uso directo en Encuestas | No aporta valor inmediato al flujo actual |
| `scikit-learn` | No prioritaria | Sin uso directo en Encuestas | No aplica sin modelos predictivos específicos del módulo |
| `joblib` | No prioritaria | Sin uso directo en Encuestas | No aplica mientras no existan artefactos de modelos |
| `Pillow` | No prioritaria | Sin uso directo en Encuestas | No aporta al flujo actual |

## Criterio

El objetivo no es forzar el uso de todas las librerías instaladas, sino aprovechar al máximo las útiles para `encuestas` sin introducir complejidad artificial. En este ajuste se priorizaron las que aportan valor directo al negocio:

- `pandas` para estructurar datasets de resultados, comparativos y filtros
- `reportlab` para reportes PDF descargables
- `httpx` para integración saliente por backendhook
- `celery` + `redis` para automatización y backendhooks asíncronos con fallback local

## Configuración nueva útil

Se puede activar backendhook por encuesta usando `publication_rules_json` o `settings_json`:

```json
{
  "backendhook_url": "https://tu-endpoint.example/backendhooks/encuestas",
  "backendhook_events": ["response_submitted"],
  "backendhook_timeout_seconds": 5
}
```

## Configuración opcional de background jobs

```bash
export REDIS_URL=redis://localhost:6379/0
export ENCUESTAS_CELERY_BROKER_URL=$REDIS_URL
export ENCUESTAS_CELERY_RESULT_BACKEND=$REDIS_URL
export ENCUESTAS_CELERY_QUEUE=encuestas_automation
```

Worker sugerido:

```bash
celery -A fastapi_modulo.modulos.encuestas.modelos.encuestas_tasks.celery_app worker -Q encuestas_automation -l info
```

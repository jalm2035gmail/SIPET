# Segmentacion Inteligente 1.4

Estado:
- Segmentacion por reglas (umbrales): completado tecnicamente.
- Segmentacion estadistica (clustering): completado tecnicamente.
- Exposicion por API de ejecucion: completado tecnicamente.
- Integracion en orquestacion (cron/pipeline): completado tecnicamente.
- Umbrales oficiales versionados con negocio: completado tecnicamente.
- Acciones/campanas automaticas por segmento: completado tecnicamente.

Comando:
- `python manage.py segmentacion_inteligente_socios_1_4 --metodo reglas`
- `python manage.py segmentacion_inteligente_socios_1_4 --metodo clustering --clusters 5`
- `python manage.py orquestar_pipelines_fase5 --fecha-corte YYYY-MM-DD --run-id daily_0215`
- `python manage.py definir_umbrales_segmentacion_1_4 --thresholds-version segmentacion_1_4_v1 --aprobado-por comite_negocio`
- `python manage.py activar_acciones_campanas_segmentos_1_4 --autogenerar-segmentacion`

API:
- `POST /api/analitica/ml/segmentacion-inteligente/ejecutar/`

Artefactos:
- `docs/mineria/customer_intelligence/01_segmentacion_inteligente_resumen.csv`
- `docs/mineria/customer_intelligence/01_segmentacion_inteligente_socios.csv`
- `docs/mineria/customer_intelligence/01_segmentacion_inteligente.md`
- `docs/mineria/customer_intelligence/02_umbrales_segmentacion_oficial_v1.json`
- `docs/mineria/customer_intelligence/02_umbrales_segmentacion_oficial.csv`
- `docs/mineria/customer_intelligence/02_umbrales_segmentacion_oficial.md`
- `docs/mineria/customer_intelligence/03_resumen_acciones_segmentos.csv`
- `docs/mineria/customer_intelligence/03_acciones_campanas_segmentos.csv`
- `docs/mineria/customer_intelligence/03_acciones_campanas_segmentos.md`

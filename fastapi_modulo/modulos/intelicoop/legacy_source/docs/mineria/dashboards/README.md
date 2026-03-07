# Dashboards Ejecutivos y Operativos 1.8

Objetivo:
- Entregar visibilidad ejecutiva y operativa para Consejo, Gerencia, jefaturas y ejecutivos.

Comando:
- `python manage.py dashboards_ejecutivos_operativos_1_8`
- `python manage.py actualizar_dashboards_programado_1_8`
- `python manage.py cerrar_uat_dashboards_1_8`

Dashboards:
- Salud de cartera (vigente/vencida, IMOR, vintage)
- Colocacion (metas vs real, embudo, tiempos)
- Captacion (crecimiento, estabilidad)
- Riesgo (cobertura, provisiones, castigos)
- Sucursales (ranking Yuriria/Cuitzeo/Santa Ana)
- Eficiencia de cobranza
- Semaforos consolidados para dashboard
- Tendencias historicas mensual/trimestral por tablero (metas vs real)

Artefactos:
- `docs/mineria/dashboards/01_salud_cartera.csv`
- `docs/mineria/dashboards/02_colocacion.csv`
- `docs/mineria/dashboards/03_captacion.csv`
- `docs/mineria/dashboards/04_riesgo.csv`
- `docs/mineria/dashboards/05_sucursales_ranking.csv`
- `docs/mineria/dashboards/06_eficiencia_cobranza.csv`
- `docs/mineria/dashboards/07_semaforos_dashboard.csv`
- `docs/mineria/dashboards/01_dashboards_ejecutivos_operativos.md`

API semaforos:
- `GET /api/analitica/ml/dashboard/semaforos/`

API tableros completos:
- `GET /api/analitica/ml/dashboard/ejecutivos-operativos/`
- Drill-down sucursal: `GET /api/analitica/ml/dashboard/ejecutivos-operativos/?sucursal=Yuriria&detalle=1`

Visibilidad por rol (1.8):
- `administrador/superadmin` -> vista `consejo_gerencia` (todas las secciones + drill-down).
- `jefe_departamento` -> vista `jefatura` (sin `castigos_estimados`).
- `auditor` -> vista `ejecutivo` (sin riesgo/eficiencia ni drill-down).

Actualizacion automatizada (cron sugerido):
- `0 * * * * /ruta/python /ruta/manage.py actualizar_dashboards_programado_1_8`
- Estado generado en: `docs/mineria/dashboards/08_estado_actualizacion.json`

Cierre UAT (aceptacion de negocio):
- `docs/mineria/dashboards/10_uat_aceptacion_negocio.csv`
- `docs/mineria/dashboards/10_uat_evidencias_operacion.jsonl`
- `docs/mineria/dashboards/10_uat_aceptacion_negocio.md`

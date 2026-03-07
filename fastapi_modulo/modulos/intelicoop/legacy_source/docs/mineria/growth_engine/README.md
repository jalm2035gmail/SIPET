# Motor de Campanas y Colocacion 1.6

Objetivo:
- Transformar insights en colocacion con listas accionables y seguimiento operativo.
- Persistir operacion comercial (contacto y seguimiento/conversion) en tablas transaccionales.

Comando:
- `python manage.py configurar_catalogo_growth_engine_1_6 --catalog-version growth_engine_catalogo_v1`
- `python manage.py motor_campanas_colocacion_1_6`
- `python manage.py integrar_canales_crm_growth_engine_1_6`

Salidas:
- `docs/mineria/growth_engine/00_catalogo_sucursales_ejecutivos.json`
- `docs/mineria/growth_engine/00_catalogo_sucursales_ejecutivos.csv`
- `docs/mineria/growth_engine/00_catalogo_sucursales_ejecutivos.md`
- `docs/mineria/growth_engine/01_preaprobados_sucursal.csv`
- `docs/mineria/growth_engine/02_alta_prob_renovacion.csv`
- `docs/mineria/growth_engine/03_alerta_baja_ahorro.csv`
- `docs/mineria/growth_engine/04_alerta_abandono.csv`
- `docs/mineria/growth_engine/05_asignacion_ejecutivos.csv`
- `docs/mineria/growth_engine/06_registro_contacto.csv`
- `docs/mineria/growth_engine/07_seguimiento_conversion.csv`
- `docs/mineria/growth_engine/08_medicion_campanas.csv`
- `docs/mineria/growth_engine/01_growth_engine_colocacion.md`
- `docs/mineria/growth_engine/09_canales_crm_config.json`
- `docs/mineria/growth_engine/09_envios_canales.jsonl`
- `docs/mineria/growth_engine/10_feedback_conversion.csv`
- `docs/mineria/growth_engine/10_integracion_canales_crm.csv`
- `docs/mineria/growth_engine/10_integracion_canales_crm.md`

Persistencia transaccional:
- `contactos_campania` (modelo `ContactoCampania`)
- `seguimiento_conversion_campania` (modelo `SeguimientoConversionCampania`)

# Ejecuciones de Codigo - Fase 2

## 2026-02-18

### Comando: perfilamiento de calidad
- Comando:
  - `backend/venv/bin/python backend/django_project/manage.py perfilar_datos --format both`
- Salida:
  - `.run/mineria/perfilamiento_calidad_20260218T032235Z.csv`
  - `.run/mineria/perfilamiento_calidad_20260218T032235Z.json`

### Comando: diccionario de datos ORM
- Comando:
  - `backend/venv/bin/python backend/django_project/manage.py diccionario_datos --format both`
- Salida:
  - `.run/mineria/diccionario_datos_20260218T032423Z.csv`
  - `.run/mineria/diccionario_datos_20260218T032423Z.json`

### Comando: reporte de calidad (markdown)
- Comando:
  - `backend/venv/bin/python backend/django_project/manage.py reporte_calidad_datos`
- Salida:
  - `docs/mineria/fase2/12_reporte_calidad_datos.md`

### Comando: plan de remediacion de calidad
- Comando:
  - `backend/venv/bin/python backend/django_project/manage.py plan_remediacion_datos`
- Salida:
  - `docs/mineria/fase2/13_plan_remediacion_calidad.csv`
  - `docs/mineria/fase2/13_plan_remediacion_calidad.md`

### Comando: homologacion de catalogos
- Comando:
  - `backend/venv/bin/python backend/django_project/manage.py homologar_catalogos`
- Salida:
  - `docs/mineria/fase2/14_homologacion_catalogos.csv`
  - `docs/mineria/fase2/14_homologacion_catalogos.md`

### Comando: validacion de datos
- Comando:
  - `backend/venv/bin/python backend/django_project/manage.py validar_datos`
- Salida:
  - `docs/mineria/fase2/15_validacion_datos.csv`
  - `docs/mineria/fase2/15_validacion_datos.md`

### Comando: registro de lineage de carga
- Comando:
  - `backend/venv/bin/python backend/django_project/manage.py registrar_lineage_carga`
- Salida:
  - `.run/mineria/lineage_registry.jsonl`
  - `docs/mineria/fase2/16_lineage_cargas.csv`
  - `docs/mineria/fase2/16_lineage_cargas.md`

### Comando: auditoria de seguridad y cumplimiento
- Comando:
  - `backend/venv/bin/python backend/django_project/manage.py auditar_seguridad_datos`
- Salida:
  - `docs/mineria/fase2/17_auditoria_seguridad.csv`
  - `docs/mineria/fase2/17_auditoria_seguridad.md`

### Comando: cierre tecnico Fase 2
- Comando:
  - `backend/venv/bin/python backend/django_project/manage.py cerrar_fase2_gobierno`
- Salida:
  - `docs/mineria/fase2/18_cierre_fase2.md`

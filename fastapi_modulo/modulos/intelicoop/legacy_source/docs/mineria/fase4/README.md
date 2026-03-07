# Fase 4 - Modelos Complementarios

Evidencia tecnica de implementacion de la fase:

- `01_priorizacion_submodulos.md`
- `01_priorizacion_submodulos.csv`
- `02_mora_temprana_alertas.md`
- `02_mora_temprana_alertas.csv`
- `03_segmentacion_socios_perfiles.md`
- `03_segmentacion_socios_perfiles.csv`
- `04_reglas_asociacion_productos.md`
- `04_reglas_asociacion_productos.csv`
- `05_integracion_submodulos.md`
- `05_integracion_submodulos.csv`
- `06_validacion_funcional_tecnica.md`
- `06_validacion_funcional_tecnica.csv`
- `07_entregables_fase4.md`
- `07_entregables_fase4.csv`

Estado actual:
- Punto 1 de 7: completado tecnicamente.
- Punto 2 de 7: completado tecnicamente.
- Punto 3 de 7: completado tecnicamente.
- Punto 4 de 7: completado tecnicamente.
- Punto 5 de 7: completado tecnicamente.
- Punto 6 de 7: completado tecnicamente.
- Punto 7 de 7: completado tecnicamente.

Comando de regeneracion de evidencia:
- `cd backend/django_project && ../venv/bin/python manage.py priorizar_modelos_complementarios`
- `cd backend/django_project && ../venv/bin/python manage.py generar_alertas_mora_temprana`
- `cd backend/django_project && ../venv/bin/python manage.py generar_segmentacion_mensual_socios --engine orm`
- `cd backend/django_project && ../venv/bin/python manage.py generar_reglas_asociacion_productos`
- `cd backend/django_project && ../venv/bin/python manage.py integrar_submodulos_fase4`
- `cd backend/django_project && ../venv/bin/python manage.py validar_submodulos_fase4`
- `cd backend/django_project && ../venv/bin/python manage.py cerrar_fase4_modelos_complementarios`

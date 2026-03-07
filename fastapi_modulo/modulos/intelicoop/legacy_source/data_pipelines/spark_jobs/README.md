# Segmentacion Diaria de Socios

## Ejecucion manual
```bash
backend/venv/bin/python backend/django_project/manage.py segmentar_socios --engine auto
```

## Modo de prueba (sin escribir en DB)
```bash
backend/venv/bin/python backend/django_project/manage.py segmentar_socios --dry-run --engine orm
```

## Programacion diaria (cron)
1. Copiar la linea de `cron.segmentacion.example` y ajustarla a la ruta del servidor.
2. Cargarla con:
```bash
crontab -e
```
3. Verificar logs en:
`./.run/segmentacion_diaria.log`

## Script operativo
El script `run_segmentacion_diaria.sh`:
- valida virtualenv,
- ejecuta `segmentar_socios`,
- guarda salida con timestamp en `.run/segmentacion_diaria.log`.

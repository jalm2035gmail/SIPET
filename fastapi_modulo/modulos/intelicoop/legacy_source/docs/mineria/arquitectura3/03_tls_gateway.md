# Arquitectura 3 - Etapa 3 de 4: TLS en Transito

Fecha ejecucion UTC: 2026-02-18T17:42:05.448551+00:00

## Resultado
- Controles evaluados: 5
- Configurados: 3
- Pendientes: 2

## Controles
| Control | Estado | Detalle |
|---|---|---|
| nginx_tls_conf | Configurado | /Users/jalm/Dropbox/Apps/intelicoop/docker/nginx.gateway.tls.conf |
| compose_tls_override | Configurado | /Users/jalm/Dropbox/Apps/intelicoop/docker/docker-compose.tls.yml |
| cert_fullchain | Pendiente | /Users/jalm/Dropbox/Apps/intelicoop/certs/fullchain.pem |
| cert_privkey | Pendiente | /Users/jalm/Dropbox/Apps/intelicoop/certs/privkey.pem |
| hsts_header | Configurado | header_hsts_en_nginx_tls_conf |

## Ejecucion TLS (compose override)
- Comando:
```bash
docker compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.tls.yml up -d --build
```
- URL local HTTPS esperada: `https://localhost:8443`
- Certificados requeridos: `certs/fullchain.pem` y `certs/privkey.pem`

## Estado
- Etapa 3 de 4 completada tecnicamente.
- Configuracion TLS del gateway habilitable en despliegue productivo.

## Artefactos
- Reporte CSV: `/Users/jalm/Dropbox/Apps/intelicoop/docs/mineria/arquitectura3/03_tls_gateway.csv`
- Manifest JSON: `/Users/jalm/Dropbox/Apps/intelicoop/docs/mineria/arquitectura3/03_tls_gateway.json`

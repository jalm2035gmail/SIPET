#!/usr/bin/env bash
set -euo pipefail

SERVER="administrator@38.247.146.242"
REMOTE_DIR="/opt/sipet/"
LOCAL_DIR="/Users/jalm/Dropbox/Apps/SIPET/"
PERSISTENT_DB_DIR="/var/lib/sipet/data"
PERSISTENT_DB_PATH="${PERSISTENT_DB_DIR}/polobdtittlan.db"
LEGACY_DB_PATH="/opt/sipet/polobdtittlan.db"
LEGACY_DB_FALLBACK_PATH="/opt/sipet/strategic_planning.db"
DATAMAIN_URL_VALUE="sqlite:////${PERSISTENT_DB_PATH#/}"

echo "Validando ruta persistente de MAIN de datos en servidor..."
ssh "$SERVER" "test -d '${PERSISTENT_DB_DIR}' || { echo 'ERROR: ${PERSISTENT_DB_DIR} no existe en servidor.'; exit 1; }"

echo "Migrando BD legacy si aplica..."
ssh "$SERVER" "if [ -f '${LEGACY_DB_PATH}' ] && [ ! -f '${PERSISTENT_DB_PATH}' ]; then cp '${LEGACY_DB_PATH}' '${PERSISTENT_DB_PATH}'; elif [ -f '${LEGACY_DB_FALLBACK_PATH}' ] && [ ! -f '${PERSISTENT_DB_PATH}' ]; then cp '${LEGACY_DB_FALLBACK_PATH}' '${PERSISTENT_DB_PATH}'; fi"

echo "Fijando configuración de producción en /opt/sipet/.env..."
ssh "$SERVER" "touch '${REMOTE_DIR}.env' && \
  grep -q '^APP_ENV=' '${REMOTE_DIR}.env' && sed -i 's|^APP_ENV=.*|APP_ENV=production|' '${REMOTE_DIR}.env' || echo 'APP_ENV=production' >> '${REMOTE_DIR}.env' && \
  grep -q '^DATAMAIN_URL=' '${REMOTE_DIR}.env' && sed -i 's|^DATAMAIN_URL=.*|DATAMAIN_URL=${DATAMAIN_URL_VALUE}|' '${REMOTE_DIR}.env' || echo 'DATAMAIN_URL=${DATAMAIN_URL_VALUE}' >> '${REMOTE_DIR}.env' && \
  grep -q '^SQLITE_DB_PATH=' '${REMOTE_DIR}.env' && sed -i 's|^SQLITE_DB_PATH=.*|SQLITE_DB_PATH=${PERSISTENT_DB_PATH}|' '${REMOTE_DIR}.env' || echo 'SQLITE_DB_PATH=${PERSISTENT_DB_PATH}' >> '${REMOTE_DIR}.env' && \
  grep -q '^AUTH_COOKIE_SECRET=' '${REMOTE_DIR}.env' || (python3 -c 'import secrets; print(\"AUTH_COOKIE_SECRET=\" + secrets.token_urlsafe(48))' >> '${REMOTE_DIR}.env')"

echo "Desplegando código..."
rsync -az --delete \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.env' \
  --exclude 'fastapi_modulo/runtime_store/' \
  --exclude 'fastapi_modulo/templates/imagenes/' \
  --exclude 'fastapi_modulo/identidad_login.json' \
  --exclude 'fastapi_modulo/uploads/' \
  "$LOCAL_DIR" "$SERVER:$REMOTE_DIR"

echo "Reiniciando app con SQLITE_DB_PATH persistente..."
ssh -tt "$SERVER" "cd '${REMOTE_DIR}' && SQLITE_DB_PATH='${PERSISTENT_DB_PATH}' sudo /usr/local/bin/sipet-restart"

echo "Deploy completado. BD persistente en ${PERSISTENT_DB_PATH}"

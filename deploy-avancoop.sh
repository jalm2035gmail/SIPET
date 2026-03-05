#!/usr/bin/env bash
set -euo pipefail

# =========================
# Configuracion AVANCOOP (exclusiva)
# =========================
SERVER="${SERVER:-administrator@38.247.130.84}"
REMOTE_DIR="${REMOTE_DIR:-/opt/avancoop/}"
LOCAL_DIR="${LOCAL_DIR:-/Users/jalm/Dropbox/Apps/SIPET/}"
PERSISTENT_DB_DIR="${PERSISTENT_DB_DIR:-/var/lib/avancoop/data}"
PERSISTENT_DB_PATH="${PERSISTENT_DB_PATH:-${PERSISTENT_DB_DIR}/strategic_planning.db}"
LEGACY_DB_PATH="${LEGACY_DB_PATH:-/opt/avancoop/strategic_planning.db}"
RESTART_CMD="${RESTART_CMD:-/usr/local/bin/avancoop-restart}"
DATABASE_URL_VALUE="sqlite:////${PERSISTENT_DB_PATH#/}"

echo "Configuracion activa:"
echo "  SERVER=$SERVER"
echo "  APP=avancoop"
echo "  REMOTE_DIR=$REMOTE_DIR"
echo "  PERSISTENT_DB_DIR=$PERSISTENT_DB_DIR"
echo "  RESTART_CMD=$RESTART_CMD"

echo "Validando ruta persistente de base de datos en servidor..."
ssh "$SERVER" "test -d '${PERSISTENT_DB_DIR}' || { echo 'ERROR: ${PERSISTENT_DB_DIR} no existe en servidor.'; exit 1; }"

echo "Migrando BD legacy si aplica..."
ssh "$SERVER" "if [ -f '${LEGACY_DB_PATH}' ] && [ ! -f '${PERSISTENT_DB_PATH}' ]; then cp '${LEGACY_DB_PATH}' '${PERSISTENT_DB_PATH}'; fi"

echo "Fijando configuracion de produccion en ${REMOTE_DIR}.env..."
ssh "$SERVER" "touch '${REMOTE_DIR}.env' && \
  grep -q '^APP_ENV=' '${REMOTE_DIR}.env' && sed -i 's|^APP_ENV=.*|APP_ENV=production|' '${REMOTE_DIR}.env' || echo 'APP_ENV=production' >> '${REMOTE_DIR}.env' && \
  grep -q '^DATABASE_URL=' '${REMOTE_DIR}.env' && sed -i 's|^DATABASE_URL=.*|DATABASE_URL=${DATABASE_URL_VALUE}|' '${REMOTE_DIR}.env' || echo 'DATABASE_URL=${DATABASE_URL_VALUE}' >> '${REMOTE_DIR}.env' && \
  grep -q '^SQLITE_DB_PATH=' '${REMOTE_DIR}.env' && sed -i 's|^SQLITE_DB_PATH=.*|SQLITE_DB_PATH=${PERSISTENT_DB_PATH}|' '${REMOTE_DIR}.env' || echo 'SQLITE_DB_PATH=${PERSISTENT_DB_PATH}' >> '${REMOTE_DIR}.env' && \
  grep -q '^AUTH_COOKIE_SECRET=' '${REMOTE_DIR}.env' || (python3 -c 'import secrets; print(\"AUTH_COOKIE_SECRET=\" + secrets.token_urlsafe(48))' >> '${REMOTE_DIR}.env')"

echo "Desplegando codigo..."
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
ssh -tt "$SERVER" "cd '${REMOTE_DIR}' && SQLITE_DB_PATH='${PERSISTENT_DB_PATH}' sudo '${RESTART_CMD}'"

echo "Deploy completado. BD persistente en ${PERSISTENT_DB_PATH}"

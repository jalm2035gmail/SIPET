#!/bin/bash
# Script para reiniciar el sistema, cargar módulos y base de datos

# Activar entorno virtual .venv si existe
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Cargar variables de entorno desde .env (desarrollo local)
if [ -f ".env" ]; then
    set -a
    # shellcheck disable=SC1091
    source ".env"
    set +a
fi

# Configurar ruta persistente para SQLite (producción web)
# Prioridad:
# 1) SQLITE_DB_PATH ya definida en entorno/.env
# 2) Ruta persistente por defecto /var/lib/sipet/data/strategic_planning.db
# 3) Fallback local ./strategic_planning.db si no hay permisos
DEFAULT_DB_DIR="/var/lib/sipet/data"
DEFAULT_DB_PATH="${DEFAULT_DB_DIR}/strategic_planning.db"
LEGACY_DB_PATH="/opt/sipet/strategic_planning.db"

if [ -z "${SQLITE_DB_PATH:-}" ]; then
    SQLITE_DB_PATH="$DEFAULT_DB_PATH"
fi

DB_DIR="$(dirname "$SQLITE_DB_PATH")"
if ! mkdir -p "$DB_DIR" 2>/dev/null; then
    echo "Aviso: No se pudo crear ${DB_DIR}. Se usará fallback local."
    SQLITE_DB_PATH="${PWD}/strategic_planning.db"
    DB_DIR="$(dirname "$SQLITE_DB_PATH")"
    mkdir -p "$DB_DIR"
fi

# Migrar BD legacy solo si existe y la nueva no existe aún
if [ "$SQLITE_DB_PATH" != "$LEGACY_DB_PATH" ] && [ -f "$LEGACY_DB_PATH" ] && [ ! -f "$SQLITE_DB_PATH" ]; then
    cp "$LEGACY_DB_PATH" "$SQLITE_DB_PATH"
    echo "BD migrada desde $LEGACY_DB_PATH hacia $SQLITE_DB_PATH"
fi

export SQLITE_DB_PATH

# Persistir SQLITE_DB_PATH en .env para reinicios futuros
if [ -f ".env" ]; then
    if grep -q '^SQLITE_DB_PATH=' ".env"; then
        sed -i.bak "s|^SQLITE_DB_PATH=.*|SQLITE_DB_PATH=${SQLITE_DB_PATH}|g" ".env" && rm -f ".env.bak"
    else
        printf '\nSQLITE_DB_PATH=%s\n' "$SQLITE_DB_PATH" >> ".env"
    fi
else
    printf 'SQLITE_DB_PATH=%s\n' "$SQLITE_DB_PATH" > ".env"
fi
echo "Usando SQLITE_DB_PATH=${SQLITE_DB_PATH}"

# En producción, forzar DATABASE_URL hacia ruta persistente para evitar
# que quede apuntando a sqlite:///./strategic_planning.db dentro de /opt/sipet.
APP_ENV_EFFECTIVE="${APP_ENV:-development}"
if [ "$APP_ENV_EFFECTIVE" = "production" ] || [ "$APP_ENV_EFFECTIVE" = "prod" ]; then
    DATABASE_URL="sqlite:///${SQLITE_DB_PATH}"
    export DATABASE_URL
    if [ -f ".env" ]; then
        if grep -q '^DATABASE_URL=' ".env"; then
            sed -i.bak "s|^DATABASE_URL=.*|DATABASE_URL=${DATABASE_URL}|g" ".env" && rm -f ".env.bak"
        else
            printf '\nDATABASE_URL=%s\n' "$DATABASE_URL" >> ".env"
        fi
        if grep -q '^APP_ENV=' ".env"; then
            sed -i.bak "s|^APP_ENV=.*|APP_ENV=production|g" ".env" && rm -f ".env.bak"
        else
            printf '\nAPP_ENV=production\n' >> ".env"
        fi
    fi
    echo "Producción activa. DATABASE_URL fijada a ${DATABASE_URL}"
fi

# Asegurar secreto estable para login/hash de usuarios.
# Si falta, se persiste en .env para que no cambie entre reinicios.
if [ -z "${AUTH_COOKIE_SECRET:-}" ]; then
    AUTH_COOKIE_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')
    export AUTH_COOKIE_SECRET
    if [ -f ".env" ]; then
        if ! grep -q '^AUTH_COOKIE_SECRET=' ".env"; then
            printf '\nAUTH_COOKIE_SECRET=%s\n' "$AUTH_COOKIE_SECRET" >> ".env"
        fi
    else
        printf 'AUTH_COOKIE_SECRET=%s\n' "$AUTH_COOKIE_SECRET" > ".env"
    fi
    echo "Aviso: AUTH_COOKIE_SECRET no estaba definida. Se generó y guardó en .env."
fi

# Instalar dependencias
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

# Migrar base de datos (Alembic — usa 'heads' para soportar múltiples cabezas)
if [ -f "alembic.ini" ]; then
    alembic upgrade heads
fi

# Cargar módulos personalizados (placeholder)
# Aquí puedes agregar comandos para cargar módulos
# echo "Cargando módulos..."

# Reiniciar el sistema (FastAPI)
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"
LOG_FILE="${LOG_FILE:-uvicorn.log}"

# Detener procesos previos
PIDS_EN_PUERTO=$(lsof -ti:"$PORT" 2>/dev/null)
if [ -n "$PIDS_EN_PUERTO" ]; then
    echo "Deteniendo procesos en el puerto $PORT: $PIDS_EN_PUERTO"
    for PID in $PIDS_EN_PUERTO; do
        kill "$PID" 2>/dev/null || true
    done
    sleep 1

    PIDS_RESTANTES=$(lsof -ti:"$PORT" 2>/dev/null)
    if [ -n "$PIDS_RESTANTES" ]; then
        echo "Forzando cierre de procesos restantes: $PIDS_RESTANTES"
        for PID in $PIDS_RESTANTES; do
            kill -9 "$PID" 2>/dev/null || true
        done
        sleep 1
    fi

    PIDS_BLOQUEANDO=$(lsof -ti:"$PORT" 2>/dev/null)
    if [ -n "$PIDS_BLOQUEANDO" ]; then
        echo "Error: No se pudo liberar el puerto $PORT. Procesos bloqueando: $PIDS_BLOQUEANDO"
        echo "Tip: intenta con permisos elevados, por ejemplo: sudo lsof -i :$PORT"
        exit 1
    fi
fi

# Iniciar el servidor y guardar logs reales
echo "Iniciando servidor FastAPI en ${HOST}:${PORT}..."
uvicorn fastapi_modulo.main:app --host "$HOST" --port "$PORT" > "$LOG_FILE" 2>&1 &
UVICORN_PID=$!
sleep 3

if kill -0 "$UVICORN_PID" 2>/dev/null && lsof -ti:"$PORT" 2>/dev/null | grep -qx "$UVICORN_PID"; then
    echo "Servidor iniciado correctamente en ${HOST}:${PORT}."
else
    echo "Error: El servidor no se inició. Revisa $LOG_FILE para detalles."
    if [ -f "$LOG_FILE" ]; then
        echo "Ultimas lineas del log:"
        tail -n 40 "$LOG_FILE"
    fi
fi

echo "Sistema actualizado y reiniciado."

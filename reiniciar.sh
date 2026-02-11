#!/bin/bash
# Script para reiniciar el sistema, cargar módulos y base de datos

 # Activar entorno virtual .venv si existe
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Instalar dependencias
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

# Migrar base de datos (ejemplo para Alembic)
if [ -d "fastapi_modulo" ] && [ -f "fastapi_modulo/alembic.ini" ]; then
    alembic upgrade head
fi

# Cargar módulos personalizados (placeholder)
# Aquí puedes agregar comandos para cargar módulos
# echo "Cargando módulos..."

# Reiniciar el sistema (FastAPI)
# Detener procesos previos
PID=$(lsof -ti:8005)
if [ ! -z "$PID" ]; then
    echo "Matando proceso en el puerto 8005 (PID: $PID)"
    kill -9 $PID
fi
# Iniciar el servidor
echo "Iniciando servidor FastAPI en el puerto 8005..."
uvicorn fastapi_modulo.main:app --host 0.0.0.0 --port 8005 &
sleep 2
lsof -i:8005 > /dev/null
if [ $? -eq 0 ]; then
    echo "Servidor iniciado correctamente."
else
    echo "Error: El servidor no se inició. Revisa uvicorn.log para detalles."
fi

echo "Sistema actualizado y reiniciado."

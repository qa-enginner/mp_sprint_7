#!/bin/bash
set -e

wait_for_port() {
    local host="$1"
    local port="$2"
    local service="$3"
    echo "Waiting for $service to become ready..."
    while ! python -c "import socket; socket.create_connection(('$host', $port), timeout=2)" 2>/dev/null; do
        echo "$service is unavailable - sleeping"
        sleep 2
    done
    echo "$service is ready!"
}

# Wait for dependencies
wait_for_port "$POSTGRES_HOST" "$POSTGRES_PORT" "PostgreSQL"
wait_for_port "$REDIS_HOST" "$REDIS_PORT" "Redis"

echo "Applying database migrations..."
alembic upgrade head

echo "Starting application..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
#!/bin/bash
# Docker entrypoint script: Run migrations then start the app

set -e

echo "Waiting for PostgreSQL to be ready..."
while ! nc -z "$DB_HOST" "$DB_PORT" 2>/dev/null; do
    echo "  PostgreSQL not ready yet, retrying in 2 seconds..."
    sleep 2
done
echo "PostgreSQL is ready!"

echo ""
echo "Running database migrations..."
alembic upgrade head
echo "Migrations completed!"

echo ""
echo "🚀 Starting Laker API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app

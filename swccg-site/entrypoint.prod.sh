#!/bin/sh

# Exit on error
set -e

# Wait for database to be ready
echo "Waiting for PostgreSQL..."
while ! nc -z $DATABASE_HOST $DATABASE_PORT; do
  sleep 0.1
done
echo "PostgreSQL started"

# Wait for Redis to be ready (backs the Channels layer)
echo "Waiting for Redis..."
while ! nc -z ${REDIS_HOST:-redis} ${REDIS_PORT:-6379}; do
  sleep 0.1
done
echo "Redis started"

# Run database migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Start Gunicorn (ASGI, via Uvicorn workers, for Channels/WebSocket support)
echo "Starting Gunicorn..."
exec gunicorn swccg.asgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --worker-class uvicorn.workers.UvicornWorker \
    --log-file - \
    --access-logfile - \
    --error-logfile - \
    --log-level info

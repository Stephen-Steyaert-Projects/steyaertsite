#!/bin/sh

# Exit on error
set -e

# Wait for database to be ready
echo "Waiting for PostgreSQL..."
while ! nc -z $DATABASE_HOST $DATABASE_PORT; do
  sleep 0.1
done
echo "PostgreSQL started"

# Run database migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Start Gunicorn
echo "Starting Gunicorn..."
exec gunicorn steyaertsite.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 1 \
    --threads 4 \
    --worker-class gthread \
    --worker-tmp-dir /dev/shm \
    --log-file - \
    --access-logfile - \
    --error-logfile - \
    --log-level info 

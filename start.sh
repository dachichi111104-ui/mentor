#!/usr/bin/env bash
# ProjectHub AI Startup Script for Production (Render)
set -o errexit

echo "1. Running database migrations..."
python manage.py migrate --noinput

echo "2. Ensuring system admin user..."
python manage.py ensure_admin

echo "3. Collecting static files..."
python manage.py collectstatic --noinput

PORT="${PORT:-10000}"
echo "4. Starting ASGI Web Server on 0.0.0.0:${PORT}..."
exec gunicorn projecthub_config.asgi:application \
    -k uvicorn.workers.UvicornWorker \
    --bind "0.0.0.0:${PORT}" \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -

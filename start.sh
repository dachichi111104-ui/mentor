#!/usr/bin/env bash
# Script khởi chạy gộp cho Render Free Plan (1 Web Instance duy nhất)

# Khởi chạy Celery worker & beat ở background nếu có REDIS_URL
if [ -n "$REDIS_URL" ]; then
    echo "Starting Celery worker in background..."
    celery -A projecthub_config worker --loglevel=info &
    
    echo "Starting Celery beat in background..."
    celery -A projecthub_config beat --loglevel=info &
fi

# Khởi chạy Web Server chính (Gunicorn)
echo "Starting Gunicorn Web Server..."
exec gunicorn projecthub_config.wsgi:application --log-file -

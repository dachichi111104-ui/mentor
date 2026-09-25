#!/usr/bin/env bash
# Script khởi chạy gộp cho Render Free Plan (1 Web Instance duy nhất)

# 1. Khởi chạy Celery worker & beat ở background (nếu cài đặt celery và có REDIS_URL)
if [ -n "$REDIS_URL" ]; then
    echo "Starting Celery worker & beat in background..."
    (celery -A projecthub_config worker --loglevel=info &) || true
    (celery -A projecthub_config beat --loglevel=info &) || true
fi

# 2. Khởi chạy Gunicorn Web Server chính (bắt buộc bind đúng PORT do Render cấp)
PORT="${PORT:-10000}"
echo "Starting Gunicorn Web Server on 0.0.0.0:${PORT}..."
exec gunicorn projecthub_config.wsgi:application --bind "0.0.0.0:${PORT}" --workers 2 --timeout 120 --log-file -

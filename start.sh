#!/usr/bin/env bash
# Script khởi chạy gộp tối ưu cho Render Free Plan (512MB RAM)
set -o errexit

# 1. Tạo tài khoản mẫu tự động nếu cơ sở dữ liệu mới tinh (trên Render PostgreSQL)
python manage.py shell -c "
from accounts.models import User, UserRole
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@vnu.edu.vn', 'admin123', first_name='Quản trị', last_name='Hệ thống', role=UserRole.ADMIN)
    print('Created default admin: admin / admin123')
if not User.objects.filter(username='student').exists():
    User.objects.create_user('student', 'student@vnu.edu.vn', 'student123', first_name='Nguyễn Văn', last_name='Anh', role=UserRole.STUDENT, student_id='SV2026001', department='CNTT', class_name='KTPM2022')
    print('Created default student: student / student123')
if not User.objects.filter(username='mentor').exists():
    User.objects.create_user('mentor', 'mentor@vnu.edu.vn', 'mentor123', first_name='Nguyễn Văn', last_name='Minh', role=UserRole.MENTOR, student_id='GV2026001', department='CNTT', specialization='Phát triển Web & AI')
    print('Created default mentor: mentor / mentor123')
" || true

# 2. Khởi chạy Celery worker (--pool=solo) & beat ở background tiết kiệm RAM (nếu có REDIS_URL)
if [ -n "$REDIS_URL" ]; then
    echo "Starting Celery worker (--pool=solo) & beat in background..."
    (celery -A projecthub_config worker --loglevel=info --pool=solo &) || true
    (celery -A projecthub_config beat --loglevel=info &) || true
fi

# 3. Khởi chạy Gunicorn Web Server (1 worker, 2 threads tránh tràn RAM 512MB gây lỗi 502)
PORT="${PORT:-10000}"
echo "Starting Gunicorn Web Server on 0.0.0.0:${PORT}..."
exec gunicorn projecthub_config.wsgi:application --bind "0.0.0.0:${PORT}" --workers 1 --threads 2 --timeout 120 --log-file -

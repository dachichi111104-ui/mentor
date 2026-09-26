#!/usr/bin/env bash
# Script khởi chạy gộp tối ưu cho Render Free Plan (512MB RAM)
set -o errexit

# 1. Khởi tạo CSDL & dữ liệu mẫu tự động trên Render PostgreSQL
python manage.py shell -c "
from django.utils import timezone
import datetime
from accounts.models import User, UserRole
from projects.models import Project, ProjectMember, ProjectStatus
from tasks.models import Task, TaskStatus, TaskPriority
from milestones.models import Milestone
from documents.models import Document, DocumentVersion

admin_u, _ = User.objects.get_or_create(username='admin', defaults={'email': 'admin@vnu.edu.vn', 'first_name': 'Quản trị', 'last_name': 'Hệ thống', 'role': UserRole.ADMIN, 'is_superuser': True, 'is_staff': True})
if _: admin_u.set_password('admin123'); admin_u.save()

student, _ = User.objects.get_or_create(username='student', defaults={'email': 'student@vnu.edu.vn', 'first_name': 'Nguyễn Văn', 'last_name': 'Anh', 'role': UserRole.STUDENT, 'student_id': 'SV2026001', 'department': 'CNTT', 'class_name': 'KTPM2022'})
if _: student.set_password('student123'); student.save()

mentor, _ = User.objects.get_or_create(username='mentor', defaults={'email': 'mentor@vnu.edu.vn', 'first_name': 'Nguyễn Văn', 'last_name': 'Minh', 'role': UserRole.MENTOR, 'student_id': 'GV2026001', 'department': 'CNTT', 'specialization': 'Phát triển Web & AI'})
if _: mentor.set_password('mentor123'); mentor.save()

if not Project.objects.exists():
    from django.core.management import call_command
    try:
        call_command('loaddata', 'fixtures_demo.json')
        print('Loaded fixtures_demo.json successfully to Render PostgreSQL!')
    except Exception as e:
        print(f'Loaddata notice: {e}')
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

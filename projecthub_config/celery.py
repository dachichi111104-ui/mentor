import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'projecthub_config.settings')

app = Celery('projecthub_config')

# Load configuration from Django settings, using CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Redis Broker & Result Backend configuration
redis_url = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')
app.conf.broker_url = redis_url
app.conf.result_backend = redis_url
app.conf.timezone = 'Asia/Ho_Chi_Minh'

# Celery Beat Periodic Schedule
app.conf.beat_schedule = {
    'check-overdue-tasks-and-milestones-daily': {
        'task': 'notifications.tasks.check_overdue_tasks_and_milestones',
        'schedule': crontab(hour=8, minute=0),  # Runs daily at 08:00 AM
    },
    'generate-weekly-project-summaries': {
        'task': 'ai_assistant.tasks.generate_weekly_summaries_task',
        'schedule': crontab(day_of_week='monday', hour=7, minute=0),  # Runs every Monday at 07:00 AM
    },
}

app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

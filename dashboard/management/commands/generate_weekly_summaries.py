import sys
from django.core.management.base import BaseCommand
from ai_assistant.tasks import generate_weekly_summaries_task

class Command(BaseCommand):
    help = "Generates weekly summaries for all active projects."

    def handle(self, *args, **options):
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        res = generate_weekly_summaries_task()
        self.stdout.write(self.style.SUCCESS(f"Tạo báo cáo tuần hoàn tất: {res}"))

import sys
from django.core.management.base import BaseCommand
from ai_assistant.tasks import daily_risk_scan_task

class Command(BaseCommand):
    help = "Scans active projects for risks and sends critical risk notifications."

    def handle(self, *args, **options):
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        res = daily_risk_scan_task()
        self.stdout.write(self.style.SUCCESS(f"Quét rủi ro hoàn tất: {res}"))

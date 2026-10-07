import sys
from django.core.management.base import BaseCommand
from django.utils import timezone
from milestones.models import Milestone, MilestoneStatus
from tasks.models import Task

class Command(BaseCommand):
    help = "Checks and marks overdue milestones and tasks."

    def handle(self, *args, **options):
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        today = timezone.localdate()
        m_count = Milestone.objects.filter(due_date__lt=today).exclude(status=MilestoneStatus.COMPLETED).update(status=MilestoneStatus.OVERDUE)
        self.stdout.write(self.style.SUCCESS(f"Đã cập nhật {m_count} milestone quá hạn thành OVERDUE."))

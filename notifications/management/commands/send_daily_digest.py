from django.core.management.base import BaseCommand
from accounts.models import User, UserStatus
from tasks.models import Task, TaskStatus
from notifications.services import notify
from notifications.models import Notification, NotificationType

class Command(BaseCommand):
    help = 'Gui thong bao tong hop cong viec hang ngay (Daily Digest) cho sinh vien va mentor'

    def handle(self, *args, **options):
        self.stdout.write("Bat dau gui Daily Digest notifications...")
        users = User.objects.filter(status=UserStatus.ACTIVE)

        sent_count = 0
        for u in users:
            pending_tasks = Task.objects.filter(assignee=u).exclude(status=TaskStatus.DONE)
            overdue_count = sum(1 for t in pending_tasks if t.is_overdue)

            if pending_tasks.exists():
                msg = f"Ban dang co {pending_tasks.count()} cong viec chua hoan thanh"
                if overdue_count > 0:
                    msg += f", trong do co {overdue_count} cong viec da qua han!"
                else:
                    msg += ". Vui long kiem tra tien do hom nay."

                notify(
                    recipient=u,
                    title="[Daily Digest] Tong hop tien do cong viec hom nay",
                    message=msg,
                    link="/my-tasks/",
                    notification_type=NotificationType.TASK_ASSIGNED
                )
                sent_count += 1

        self.stdout.write(self.style.SUCCESS(f"Da gui thanh cong {sent_count} thong bao Daily Digest!"))

from django.core.management.base import BaseCommand
from django.utils import timezone
from tasks.models import Task, TaskStatus
from milestones.models import Milestone, MilestoneStatus
from notifications.models import Notification, NotificationType

class Command(BaseCommand):
    help = 'Kiểm tra và cảnh báo công việc / mốc đồ án bị quá hạn chót'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # 1. Overdue Tasks
        overdue_tasks = Task.objects.filter(due_date__lt=today).exclude(status=TaskStatus.DONE)
        task_count = 0
        for task in overdue_tasks:
            # Check if notification already sent for this overdue task today
            exists = Notification.objects.filter(
                recipient=task.assignee if task.assignee else task.created_by,
                notification_type=NotificationType.TASK_OVERDUE,
                link=f'/projects/{task.project.id}/tasks/',
                created_at__date=today
            ).exists()
            
            if not exists and (task.assignee or task.created_by):
                target_user = task.assignee if task.assignee else task.created_by
                Notification.objects.create(
                    recipient=target_user,
                    sender=task.created_by,
                    title=f'Cảnh báo: Task quá hạn [{task.title}]',
                    message=f'Công việc "{task.title}" trong đồ án "{task.project.name}" đã trễ hạn chót ({task.due_date}).',
                    link=f'/projects/{task.project.id}/tasks/',
                    notification_type=NotificationType.TASK_OVERDUE
                )
                task_count += 1

        # 2. Overdue Milestones
        overdue_milestones = Milestone.objects.filter(due_date__lt=today).exclude(status=MilestoneStatus.COMPLETED)
        milestone_count = 0
        for ms in overdue_milestones:
            if ms.status != MilestoneStatus.OVERDUE:
                ms.status = MilestoneStatus.OVERDUE
                ms.save()

            # Send notification to project members
            members = ms.project.memberships.all()
            for m in members:
                exists = Notification.objects.filter(
                    recipient=m.user,
                    notification_type=NotificationType.MILESTONE_DUE,
                    link=f'/projects/{ms.project.id}/milestones/',
                    created_at__date=today
                ).exists()
                
                if not exists:
                    Notification.objects.create(
                        recipient=m.user,
                        sender=ms.project.created_by,
                        title=f'Cảnh báo: Milestone trễ hạn [{ms.name}]',
                        message=f'Mốc milestone "{ms.name}" của đồ án "{ms.project.name}" đã quá hạn ({ms.due_date}). Tiến độ hiện đạt {ms.progress_percentage}%.',
                        link=f'/projects/{ms.project.id}/milestones/',
                        notification_type=NotificationType.MILESTONE_DUE
                    )
                    milestone_count += 1

        self.stdout.write(self.style.SUCCESS(f'Hoàn thành kiểm tra: Đã tạo {task_count} thông báo task quá hạn, cập nhật {milestone_count} milestone quá hạn.'))

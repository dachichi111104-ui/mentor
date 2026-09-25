from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from tasks.models import Task, TaskStatus
from milestones.models import Milestone, MilestoneStatus
from notifications.models import Notification, NotificationType

@shared_task
def check_overdue_tasks_and_milestones():
    """
    Periodic task run by Celery Beat to check overdue/approaching tasks & milestones,
    create system notifications and send email alerts.
    """
    today = timezone.now().date()
    notified_count = 0

    # 1. Overdue Tasks
    overdue_tasks = Task.objects.filter(
        due_date__lt=today
    ).exclude(status=TaskStatus.DONE)

    for task in overdue_tasks:
        recipients = set()
        if task.assignee:
            recipients.add(task.assignee)
        if task.created_by:
            recipients.add(task.created_by)
        if task.project.mentor:
            recipients.add(task.project.mentor)

        for user in recipients:
            n, created = Notification.objects.get_or_create(
                recipient=user,
                title=f"⚠️ Cảnh báo trễ hạn công việc: {task.title}",
                notification_type=NotificationType.TASK_OVERDUE,
                defaults={
                    'message': f"Công việc '{task.title}' thuộc đồ án [{task.project.code}] {task.project.name} đã quá hạn hoàn thành ({task.due_date}).",
                    'link': f"/projects/{task.project.id}/tasks/"
                }
            )
            if created:
                notified_count += 1
                if user.email:
                    try:
                        send_mail(
                            subject=n.title,
                            message=n.message,
                            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@projecthub.local'),
                            recipient_list=[user.email],
                            fail_silently=True
                        )
                    except Exception as e:
                        print(f"Failed to send email to {user.email}: {e}")

    # 2. Overdue Milestones
    overdue_milestones = Milestone.objects.filter(
        due_date__lt=today
    ).exclude(status=MilestoneStatus.COMPLETED)

    for ms in overdue_milestones:
        recipients = set()
        recipients.add(ms.project.created_by)
        if ms.project.mentor:
            recipients.add(ms.project.mentor)

        for user in recipients:
            n, created = Notification.objects.get_or_create(
                recipient=user,
                title=f"🚨 Milestone quá hạn: {ms.name}",
                notification_type=NotificationType.MILESTONE_DUE,
                defaults={
                    'message': f"Giai đoạn Milestone '{ms.name}' thuộc đồ án [{ms.project.code}] {ms.project.name} đã quá hạn chót ({ms.due_date}).",
                    'link': f"/projects/{ms.project.id}/milestones/"
                }
            )
            if created:
                notified_count += 1

    return f"Checked overdue items: Sent {notified_count} new notifications."

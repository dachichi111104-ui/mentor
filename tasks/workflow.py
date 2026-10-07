from django.utils import timezone
from django.db import transaction
from tasks.models import Task, TaskStatus, TaskComment
from projects.permissions import get_project_role
from audit_log.models import ActionType
from audit_log.utils import log_action
from notifications.models import Notification, NotificationType
from notifications.services import notify


def transition(task, new_status, actor, reason=None, force=False):
    """
    Single authoritative task state machine transition helper.
    """
    if task.status == new_status:
        return True, "Trạng thái không đổi"

    role = get_project_role(actor, task.project)
    is_assignee = (task.assignee == actor or task.created_by == actor)
    old_status = task.status

    valid = False

    # TODO -> IN_PROGRESS
    if old_status == TaskStatus.TODO and new_status == TaskStatus.IN_PROGRESS:
        if is_assignee or role in ['ADMIN', 'LEADER']:
            valid = True

    # IN_PROGRESS -> TODO
    elif old_status == TaskStatus.IN_PROGRESS and new_status == TaskStatus.TODO:
        if is_assignee or role in ['ADMIN', 'LEADER']:
            valid = True

    # IN_PROGRESS -> REVIEW
    elif old_status == TaskStatus.IN_PROGRESS and new_status == TaskStatus.REVIEW:
        if is_assignee or role in ['ADMIN', 'LEADER']:
            valid = True

    # REVIEW -> DONE
    elif old_status == TaskStatus.REVIEW and new_status == TaskStatus.DONE:
        if role in ['ADMIN', 'LEADER', 'MENTOR']:
            valid = True

    # REVIEW -> IN_PROGRESS (Yêu cầu làm lại - require reason >= 10 chars)
    elif old_status == TaskStatus.REVIEW and new_status == TaskStatus.IN_PROGRESS:
        if role in ['ADMIN', 'LEADER', 'MENTOR']:
            if not reason or len(reason.strip()) < 10:
                return False, "Cần nhập lý do yêu cầu sửa tối thiểu 10 ký tự"
            valid = True

    # DONE -> IN_PROGRESS (Reopen - require reason)
    elif old_status == TaskStatus.DONE and new_status == TaskStatus.IN_PROGRESS:
        if role in ['ADMIN', 'LEADER']:
            if not reason or len(reason.strip()) < 5:
                return False, "Cần nhập lý do mở lại nhiệm vụ"
            valid = True

    # Admin force override
    if not valid and actor.is_admin_user and force:
        valid = True

    if not valid:
        return False, f"Không thể chuyển trạng thái từ {task.get_status_display()} sang {TaskStatus(new_status).label} với vai trò của bạn."

    with transaction.atomic():
        task.status = new_status
        task.status_changed_at = timezone.now()
        if new_status == TaskStatus.DONE:
            task.completed_at = timezone.now()
        elif old_status == TaskStatus.DONE:
            task.completed_at = None
        task.save()

        # Handle review revision comment
        if old_status == TaskStatus.REVIEW and new_status == TaskStatus.IN_PROGRESS and reason:
            TaskComment.objects.create(
                task=task,
                user=actor,
                content=f"[YÊU CẦU SỬA]: {reason.strip()}"
            )

        # Audit Log
        log_action(
            user=actor,
            action=ActionType.CHANGE_STATUS,
            entity_type='Task',
            entity_id=task.id,
            description=f"Chuyển trạng thái nhiệm vụ '{task.title}' từ [{old_status}] sang [{new_status}]",
            project=task.project
        )

        # Notifications
        recipients = set()
        if task.assignee and task.assignee != actor:
            recipients.add(task.assignee)
        if task.project.created_by and task.project.created_by != actor:
            recipients.add(task.project.created_by)
        if new_status == TaskStatus.REVIEW and task.project.mentor and task.project.mentor != actor:
            recipients.add(task.project.mentor)

        for recipient in recipients:
            notify(
                recipient=recipient,
                sender=actor,
                title=f"Nhiệm vụ [{task.project.code}] đổi trạng thái",
                message=f"{actor.display_name} đã chuyển nhiệm vụ '{task.title[:50]}' sang [{task.get_status_display()}].",
                link=f"/tasks/{task.id}/",
                notification_type=NotificationType.TASK_ASSIGNED,
                project=task.project
            )


    return True, "Thành công"

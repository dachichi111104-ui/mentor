from django.utils import timezone
from django.db import transaction
from projects.models import Project, ProjectStatus, MentorStatus
from audit_log.models import ActionType
from audit_log.utils import log_action
from notifications.services import notify
from notifications.models import NotificationType

def apply_project_review(project, new_status, actor, content="", rating=5):
    """
    Applies review outcome to project state machine.
    """
    old_status = project.status

    if new_status == ProjectStatus.COMPLETED:
        if old_status != ProjectStatus.REVIEW and not actor.is_admin_user:
            return False, "Đồ án phải ở trạng thái Đang Review mới có thể đánh giá Hoàn thành."
    elif new_status == ProjectStatus.IN_PROGRESS:
        pass

    with transaction.atomic():
        project.status = new_status
        project.save()

        log_action(
            user=actor,
            action=ActionType.SUBMIT_REVIEW,
            entity_type='Project',
            entity_id=project.id,
            description=f"Mentor/Admin đổi trạng thái đồ án '{project.name}' từ [{old_status}] sang [{new_status}]",
            project=project
        )

        # Notify all accepted members
        for mem in project.memberships.filter(status='ACCEPTED'):
            if mem.user != actor:
                notify(
                    recipient=mem.user,
                    sender=actor,
                    title=f"Đồ án [{project.code}] cập nhật trạng thái",
                    message=f"Mentor đã đánh giá đồ án: {new_status}",
                    link=f"/projects/{project.id}/",
                    notification_type=NotificationType.MENTOR_FEEDBACK,
                    project=project
                )

    return True, "Cập nhật trạng thái đồ án thành công"

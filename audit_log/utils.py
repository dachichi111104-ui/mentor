from audit_log.models import ActivityLog

def log_action(user, action, entity_type, entity_id, description, request=None, project=None):
    """
    Unified Audit Logging Helper for ProjectHub AI
    """
    ip_address = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')

    if not project and entity_id:
        try:
            if entity_type == 'Project':
                from projects.models import Project
                project = Project.objects.filter(id=entity_id).first()
            elif entity_type in ['Task', 'TaskComment']:
                from tasks.models import Task
                t = Task.objects.filter(id=entity_id).first()
                if t:
                    project = t.project
            elif entity_type == 'Milestone':
                from milestones.models import Milestone
                m = Milestone.objects.filter(id=entity_id).first()
                if m:
                    project = m.project
            elif entity_type == 'Document':
                from documents.models import Document
                d = Document.objects.filter(id=entity_id).first()
                if d:
                    project = d.project
            elif entity_type == 'Feedback':
                from reviews.models import Feedback
                fb = Feedback.objects.filter(id=entity_id).first()
                if fb:
                    project = fb.project
        except Exception:
            pass

    return ActivityLog.objects.create(
        user=user if (user and user.is_authenticated) else None,
        project=project,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else '',
        description=description,
        ip_address=ip_address
    )

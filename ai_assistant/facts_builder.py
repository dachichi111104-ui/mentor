import json
from django.utils import timezone
from projects.models import Project
from audit_log.models import ActivityLog
from reviews.models import Feedback

def build_facts(project: Project, days: int = 14) -> dict:
    """
    Builds project-bound fact pack dictionary from ORM data.
    """
    now = timezone.now()
    today = now.date()
    start_period = now - timezone.timedelta(days=days)

    total_days = (project.end_date - project.start_date).days if (project.start_date and project.end_date) else 90
    days_passed = (today - project.start_date).days if project.start_date else 0
    days_left = max((project.end_date - today).days, 0) if project.end_date else 0
    elapsed_pct = min(max(int((days_passed / total_days) * 100), 0), 100) if total_days > 0 else 0

    project_info = {
        'id': project.id,
        'code': project.code,
        'name': project.name,
        'description': (project.description or "")[:600],
        'technology': project.technology or "Chưa cập nhật",
        'category': project.category or "WEB",
        'status': project.status,
        'progress': project.progress,
        'start_date': project.start_date.strftime('%Y-%m-%d') if project.start_date else None,
        'end_date': project.end_date.strftime('%Y-%m-%d') if project.end_date else None,
        'days_left': days_left,
        'elapsed_pct': elapsed_pct,
        'mentor_name': project.mentor.display_name if project.mentor else None,
        'mentor_status': project.mentor_status
    }

    # Members
    members_data = []
    for mem in project.memberships.filter(status='ACCEPTED'):
        u = mem.user
        assigned_tasks = project.tasks.filter(assignee=u)
        open_tasks = assigned_tasks.exclude(status='DONE').count()
        done_tasks = assigned_tasks.filter(status='DONE').count()
        overdue_tasks = sum(1 for t in assigned_tasks if t.is_overdue)

        hours_14d = sum(t.hours_spent for t in u.time_logs.filter(project=project, created_at__gte=start_period))

        members_data.append({
            'user_id': u.id,
            'name': u.display_name,
            'role': mem.role,
            'open_tasks': open_tasks,
            'done_tasks': done_tasks,
            'overdue_tasks': overdue_tasks,
            'hours_14d': float(hours_14d)
        })

    # Milestones
    milestones_data = []
    for m in project.milestones.all():
        days_until = (m.due_date - today).days if m.due_date else 99
        t_all = m.tasks.count()
        t_done = m.tasks.filter(status='DONE').count()
        milestones_data.append({
            'id': m.id,
            'name': m.title,
            'due_date': m.due_date.strftime('%Y-%m-%d') if m.due_date else None,
            'status': 'COMPLETED' if m.is_completed else ('OVERDUE' if days_until < 0 else 'IN_PROGRESS'),
            'progress': m.progress,
            'total_tasks': t_all,
            'done_tasks': t_done,
            'days_until': days_until
        })

    # Tasks
    all_tasks = project.tasks.select_related('assignee', 'milestone').all()
    todo_list = []
    in_prog_list = []
    review_list = []
    overdue_list = []
    stuck_list = []
    recent_done_list = []

    for t in all_tasks:
        item = {
            'id': t.id,
            'title': t.title[:80],
            'status': t.status,
            'priority': t.priority,
            'assignee': t.assignee.display_name if t.assignee else 'Unassigned',
            'due': t.due_date.strftime('%Y-%m-%d') if t.due_date else None,
            'days_in_status': t.days_in_status,
            'milestone_id': t.milestone.id if t.milestone else None
        }

        if t.status == 'TODO':
            todo_list.append(item)
        elif t.status == 'IN_PROGRESS':
            in_prog_list.append(item)
            if t.days_in_status >= 3:
                stuck_list.append(item)
        elif t.status == 'REVIEW':
            review_list.append(item)
            if t.days_in_status >= 2:
                stuck_list.append(item)
        elif t.status == 'DONE':
            if t.completed_at and t.completed_at >= start_period:
                recent_done_list.append(item)

        if t.is_overdue:
            overdue_list.append(item)

    tasks_data = {
        'todo': todo_list[:12],
        'in_progress': in_prog_list[:12],
        'review': review_list[:12],
        'overdue': overdue_list[:12],
        'stuck': stuck_list[:12],
        'recent_done': recent_done_list[:8]
    }

    # Activities (via project FK or entity_id)
    activity_logs = ActivityLog.objects.filter(
        project=project,
        created_at__gte=start_period
    ).order_by('-created_at')[:10]

    recent_activities = [
        f"[{log.created_at.strftime('%d/%m %H:%M')}] {log.user.display_name if log.user else 'System'}: {log.description}"
        for log in activity_logs
    ]

    # Documents
    docs_data = list(project.documents.values('id', 'title', 'file_type', 'current_version')[:10])

    # Feedbacks
    recent_feedbacks = list(Feedback.objects.filter(project=project).order_by('-created_at')[:5].values(
        'id', 'content', 'rating', 'status', 'created_at'
    ))
    unres_count = Feedback.objects.filter(project=project, status='NEED_REVISION').count()

    facts = {
        'project': project_info,
        'members': members_data,
        'milestones': milestones_data,
        'tasks': tasks_data,
        'activity_14d': recent_activities,
        'documents': docs_data,
        'feedbacks': recent_feedbacks,
        'unresolved_feedback_count': unres_count
    }

    return facts

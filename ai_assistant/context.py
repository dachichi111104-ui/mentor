import hashlib
import json
from datetime import timedelta
from django.utils import timezone
from tasks.models import Task, TaskStatus
from milestones.models import Milestone, MilestoneStatus
from audit_log.models import ActivityLog
from reviews.models import Feedback

def build_project_context(project, days=14):
    """
    Builds a deterministic, isolated data fact pack for a specific project.
    Contains ONLY factual data from PostgreSQL for this project.
    Used as input context for LLM prompts and rule calculation.
    """
    if not project:
        return {}

    now = timezone.now()
    today = now.date()
    start_period = now - timedelta(days=days)

    # 1. Project Basic Meta
    project_info = {
        'id': project.id,
        'code': project.code,
        'name': project.name,
        'description': project.description or '',
        'category': project.get_category_display() if hasattr(project, 'get_category_display') else str(project.category),
        'status': project.get_status_display() if hasattr(project, 'get_status_display') else str(project.status),
        'progress': project.progress,
        'start_date': project.start_date.strftime('%Y-%m-%d') if project.start_date else '',
        'due_date': project.end_date.strftime('%Y-%m-%d') if project.end_date else '',
        'mentor_name': project.mentor.display_name if project.mentor else 'Chưa có',
        'mentor_status': project.get_mentor_status_display() if hasattr(project, 'get_mentor_status_display') else str(project.mentor_status)
    }

    # 2. Members & Workload
    memberships = project.memberships.filter(status='ACCEPTED').select_related('user')
    members_data = []
    for mem in memberships:
        u = mem.user
        assigned_tasks = project.tasks.filter(assignee=u)
        open_count = assigned_tasks.exclude(status=TaskStatus.DONE).count()
        done_count = assigned_tasks.filter(status=TaskStatus.DONE).count()
        overdue_count = assigned_tasks.filter(due_date__lt=today).exclude(status=TaskStatus.DONE).count()
        
        members_data.append({
            'user_id': u.id,
            'name': u.display_name,
            'role': mem.get_role_display() if hasattr(mem, 'get_role_display') else mem.role,
            'open_tasks': open_count,
            'completed_tasks': done_count,
            'overdue_tasks': overdue_count
        })

    # 3. Milestones
    milestones = project.milestones.all().order_by('due_date')
    milestones_data = []
    milestones_without_tasks = []
    for m in milestones:
        total_t = m.tasks.count()
        done_t = m.tasks.filter(status=TaskStatus.DONE).count()
        m_info = {
            'id': m.id,
            'name': m.name,
            'due_date': m.due_date.strftime('%Y-%m-%d') if m.due_date else '',
            'status': m.get_status_display() if hasattr(m, 'get_status_display') else str(m.status),
            'progress': m.progress_percentage,
            'total_tasks': total_t,
            'done_tasks': done_t
        }
        milestones_data.append(m_info)
        if total_t == 0 and m.status != MilestoneStatus.COMPLETED:
            milestones_without_tasks.append(m.name)

    # 4. Tasks Summary & Critical lists
    all_tasks = project.tasks.all()
    todo_tasks = list(all_tasks.filter(status=TaskStatus.TODO).values('id', 'title', 'priority'))
    in_progress_tasks = list(all_tasks.filter(status=TaskStatus.IN_PROGRESS).values('id', 'title', 'priority', 'assignee__first_name'))
    review_tasks = list(all_tasks.filter(status=TaskStatus.REVIEW).values('id', 'title', 'priority', 'assignee__first_name'))
    done_tasks = list(all_tasks.filter(status=TaskStatus.DONE).values('id', 'title'))

    overdue_tasks = []
    for t in all_tasks.filter(due_date__lt=today).exclude(status=TaskStatus.DONE):
        days_overdue = (today - t.due_date).days
        overdue_tasks.append({
            'id': t.id,
            'title': t.title,
            'due_date': t.due_date.strftime('%Y-%m-%d'),
            'days_overdue': days_overdue,
            'assignee': t.assignee.display_name if t.assignee else 'Chưa gán'
        })

    stuck_tasks = []
    for t in all_tasks.filter(status__in=[TaskStatus.IN_PROGRESS, TaskStatus.REVIEW]):
        days_stuck = (now - t.updated_at).days
        if days_stuck >= 3:
            stuck_tasks.append({
                'id': t.id,
                'title': t.title,
                'status': t.get_status_display(),
                'days_stuck': days_stuck,
                'assignee': t.assignee.display_name if t.assignee else 'Chưa gán'
            })

    upcoming_tasks = []
    for t in all_tasks.filter(due_date__gte=today, due_date__lte=today + timedelta(days=7)).exclude(status=TaskStatus.DONE):
        days_left = (t.due_date - today).days
        upcoming_tasks.append({
            'id': t.id,
            'title': t.title,
            'due_date': t.due_date.strftime('%Y-%m-%d'),
            'days_left': days_left
        })

    # 5. Recent Activity Logs (Filtered strictly by project)
    activity_logs = ActivityLog.objects.filter(
        entity_type='Project',
        entity_id=str(project.id),
        created_at__gte=start_period
    ).order_by('-created_at')[:10]
    
    recent_activities = [
        f"[{log.created_at.strftime('%d/%m %H:%i')}] {log.user.display_name if log.user else 'System'}: {log.description}"
        for log in activity_logs
    ]

    # 6. Documents
    documents_data = list(project.documents.values('id', 'title', 'file_type', 'current_version'))

    # 7. Recent Mentor Feedback
    recent_feedbacks = list(Feedback.objects.filter(project=project).order_by('-created_at')[:5].values(
        'id', 'content', 'rating', 'status', 'created_at'
    ))

    context_dict = {
        'project': project_info,
        'members': members_data,
        'milestones': milestones_data,
        'milestones_without_tasks': milestones_without_tasks,
        'tasks': {
            'total_count': all_tasks.count(),
            'todo': todo_tasks,
            'in_progress': in_progress_tasks,
            'review': review_tasks,
            'done_count': len(done_tasks),
            'recent_done': done_tasks[:5],
            'overdue': overdue_tasks,
            'stuck': stuck_tasks,
            'upcoming': upcoming_tasks
        },
        'activities': recent_activities,
        'documents': documents_data,
        'feedbacks': recent_feedbacks
    }

    # Hash context string for cache key verification
    context_bytes = json.dumps(context_dict, sort_keys=True, default=str).encode('utf-8')
    context_hash = hashlib.md5(context_bytes).hexdigest()
    context_dict['context_hash'] = context_hash

    return context_dict

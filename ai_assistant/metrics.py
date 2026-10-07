from datetime import timedelta
from django.utils import timezone
from tasks.models import TaskStatus
from milestones.models import MilestoneStatus
from audit_log.models import ActivityLog

def calculate_project_metrics(project):
    """
    Calculates deterministic quantitative metrics and a overall Risk Score (0-100).
    Rule-based, facts-only calculation.
    """
    if not project:
        return {'risk_score': 0, 'risks': [], 'velocity': 0, 'health_badge': 'NORMAL'}

    today = timezone.now().date()
    now = timezone.now()
    risks = []
    risk_score = 0

    all_tasks = project.tasks.all()
    total_tasks = all_tasks.count()
    completed_tasks = all_tasks.filter(status=TaskStatus.DONE).count()

    # Velocity: tasks completed in last 7 days
    week_ago = now - timedelta(days=7)
    velocity_7d = all_tasks.filter(status=TaskStatus.DONE, updated_at__gte=week_ago).count()

    # 1. Overdue Tasks Rule (Max 35 pts)
    overdue_tasks = all_tasks.filter(due_date__lt=today).exclude(status=TaskStatus.DONE)
    overdue_count = overdue_tasks.count()
    if overdue_count > 0:
        added_score = min(35, overdue_count * 10)
        risk_score += added_score
        for t in overdue_tasks:
            days_overdue = (today - t.due_date).days
            risks.append({
                'type': 'OVERDUE_TASK',
                'severity': 'CRITICAL',
                'task_id': t.id,
                'title': t.title,
                'days_overdue': days_overdue,
                'detail': f'Task "{t.title}" đã quá hạn {days_overdue} ngày (Hạn chót: {t.due_date.strftime("%d/%m/%Y")}).',
                'recommendation': f'Cần ưu tiên hoàn thành ngay task "{t.title}" hoặc gia hạn deadline hợp lý.'
            })

    # 2. Stuck Tasks Rule (Max 25 pts)
    stuck_tasks = all_tasks.filter(status__in=[TaskStatus.IN_PROGRESS, TaskStatus.REVIEW])
    stuck_count = 0
    for t in stuck_tasks:
        days_stuck = (now - t.updated_at).days
        if days_stuck >= 3:
            stuck_count += 1
            risks.append({
                'type': 'STUCK_TASK',
                'severity': 'CRITICAL' if days_stuck >= 5 else 'WARNING',
                'task_id': t.id,
                'title': t.title,
                'status': t.get_status_display(),
                'days_stuck': days_stuck,
                'detail': f'Task "{t.title}" nằm ở trạng thái [{t.get_status_display()}] đã {days_stuck} ngày chưa có hoạt động cập nhật mới.',
                'recommendation': 'Phân rã task nhỏ hơn hoặc họp nhóm tháo gỡ vướng mắc kỹ thuật.'
            })
    if stuck_count > 0:
        risk_score += min(25, stuck_count * 8)

    # 3. Milestone Risk Rule (Max 20 pts)
    milestones = project.milestones.all()
    for m in milestones:
        if m.due_date and m.status != MilestoneStatus.COMPLETED:
            days_until = (m.due_date - today).days
            prog = m.progress_percentage
            if 0 <= days_until <= 7 and prog < 50:
                risk_score += 15
                risks.append({
                    'type': 'MILESTONE_RISK',
                    'severity': 'WARNING',
                    'milestone_id': m.id,
                    'title': m.name,
                    'progress': prog,
                    'days_until': days_until,
                    'detail': f'Mốc tiến độ "{m.name}" chỉ còn {days_until} ngày nhưng tiến độ thực tế mới đạt {prog}%.',
                    'recommendation': 'Tập trung toàn bộ nhân lực cho mốc này trước ngày hạn chót.'
                })

    # 4. Inactive Project Rule (Max 10 pts) - Fixed entity_type check
    recent_activity = ActivityLog.objects.filter(
        entity_type='Project',
        entity_id=str(project.id),
        created_at__gte=now - timedelta(days=7)
    ).exists()
    if not recent_activity and total_tasks > 0:
        risk_score += 10
        risks.append({
            'type': 'INACTIVE_PROJECT',
            'severity': 'INFO',
            'detail': f'Đồ án [{project.code}] không phát sinh nhật ký hoạt động nào trên hệ thống trong 7 ngày qua.',
            'recommendation': 'Nhóm sinh viên cần cập nhật tiến độ công việc hàng ngày trên bảng Kanban.'
        })

    # 5. Workload Overload Rule (Max 10 pts)
    memberships = project.memberships.filter(status='ACCEPTED')
    for mem in memberships:
        u = mem.user
        assigned_cnt = all_tasks.filter(assignee=u).exclude(status=TaskStatus.DONE).count()
        if assigned_cnt >= 5:
            risk_score += 5
            risks.append({
                'type': 'MEMBER_OVERLOAD',
                'severity': 'WARNING',
                'user': u.display_name,
                'count': assigned_cnt,
                'detail': f'Thành viên {u.display_name} đang gánh {assigned_cnt} công việc dở dang.',
                'recommendation': 'Điều chuyển bớt công việc sang các thành viên khác trong nhóm.'
            })

    risk_score = min(100, risk_score)

    health_badge = 'HEALTHY' if risk_score < 25 else 'WARNING' if risk_score < 60 else 'CRITICAL'

    return {
        'risk_score': risk_score,
        'health_badge': health_badge,
        'risks': risks,
        'velocity_7d': velocity_7d,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'completion_rate': int((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0
    }

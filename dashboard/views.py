import csv
from pathlib import Path
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Q, Count, Avg, F
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone

from accounts.models import User, UserRole, UserStatus
from projects.models import Project, ProjectStatus
from projects.permissions import visible_projects, require_can, can
from tasks.models import Task, TaskStatus, TaskPriority
from milestones.models import Milestone, MilestoneStatus
from documents.models import Document
from audit_log.models import ActivityLog, ActionType
from audit_log.utils import log_action
from notifications.models import Notification
from dashboard.models import TimeLog

def landing_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'dashboard/landing.html')

@login_required
def dashboard_view(request):
    user = request.user
    if user.is_admin_user:
        return admin_dashboard_view(request)
    elif user.is_mentor:
        return mentor_dashboard_view(request)
    else:
        return student_dashboard_view(request)

@login_required
def student_dashboard_view(request):
    user = request.user
    my_projects = visible_projects(user)
    my_tasks = Task.objects.filter(project__in=my_projects, assignee=user)

    active_projects_count = my_projects.filter(status=ProjectStatus.IN_PROGRESS).count()
    completed_projects_count = my_projects.filter(status=ProjectStatus.COMPLETED).count()

    in_progress_tasks = my_tasks.filter(status=TaskStatus.IN_PROGRESS)
    overdue_tasks = [t for t in my_tasks if t.is_overdue]

    upcoming_milestones = Milestone.objects.filter(project__in=my_projects, status__in=['PENDING', 'IN_PROGRESS']).order_by('due_date')[:5]
    recent_activities = ActivityLog.objects.filter(project__in=my_projects).order_by('-created_at')[:8]

    total_tasks_count = my_tasks.count()
    done_tasks_count = my_tasks.filter(status=TaskStatus.DONE).count()
    pending_tasks_count = total_tasks_count - done_tasks_count
    done_percent = int((done_tasks_count / total_tasks_count * 100)) if total_tasks_count > 0 else 0

    context = {
        'total_projects': my_projects.count(),
        'active_projects_count': active_projects_count,
        'completed_projects_count': completed_projects_count,
        'total_tasks_count': total_tasks_count,
        'done_tasks_count': done_tasks_count,
        'pending_tasks_count': pending_tasks_count,
        'done_percent': done_percent,
        'my_projects': my_projects[:4],
        'my_tasks': my_tasks.exclude(status=TaskStatus.DONE)[:6],
        'in_progress_tasks_count': in_progress_tasks.count(),
        'overdue_tasks_count': len(overdue_tasks),
        'upcoming_milestones': upcoming_milestones,
        'recent_activities': recent_activities,
    }
    return render(request, 'dashboard/student_dashboard.html', context)

@login_required
def mentor_dashboard_view(request):
    user = request.user
    mentored_projects = visible_projects(user)
    pending_mentor_invites = Project.objects.filter(mentor=user, mentor_status='PENDING')

    total_mentored = mentored_projects.count()
    active_projects = mentored_projects.filter(status=ProjectStatus.IN_PROGRESS)
    review_needed_projects = mentored_projects.filter(status=ProjectStatus.REVIEW)

    pending_review_tasks = Task.objects.filter(project__in=mentored_projects, status=TaskStatus.REVIEW)

    context = {
        'total_mentored': total_mentored,
        'active_projects': active_projects,
        'review_needed_projects': review_needed_projects,
        'mentored_projects_list': mentored_projects,
        'pending_mentor_invites': pending_mentor_invites,
        'pending_review_tasks': pending_review_tasks[:8],
    }
    return render(request, 'dashboard/mentor_dashboard.html', context)

@login_required
@require_can('user.manage')
def admin_dashboard_view(request):
    total_users = User.objects.count()
    students_count = User.objects.filter(role=UserRole.STUDENT).count()
    mentors_count = User.objects.filter(role=UserRole.MENTOR).count()

    total_projects = Project.objects.count()
    active_projects = Project.objects.filter(status=ProjectStatus.IN_PROGRESS).count()
    completed_projects = Project.objects.filter(status=ProjectStatus.COMPLETED).count()

    total_tasks = Task.objects.count()
    done_tasks = Task.objects.filter(status=TaskStatus.DONE).count()

    recent_users = User.objects.all().order_by('-date_joined')[:5]
    recent_projects = Project.objects.all().order_by('-created_at')[:5]
    recent_logs = ActivityLog.objects.all().order_by('-created_at')[:8]

    context = {
        'total_users': total_users,
        'students_count': students_count,
        'mentors_count': mentors_count,
        'total_projects': total_projects,
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'total_tasks': total_tasks,
        'done_tasks': done_tasks,
        'recent_users': recent_users,
        'recent_projects': recent_projects,
        'recent_logs': recent_logs,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)

@login_required
@require_can('user.manage')
def admin_users_view(request):
    users = User.objects.all().order_by('-date_joined')
    pending_mentors = User.objects.filter(role=UserRole.MENTOR, status=UserStatus.PENDING_APPROVAL)
    return render(request, 'dashboard/admin_users.html', {
        'users': users,
        'pending_mentors': pending_mentors
    })

@login_required
@require_POST
@require_can('user.lock')
def admin_toggle_user_status_view(request, user_id):
    user_to_toggle = get_object_or_404(User, id=user_id)

    if user_to_toggle == request.user:
        messages.error(request, 'Bạn không thể tự khóa tài khoản của chính mình!')
        return redirect('admin_users')

    if user_to_toggle.is_admin_user and user_to_toggle.status == UserStatus.ACTIVE:
        active_admins = User.objects.filter(role=UserRole.ADMIN, status=UserStatus.ACTIVE).count()
        if active_admins <= 1:
            messages.error(request, 'Hệ thống cần tối thiểu 1 Quản trị viên đang hoạt động!')
            return redirect('admin_users')

    if user_to_toggle.status == UserStatus.ACTIVE:
        user_to_toggle.status = UserStatus.SUSPENDED
        action_type = ActionType.LOCK_USER
        msg = f'Đã khóa tài khoản {user_to_toggle.username}'
    else:
        user_to_toggle.status = UserStatus.ACTIVE
        action_type = ActionType.UNLOCK_USER
        msg = f'Đã mở khóa tài khoản {user_to_toggle.username}'

    user_to_toggle.save()
    log_action(user=request.user, action=action_type, entity_type='User', entity_id=user_to_toggle.id, description=msg, request=request)
    messages.success(request, msg)
    return redirect('admin_users')

@login_required
@require_can('user.manage')
def admin_user_create_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        role = request.POST.get('role', UserRole.STUDENT)

        if not username or not email or not password:
            messages.error(request, 'Vui lòng nhập đầy đủ Tên đăng nhập, Email và Mật khẩu.')
            return redirect('admin_users')

        if User.objects.filter(username=username).exists():
            messages.error(request, f'Tên đăng nhập "{username}" đã tồn tại.')
            return redirect('admin_users')

        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        try:
            validate_password(password)
        except ValidationError as e:
            messages.error(request, "; ".join(e.messages))
            return redirect('admin_users')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=role,
            status=UserStatus.ACTIVE,
            first_name=request.POST.get('first_name', ''),
            last_name=request.POST.get('last_name', '')
        )
        log_action(user=request.user, action=ActionType.CREATE_USER, entity_type='User', entity_id=user.id, description=f"Tạo người dùng mới: {user.username}", request=request)
        messages.success(request, f'Đã tạo tài khoản {user.username} thành công.')
    return redirect('admin_users')

@login_required
@require_POST
@require_can('user.manage')
def admin_user_change_role_view(request, user_id):
    user_to_change = get_object_or_404(User, id=user_id)
    new_role = request.POST.get('role')

    if user_to_change == request.user and new_role != UserRole.ADMIN:
        messages.error(request, 'Bạn không thể tự hạ quyền Admin của chính mình!')
        return redirect('admin_users')

    if user_to_change.role == UserRole.ADMIN and new_role != UserRole.ADMIN:
        active_admins = User.objects.filter(role=UserRole.ADMIN, status=UserStatus.ACTIVE).count()
        if active_admins <= 1:
            messages.error(request, 'Hệ thống cần tối thiểu 1 Quản trị viên đang hoạt động!')
            return redirect('admin_users')

    if new_role in UserRole.values:
        old_role = user_to_change.role
        user_to_change.role = new_role
        user_to_change.save()
        log_action(user=request.user, action=ActionType.CHANGE_ROLE, entity_type='User', entity_id=user_to_change.id, description=f"Đổi vai trò {user_to_change.username} từ [{old_role}] sang [{new_role}]", request=request)
        messages.success(request, f'Đã đổi vai trò {user_to_change.username} thành {user_to_change.get_role_display()}.')
    return redirect('admin_users')

from notifications.services import notify
from notifications.models import NotificationType

@login_required
@require_POST
@require_can('user.approve_mentor')
def admin_approve_user_view(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    target_user.status = UserStatus.ACTIVE
    target_user.save()

    log_action(
        user=request.user,
        action=ActionType.APPROVE_USER,
        entity_type='User',
        entity_id=target_user.id,
        description=f'Quản trị viên phê duyệt tài khoản Giảng viên: {target_user.username}',
        request=request
    )

    notify(
        recipient=target_user,
        sender=request.user,
        title='Tài khoản đã được phê duyệt',
        message='Tài khoản Giảng viên của bạn đã được Quản trị viên HVHK phê duyệt. Bạn có thể đăng nhập ngay bây giờ.',
        link='/login/',
        notification_type=NotificationType.SYSTEM
    )

    messages.success(request, f'Đã phê duyệt tài khoản Giảng viên: {target_user.display_name}')
    return redirect('admin_users')

@login_required
@require_POST
@require_can('user.approve_mentor')
def admin_reject_user_view(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    reason = request.POST.get('reason', '').strip()
    if not reason:
        messages.error(request, 'Vui lòng nhập lý do từ chối phê duyệt.')
        return redirect('admin_users')

    target_user.status = UserStatus.SUSPENDED
    target_user.save()

    log_action(
        user=request.user,
        action=ActionType.REJECT_USER,
        entity_type='User',
        entity_id=target_user.id,
        description=f'Từ chối phê duyệt Giảng viên {target_user.username}. Lý do: {reason}',
        request=request
    )

    messages.warning(request, f'Đã từ chối tài khoản Giảng viên: {target_user.display_name}. Lý do: {reason}')
    return redirect('admin_users')

@login_required
@require_can('user.manage')
def admin_audit_log_view(request):
    logs = ActivityLog.objects.all().order_by('-created_at')[:100]
    return render(request, 'dashboard/admin_audit_logs.html', {'logs': logs})

@login_required
def global_search_view(request):
    q = request.GET.get('q', '').strip()
    return render(request, 'dashboard/search_results.html', {'query': q})

@login_required
def global_search_json_view(request):
    q = request.GET.get('q', '').strip()
    if not q or len(q) < 2:
        return JsonResponse({'status': 'success', 'results': {'projects': [], 'tasks': [], 'members': [], 'documents': []}})

    user = request.user
    projects = visible_projects(user)

    p_matches = projects.filter(Q(name__icontains=q) | Q(code__icontains=q))[:5]
    p_data = [{'id': p.id, 'code': p.code, 'name': p.name, 'url': f'/projects/{p.id}/'} for p in p_matches]

    t_matches = Task.objects.filter(project__in=projects).filter(Q(title__icontains=q) | Q(description__icontains=q))[:5]
    t_data = [{'id': t.id, 'title': t.title, 'project_code': t.project.code, 'url': f'/tasks/{t.id}/'} for t in t_matches]

    visible_user_ids = set()
    for proj in projects:
        visible_user_ids.add(proj.created_by_id)
        if proj.mentor_id:
            visible_user_ids.add(proj.mentor_id)
        for m in proj.memberships.all():
            visible_user_ids.add(m.user_id)

    m_matches = User.objects.filter(id__in=visible_user_ids).filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(student_id__icontains=q))[:5]
    m_data = [{'id': m.id, 'name': m.display_name, 'role': m.get_role_display(), 'url': f'/profile/'} for m in m_matches]

    d_matches = Document.objects.filter(project__in=projects).filter(Q(title__icontains=q))[:5]
    d_data = [{'id': d.id, 'title': d.title, 'project_code': d.project.code, 'url': f'/documents/{d.id}/view/'} for d in d_matches]

    return JsonResponse({
        'status': 'success',
        'results': {
            'projects': p_data,
            'tasks': t_data,
            'members': m_data,
            'documents': d_data
        }
    })

@login_required
@require_POST
def time_tracker_start_view(request):
    project_id = request.POST.get('project_id')
    task_id = request.POST.get('task_id')
    note = request.POST.get('note', '')

    projects = visible_projects(request.user)

    if project_id:
        project = projects.filter(id=project_id).first()
        if not project:
            return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền truy cập đồ án này.'}, status=403)
    else:
        project = projects.first()
        if not project:
            return JsonResponse({'status': 'error', 'message': 'Không tìm thấy đồ án để theo dõi thời gian.'}, status=400)

    if not can(request.user, 'timelog.create', project):
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền bấm giờ trong đồ án này.'}, status=403)

    active_log = TimeLog.objects.filter(user=request.user, ended_at__isnull=True).first()
    if active_log:
        active_log.ended_at = timezone.now()
        active_log.duration = int((active_log.ended_at - active_log.started_at).total_seconds())
        active_log.save()

    task = Task.objects.filter(id=task_id, project=project).first() if task_id else None

    log = TimeLog.objects.create(
        user=request.user,
        project=project,
        task=task,
        started_at=timezone.now(),
        note=note
    )
    return JsonResponse({
        'status': 'success',
        'log': {
            'id': log.id,
            'project_name': log.project.name,
            'task_title': log.task.title if log.task else 'Công việc chung',
            'started_at': log.started_at.isoformat(),
        }
    })

@login_required
@require_POST
def time_tracker_stop_view(request):
    active_log = TimeLog.objects.filter(user=request.user, ended_at__isnull=True).first()
    if not active_log:
        return JsonResponse({'status': 'error', 'message': 'Không có trình theo dõi thời gian nào đang chạy.'}, status=400)

    active_log.ended_at = timezone.now()
    active_log.duration = int((active_log.ended_at - active_log.started_at).total_seconds())
    active_log.save()

    return JsonResponse({
        'status': 'success',
        'message': 'Đã dừng theo dõi thời gian và ghi lại nhật ký thành công!',
        'duration': active_log.duration
    })

@login_required
def time_tracker_status_view(request):
    today = timezone.now().date()
    today_logs = TimeLog.objects.filter(user=request.user, started_at__date=today)
    today_seconds = sum(l.duration or 0 for l in today_logs)

    active_log = TimeLog.objects.filter(user=request.user, ended_at__isnull=True).first()
    if active_log:
        elapsed = int((timezone.now() - active_log.started_at).total_seconds())
        return JsonResponse({
            'status': 'success',
            'is_running': True,
            'today_seconds': today_seconds,
            'log': {
                'id': active_log.id,
                'project_id': active_log.project.id,
                'project_name': active_log.project.name,
                'task_title': active_log.task.title if active_log.task else 'Công việc chung',
                'started_at': active_log.started_at.isoformat(),
                'elapsed_seconds': elapsed
            }
        })

    last_log = TimeLog.objects.filter(user=request.user, ended_at__isnull=False).order_by('-ended_at').first()
    last_duration = last_log.duration if last_log else 0

    return JsonResponse({
        'status': 'success',
        'is_running': False,
        'today_seconds': today_seconds,
        'last_duration': last_duration
    })

@login_required
def dashboard_analytics_json_view(request):
    user = request.user
    projects = visible_projects(user)
    tasks = Task.objects.filter(project__in=projects)

    total_t = tasks.count()
    done_t = tasks.filter(status=TaskStatus.DONE).count()
    completion_rate = int((done_t / total_t * 100)) if total_t > 0 else 0

    today = timezone.now().date()
    days = [(today - timezone.timedelta(days=i)) for i in range(6, -1, -1)]
    weekly_labels = [d.strftime('%d/%m') for d in days]
    weekly_completed = []

    for d in days:
        cnt = tasks.filter(status=TaskStatus.DONE, completed_at__date=d).count()
        weekly_completed.append(cnt)

    status_counts = {
        'TODO': tasks.filter(status=TaskStatus.TODO).count(),
        'IN_PROGRESS': tasks.filter(status=TaskStatus.IN_PROGRESS).count(),
        'REVIEW': tasks.filter(status=TaskStatus.REVIEW).count(),
        'DONE': done_t,
    }

    return JsonResponse({
        'status': 'success',
        'weekly_labels': weekly_labels,
        'weekly_completed': weekly_completed,
        'completion_rate': completion_rate,
        'total_tasks': total_t,
        'done_tasks': done_t,
        'status_counts': status_counts
    })

@login_required
def analytics_page_view(request):
    user = request.user
    my_projects = visible_projects(user)
    return render(request, 'dashboard/analytics.html', {'my_projects': my_projects})

@login_required
def analytics_data_json_view(request):
    period = request.GET.get('period', '30D')
    days_map = {'7D': 7, '30D': 30, '90D': 90}
    days = days_map.get(period, 30)

    user = request.user
    projects = visible_projects(user)

    project_id = request.GET.get('project_id')
    if project_id:
        projects = projects.filter(id=project_id)

    tasks = Task.objects.filter(project__in=projects)

    cutoff_date = timezone.now() - timezone.timedelta(days=days)
    period_tasks = tasks.filter(created_at__gte=cutoff_date)
    completed_in_period = period_tasks.filter(status=TaskStatus.DONE).count()

    logs = TimeLog.objects.filter(project__in=projects, started_at__gte=cutoff_date)
    total_seconds = sum(l.duration or 0 for l in logs)
    total_hours = round(total_seconds / 3600.0, 1)

    done_with_due = tasks.filter(status=TaskStatus.DONE, due_date__isnull=False)
    ontime_count = sum(1 for t in done_with_due if t.completed_at and t.completed_at.date() <= t.due_date)
    ontime_rate = int((ontime_count / done_with_due.count() * 100)) if done_with_due.exists() else 0

    # Average cycle time (guaranteed non-negative)
    valid_done_tasks = [t for t in tasks.filter(status=TaskStatus.DONE, completed_at__isnull=False) if t.completed_at >= t.created_at]
    if valid_done_tasks:
        total_cycle_days = sum((t.completed_at - t.created_at).total_seconds() / 86400.0 for t in valid_done_tasks)
        avg_days = max(0.0, total_cycle_days / len(valid_done_tasks))
        avg_cycle_time = f"{round(avg_days, 1)} ngày"
    else:
        avg_cycle_time = "-"

    # Top contributors in visible projects
    visible_user_ids = set()
    for p in projects:
        visible_user_ids.add(p.created_by_id)
        for m in p.memberships.filter(status='ACCEPTED'):
            visible_user_ids.add(m.user_id)

    top_contribs = []
    for u in User.objects.filter(id__in=visible_user_ids):
        done_cnt = tasks.filter(assignee=u, status=TaskStatus.DONE).count()
        top_contribs.append({'name': u.display_name, 'avatar': u.get_avatar_url(), 'done_count': done_cnt})

    top_contribs.sort(key=lambda x: x['done_count'], reverse=True)
    top_contribs = top_contribs[:5]

    time_by_proj = []
    for p in projects[:5]:
        p_hrs = round(sum(l.duration or 0 for l in p.time_logs.filter(started_at__gte=cutoff_date)) / 3600.0, 1)
        time_by_proj.append({'name': p.name, 'hours': p_hrs})

    return JsonResponse({
        'status': 'success',
        'period': period,
        'kpis': {
            'completed_tasks': completed_in_period,
            'working_hours': total_hours,
            'ontime_rate': ontime_rate,
            'avg_cycle_time': avg_cycle_time
        },
        'top_contributors': top_contribs,
        'time_by_project': time_by_proj
    })

def _clean_csv_cell(val):
    if val is None:
        return ''
    s = str(val)
    if s and s[0] in ['=', '+', '-', '@', '\t', '\r']:
        return "'" + s
    return s

@login_required
def analytics_export_csv_view(request):
    user = request.user
    projects = visible_projects(user)
    tasks = Task.objects.filter(project__in=projects)

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="projecthub_analytics.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID Task', 'Tiêu đề Task', 'Đồ án', 'Người thực hiện', 'Trạng thái', 'Độ ưu tiên', 'Hạn chót'])

    for t in tasks:
        writer.writerow([
            _clean_csv_cell(t.id),
            _clean_csv_cell(t.title),
            _clean_csv_cell(t.project.name),
            _clean_csv_cell(t.assignee.display_name if t.assignee else 'Chưa giao'),
            _clean_csv_cell(t.get_status_display()),
            _clean_csv_cell(t.get_priority_display()),
            _clean_csv_cell(t.due_date.strftime('%d/%m/%Y') if t.due_date else '')
        ])

    return response

@login_required
def analytics_export_pdf_view(request):
    user = request.user
    projects = visible_projects(user)
    tasks = Task.objects.filter(project__in=projects).distinct()

    context = {
        'user': user,
        'projects': projects,
        'tasks': tasks,
        'generated_at': timezone.now().strftime('%H:%M %d/%m/%Y')
    }
    return render(request, 'dashboard/analytics_pdf_report.html', context)

def healthz_view(request):
    """
    Health check endpoint for production load balancers and Render health checks.
    Checks DB connectivity and MEDIA_ROOT write permissions.
    """
    from django.db import connection
    from django.conf import settings
    import tempfile

    db_ok = True
    try:
        connection.ensure_connection()
    except Exception:
        db_ok = False

    media_ok = True
    try:
        media_dir = getattr(settings, 'MEDIA_ROOT', None)
        if media_dir:
            test_file = Path(media_dir) / '.health_check_tmp'
            test_file.write_bytes(b'health_check')
            if test_file.exists():
                test_file.unlink()
    except Exception:
        media_ok = False

    status_code = 200 if (db_ok and media_ok) else 500
    return JsonResponse({
        'status': 'ok' if (db_ok and media_ok) else 'error',
        'db': 'ok' if db_ok else 'error',
        'media_storage': 'ok' if media_ok else 'error'
    }, status=status_code)


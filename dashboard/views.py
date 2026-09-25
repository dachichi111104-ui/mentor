from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.contrib import messages
from django.http import JsonResponse
from accounts.models import User, UserRole, UserStatus
from projects.models import Project, ProjectStatus
from tasks.models import Task, TaskStatus, TaskPriority
from milestones.models import Milestone, MilestoneStatus
from documents.models import Document
from audit_log.models import ActivityLog, ActionType
from notifications.models import Notification

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
    my_projects = Project.objects.filter(memberships__user=user)
    my_tasks = Task.objects.filter(assignee=user)
    
    active_projects_count = my_projects.filter(status=ProjectStatus.IN_PROGRESS).count()
    completed_projects_count = my_projects.filter(status=ProjectStatus.COMPLETED).count()
    
    in_progress_tasks = my_tasks.filter(status=TaskStatus.IN_PROGRESS)
    overdue_tasks = [t for t in my_tasks if t.is_overdue]
    
    upcoming_milestones = Milestone.objects.filter(project__in=my_projects).order_by('due_date')[:5]
    recent_activities = ActivityLog.objects.filter(user=user)[:8]

    context = {
        'total_projects': my_projects.count(),
        'active_projects_count': active_projects_count,
        'completed_projects_count': completed_projects_count,
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
    mentored_projects = Project.objects.filter(mentor=user, mentor_status='ACCEPTED')
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
def admin_dashboard_view(request):
    if not request.user.is_admin_user:
        return render(request, 'errors/403.html', status=403)
        
    total_users = User.objects.count()
    students_count = User.objects.filter(role=UserRole.STUDENT).count()
    mentors_count = User.objects.filter(role=UserRole.MENTOR).count()
    
    total_projects = Project.objects.count()
    active_projects = Project.objects.filter(status=ProjectStatus.IN_PROGRESS).count()
    completed_projects = Project.objects.filter(status=ProjectStatus.COMPLETED).count()
    
    audit_logs = ActivityLog.objects.all()[:10]
    
    context = {
        'total_users': total_users,
        'students_count': students_count,
        'mentors_count': mentors_count,
        'total_projects': total_projects,
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'audit_logs': audit_logs,
        'recent_projects': Project.objects.all()[:5],
    }
    return render(request, 'dashboard/admin_dashboard.html', context)

@login_required
def admin_users_view(request):
    if not request.user.is_admin_user:
        return render(request, 'errors/403.html', status=403)
        
    query = request.GET.get('q', '')
    role_filter = request.GET.get('role', '')
    
    users = User.objects.all().order_by('-created_at')
    if query:
        users = users.filter(Q(username__icontains=query) | Q(email__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query))
    if role_filter:
        users = users.filter(role=role_filter)
        
    context = {
        'users_list': users,
        'query': query,
        'role_filter': role_filter,
    }
    return render(request, 'dashboard/admin_users.html', context)

@login_required
def admin_toggle_user_status_view(request, user_id):
    if not request.user.is_admin_user:
        return render(request, 'errors/403.html', status=403)
        
    user_to_toggle = get_object_or_404(User, id=user_id)
    if user_to_toggle.status == UserStatus.ACTIVE:
        user_to_toggle.status = UserStatus.SUSPENDED
        messages.warning(request, f'Đã khóa tài khoản {user_to_toggle.display_name}.')
        action_type = ActionType.LOCK_USER
    else:
        user_to_toggle.status = UserStatus.ACTIVE
        messages.success(request, f'Đã mở khóa tài khoản {user_to_toggle.display_name}.')
        action_type = ActionType.UNLOCK_USER
        
    user_to_toggle.save()
    
    ActivityLog.objects.create(
        user=request.user,
        action=action_type,
        entity_type='User',
        entity_id=str(user_to_toggle.id),
        description=f'Thay đổi trạng thái tài khoản {user_to_toggle.username} sang {user_to_toggle.get_status_display()}',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    return redirect('admin_users')

@login_required
def admin_user_change_role_view(request, user_id):
    if not request.user.is_admin_user:
        return render(request, 'errors/403.html', status=403)
    if request.method == 'POST':
        user_obj = get_object_or_404(User, id=user_id)
        new_role = request.POST.get('role')
        if new_role in [UserRole.STUDENT, UserRole.MENTOR, UserRole.ADMIN]:
            old_role_display = user_obj.get_role_display()
            user_obj.role = new_role
            user_obj.save()
            messages.success(request, f'Đã đổi vai trò tài khoản {user_obj.username} từ {old_role_display} sang {user_obj.get_role_display()}.')
            ActivityLog.objects.create(
                user=request.user,
                action=ActionType.UPDATE_TASK,
                entity_type='UserRole',
                entity_id=str(user_obj.id),
                description=f'Cập nhật vai trò người dùng {user_obj.username} thành {user_obj.get_role_display()}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
    return redirect('admin_users')

@login_required
def admin_user_create_view(request):
    if not request.user.is_admin_user:
        return render(request, 'errors/403.html', status=403)
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role', UserRole.STUDENT)
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')

        if User.objects.filter(username=username).exists():
            messages.error(request, f'Tên đăng nhập "{username}" đã tồn tại.')
        elif not password or len(password) < 6:
            messages.error(request, 'Mật khẩu phải chứa ít nhất 6 ký tự.')
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=role,
                status=UserStatus.ACTIVE
            )
            messages.success(request, f'Tạo tài khoản {user.display_name} thành công!')
            ActivityLog.objects.create(
                user=request.user,
                action=ActionType.CREATE_TASK,
                entity_type='User',
                entity_id=str(user.id),
                description=f'Quản trị viên tạo tài khoản {user.get_role_display()} mới: {user.username}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
    return redirect('admin_users')

@login_required
def admin_audit_log_view(request):
    if not request.user.is_admin_user:
        return render(request, 'errors/403.html', status=403)
        
    logs = ActivityLog.objects.all().order_by('-created_at')[:100]
    return render(request, 'dashboard/admin_audit_log.html', {'logs': logs})

@login_required
def global_search_view(request):
    q = request.GET.get('q', '')
    if not q or len(q) < 2:
        return JsonResponse({'projects': [], 'tasks': [], 'documents': []})
    
    user = request.user
    if user.is_admin_user:
        accessible_projects = Project.objects.all()
    elif user.is_mentor:
        accessible_projects = Project.objects.filter(
            Q(mentor=user, mentor_status='ACCEPTED') | Q(created_by=user)
        )
    else:
        accessible_projects = Project.objects.filter(memberships__user=user)

    projects = accessible_projects.filter(Q(name__icontains=q) | Q(code__icontains=q))[:4]
    tasks = Task.objects.filter(project__in=accessible_projects, title__icontains=q)[:5]
    documents = Document.objects.filter(project__in=accessible_projects, title__icontains=q)[:4]
    
    p_data = [{'id': p.id, 'name': p.name, 'code': p.code} for p in projects]
    t_data = [{'id': t.id, 'title': t.title, 'project_id': t.project.id} for t in tasks]
    d_data = [{'id': d.id, 'title': d.title, 'project_id': d.project.id} for d in documents]
    
    return JsonResponse({'projects': p_data, 'tasks': t_data, 'documents': d_data})

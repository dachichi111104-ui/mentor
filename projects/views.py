from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone

from projects.models import Project, ProjectMember, ProjectStatus, ProjectCategory, MemberRole, MemberStatus, MentorStatus, Message
from projects.permissions import visible_projects, require_can, can
from projects.forms import ProjectForm
from accounts.models import User, UserRole, UserStatus
from audit_log.models import ActionType, ActivityLog
from audit_log.utils import log_action
from notifications.models import Notification, NotificationType
from notifications.services import notify
from tasks.models import Task, TaskStatus

@login_required
def project_list_view(request):
    user = request.user
    projects = visible_projects(user)

    status_filter = request.GET.get('status')
    category_filter = request.GET.get('category')
    query = request.GET.get('q', '').strip()

    if status_filter:
        projects = projects.filter(status=status_filter)
    if category_filter:
        projects = projects.filter(category=category_filter)
    if query:
        projects = projects.filter(Q(name__icontains=query) | Q(code__icontains=query) | Q(technology__icontains=query))

    pending_invites = None
    if user.is_mentor:
        pending_invites = Project.objects.filter(mentor=user, mentor_status=MentorStatus.PENDING)

    mentors = User.objects.filter(role=UserRole.MENTOR, status=UserStatus.ACTIVE)

    return render(request, 'projects/project_list.html', {
        'projects': projects.order_by('-created_at'),
        'status_filter': status_filter,
        'category_filter': category_filter,
        'query': query,
        'pending_invites': pending_invites,
        'mentors': mentors,
    })

@login_required
@require_can('project.view')
def project_detail_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    request.breadcrumb_obj = project

    members = project.memberships.all().select_related('user')
    tasks = project.tasks.all().select_related('assignee')
    milestones = project.milestones.all()
    documents = project.documents.all()
    feedbacks = project.feedbacks.all()
    activity_logs = ActivityLog.objects.filter(project=project)[:15]

    can_edit = can(request.user, 'project.edit', project)
    is_leader = (project.created_by == request.user)

    available_students = User.objects.filter(role=UserRole.STUDENT, status=UserStatus.ACTIVE).exclude(project_memberships__project=project)
    mentors = User.objects.filter(role=UserRole.MENTOR, status=UserStatus.ACTIVE)

    context = {
        'project': project,
        'members': members,
        'tasks': tasks,
        'milestones': milestones,
        'documents': documents,
        'feedbacks': feedbacks,
        'activity_logs': activity_logs,
        'can_edit': can_edit,
        'is_leader': is_leader,
        'available_students': available_students,
        'mentors': mentors,
    }
    return render(request, 'projects/project_detail.html', context)

@login_required
@require_POST
@require_can('project.create')
def project_create_view(request):
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('accept', '')
    form = ProjectForm(request.POST)

    if not form.is_valid():
        if is_ajax:
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        first_err = list(form.errors.values())[0][0] if form.errors else 'Vui lòng kiểm tra lại thông tin nhập!'
        messages.error(request, first_err)
        return redirect('project_list')

    project = form.save(commit=False)
    project.code = project.code.strip().upper()
    project.created_by = request.user
    project.status = ProjectStatus.PLANNING
    if project.mentor:
        project.mentor_status = MentorStatus.PENDING
    else:
        project.mentor_status = MentorStatus.NONE
    project.save()

    ProjectMember.objects.create(
        project=project,
        user=request.user,
        role=MemberRole.LEADER,
        status=MemberStatus.ACCEPTED
    )

    log_action(
        user=request.user,
        action=ActionType.CREATE_PROJECT,
        entity_type='Project',
        entity_id=project.id,
        description=f'Khởi tạo đồ án mới: {project.name} ({project.code})',
        project=project,
        request=request
    )

    messages.success(request, f'Tạo đồ án "{project.name}" thành công!')
    if is_ajax:
        return JsonResponse({'status': 'success', 'project_id': project.id, 'redirect_url': f'/projects/{project.id}/'})
    return redirect('project_detail', project_id=project.id)

@login_required
@require_POST
def project_edit_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not can(request.user, 'project.edit', project):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('accept', '')
    form = ProjectForm(request.POST, instance=project)

    if not form.is_valid():
        if is_ajax:
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        first_err = list(form.errors.values())[0][0] if form.errors else 'Dữ liệu không hợp lệ!'
        messages.error(request, first_err)
        return redirect('project_detail', project_id=project.id)

    old_mentor = project.mentor
    project = form.save(commit=False)
    project.code = project.code.strip().upper()
    if project.mentor and project.mentor != old_mentor:
        project.mentor_status = MentorStatus.PENDING
    project.save()

    log_action(
        user=request.user,
        action=ActionType.UPDATE_PROJECT,
        entity_type='Project',
        entity_id=project.id,
        description=f'Cập nhật thông tin đồ án: {project.name}',
        project=project,
        request=request
    )

    messages.success(request, f'Cập nhật đồ án "{project.name}" thành công!')
    if is_ajax:
        return JsonResponse({'status': 'success', 'project_id': project.id})
    return redirect('project_detail', project_id=project.id)

@login_required
@require_POST
def project_delete_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not can(request.user, 'project.delete', project):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    confirm_code = request.POST.get('confirm_code', '').strip().upper()
    if confirm_code != project.code and not request.user.is_admin_user:
        messages.error(request, f'Mã đồ án gõ lại không đúng ({confirm_code} ≠ {project.code}).')
        return redirect('project_detail', project_id=project.id)

    p_name = project.name
    p_id = project.id
    project.delete()

    log_action(
        user=request.user,
        action=ActionType.DELETE_PROJECT,
        entity_type='Project',
        entity_id=p_id,
        description=f'Xóa đồ án: "{p_name}"',
        request=request
    )
    messages.success(request, f'Đã xóa thành công đồ án "{p_name}".')
    return redirect('project_list')

@login_required
@require_POST
def project_add_member_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not can(request.user, 'project.member.add', project):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    user_id = request.POST.get('user_id')
    user_to_add = get_object_or_404(User, id=user_id)

    pm, created = ProjectMember.objects.get_or_create(
        project=project,
        user=user_to_add,
        defaults={'role': MemberRole.MEMBER, 'status': MemberStatus.PENDING}
    )

    notify(
        recipient=user_to_add,
        sender=request.user,
        title=f'Lời mời tham gia đồ án [{project.code}]',
        message=f'{request.user.display_name} đã mời bạn tham gia đồ án "{project.name}". Vui lòng xác nhận.',
        link=f'/projects/{project.id}/',
        notification_type=NotificationType.PROJECT_INVITE,
        project=project
    )
    log_action(
        user=request.user,
        action=ActionType.MEMBER_CHANGE,
        entity_type='ProjectMember',
        entity_id=pm.id,
        description=f'Mời thành viên {user_to_add.display_name} vào đồ án {project.code}',
        project=project,
        request=request
    )
    messages.success(request, f'Đã gửi lời mời tham gia cho {user_to_add.display_name}!')
    return redirect('project_detail', project_id=project.id)

@login_required
@require_POST
def project_member_accept_view(request, project_id):
    pm = get_object_or_404(ProjectMember, project_id=project_id, user=request.user)
    pm.status = MemberStatus.ACCEPTED
    pm.save()
    messages.success(request, 'Bạn đã chấp nhận tham gia đồ án!')
    return redirect('project_detail', project_id=project_id)

@login_required
@require_POST
def project_mentor_accept_view(request, project_id):
    project = get_object_or_404(Project, id=project_id, mentor=request.user)
    if not can(request.user, 'project.mentor.respond', project):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    project.mentor_status = MentorStatus.ACCEPTED
    project.status = ProjectStatus.IN_PROGRESS
    project.save()

    notify(
        recipient=project.created_by,
        sender=request.user,
        title=f'Mentor đã chấp nhận hướng dẫn đồ án [{project.code}]',
        message=f'Giảng viên {request.user.display_name} đã đồng ý hướng dẫn đồ án "{project.name}".',
        link=f'/projects/{project.id}/',
        notification_type=NotificationType.PROJECT_ACCEPTED,
        project=project
    )
    messages.success(request, 'Bạn đã chấp nhận hướng dẫn đồ án này!')
    return redirect('project_detail', project_id=project_id)

@login_required
@require_POST
def project_mentor_reject_view(request, project_id):
    project = get_object_or_404(Project, id=project_id, mentor=request.user)
    if not can(request.user, 'project.mentor.respond', project):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    reason = request.POST.get('reason', '').strip()
    project.mentor_status = MentorStatus.REJECTED
    project.save()

    notify(
        recipient=project.created_by,
        sender=request.user,
        title=f'Mentor từ chối hướng dẫn đồ án [{project.code}]',
        message=f'Giảng viên {request.user.display_name} từ chối hướng dẫn đồ án "{project.name}". Lý do: {reason or "Không có"}',
        link=f'/projects/{project.id}/',
        notification_type=NotificationType.PROJECT_REJECTED,
        project=project
    )

    messages.warning(request, 'Bạn đã từ chối hướng dẫn đồ án này.')
    return redirect('project_list')

@login_required
def team_page_view(request):
    user = request.user
    my_projects = visible_projects(user)

    visible_user_ids = set()
    for p in my_projects:
        visible_user_ids.add(p.created_by_id)
        if p.mentor_id:
            visible_user_ids.add(p.mentor_id)
        for m in p.memberships.all():
            visible_user_ids.add(m.user_id)

    role_filter = request.GET.get('role')
    dept_filter = request.GET.get('department')
    query = request.GET.get('q', '').strip()

    users_qs = User.objects.filter(id__in=visible_user_ids, status=UserStatus.ACTIVE) if not user.is_admin_user else User.objects.filter(status=UserStatus.ACTIVE)

    if role_filter:
        users_qs = users_qs.filter(role=role_filter)
    if dept_filter:
        users_qs = users_qs.filter(department=dept_filter)
    if query:
        users_qs = users_qs.filter(Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(student_id__icontains=query))

    member_data = []
    for u in users_qs.order_by('role', 'last_name', 'first_name'):
        assigned_tasks = Task.objects.filter(project__in=my_projects, assignee=u)
        open_count = assigned_tasks.exclude(status=TaskStatus.DONE).count()
        done_count = assigned_tasks.filter(status=TaskStatus.DONE).count()
        total_count = assigned_tasks.count()
        workload = int((open_count / 5.0) * 100) if open_count > 0 else 0
        if workload > 100:
            workload = 100

        member_data.append({
            'user': u,
            'open_count': open_count,
            'done_count': done_count,
            'total_count': total_count,
            'workload': workload,
            'is_high_workload': open_count >= 4
        })

    return render(request, 'projects/team.html', {
        'members_data': member_data,
        'role_filter': role_filter,
        'dept_filter': dept_filter,
        'query': query,
        'my_projects': my_projects,
    })

@login_required
@require_POST
def project_chat_send_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not can(request.user, 'chat.send', project):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    content = request.POST.get('content', '').strip()[:1000]
    if content:
        msg = Message.objects.create(
            project=project,
            sender=request.user,
            content=content
        )
        local_time = timezone.localtime(msg.created_at).strftime('%H:%M %d/%m')
        return JsonResponse({
            'status': 'success',
            'message': {
                'id': msg.id,
                'sender_name': msg.sender.display_name,
                'sender_avatar': msg.sender.get_avatar_url(),
                'content': msg.content,
                'created_at': local_time
            }
        })
    return JsonResponse({'status': 'error', 'message': 'Nội dung tin nhắn không hợp lệ'}, status=400)

@login_required
def project_chat_messages_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not can(request.user, 'chat.read', project):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    messages_qs = project.messages.select_related('sender').order_by('created_at')[:100]
    msg_list = [{
        'id': m.id,
        'sender_id': m.sender.id,
        'sender_name': m.sender.display_name,
        'sender_avatar': m.sender.get_avatar_url(),
        'content': m.content,
        'created_at': timezone.localtime(m.created_at).strftime('%H:%M %d/%m'),
        'is_me': (m.sender == request.user)
    } for m in messages_qs]

    return JsonResponse({'status': 'success', 'messages': msg_list})

@login_required
@require_POST
def project_submit_review_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not can(request.user, 'project.submit_review', project):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền nộp đồ án chờ nghiệm thu.'}, status=403)
        return render(request, 'errors/403.html', status=403)

    if project.mentor_status != MentorStatus.ACCEPTED or not project.mentor:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Đồ án phải được Mentor chấp nhận hướng dẫn mới có thể nộp review.'}, status=400)
        messages.error(request, 'Đồ án phải được Mentor chấp nhận hướng dẫn mới có thể nộp review.')
        return redirect('project_detail', project_id=project.id)

    if project.tasks.count() == 0:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Đồ án phải có ít nhất 1 nhiệm vụ mới có thể nộp review.'}, status=400)
        messages.error(request, 'Đồ án phải có ít nhất 1 nhiệm vụ mới có thể nộp review.')
        return redirect('project_detail', project_id=project.id)

    project.status = ProjectStatus.REVIEW
    project.save()

    log_action(
        user=request.user,
        action=ActionType.SUBMIT_REVIEW,
        entity_type='Project',
        entity_id=project.id,
        description=f'Nhóm trưởng {request.user.display_name} nộp đồ án {project.code} chờ Mentor review',
        project=project,
        request=request
    )

    if project.mentor:
        notify(
            recipient=project.mentor,
            sender=request.user,
            title=f'Đồ án [{project.code}] nộp chờ review',
            message=f'Nhóm trưởng {request.user.display_name} đã nộp đồ án "{project.name}" chờ duyệt nghiệm thu.',
            link=f'/projects/{project.id}/',
            notification_type=NotificationType.SUBMIT_REVIEW,
            project=project
        )

    messages.success(request, 'Đã nộp đồ án chờ Mentor review nghiệm thu!')
    return redirect('project_detail', project_id=project.id)

@login_required
@require_POST
def project_archive_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not can(request.user, 'project.archive', project):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền lưu trữ đồ án này.'}, status=403)
        return render(request, 'errors/403.html', status=403)

    project.status = ProjectStatus.ARCHIVED
    project.save()

    log_action(
        user=request.user,
        action=ActionType.UPDATE_PROJECT,
        entity_type='Project',
        entity_id=project.id,
        description=f'Quản trị viên chuyển đồ án {project.code} sang lưu trữ (ARCHIVED)',
        project=project,
        request=request
    )

    messages.success(request, f'Đã chuyển đồ án [{project.code}] sang lưu trữ.')
    return redirect('project_detail', project_id=project.id)


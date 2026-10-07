from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.db.models import Q
from django.utils import timezone

from projects.models import Project, ProjectMember, ProjectStatus, ProjectCategory, MemberRole, MemberStatus, MentorStatus, Message
from projects.forms import ProjectForm
from projects.permissions import user_can_access_project, user_can_edit_project
from accounts.models import User, UserRole
from audit_log.models import ActionType, ActivityLog
from audit_log.utils import log_action
from notifications.models import Notification, NotificationType
from tasks.models import Task, TaskStatus

@login_required
def project_list_view(request):
    user = request.user
    if user.is_admin_user:
        projects = Project.objects.all()
    elif user.is_mentor:
        projects = Project.objects.filter(
            Q(mentor=user, mentor_status=MentorStatus.ACCEPTED) | Q(created_by=user)
        ).distinct()
    else:
        projects = Project.objects.filter(
            Q(memberships__user=user, memberships__status=MemberStatus.ACCEPTED) | Q(created_by=user)
        ).distinct()

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

    mentors = User.objects.filter(role=UserRole.MENTOR)

    return render(request, 'projects/project_list.html', {
        'projects': projects.order_by('-created_at'),
        'status_filter': status_filter,
        'category_filter': category_filter,
        'query': query,
        'pending_invites': pending_invites,
        'mentors': mentors,
    })

@login_required
def project_detail_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not user_can_access_project(request.user, project):
        return render(request, 'errors/403.html', status=403)

    members = project.memberships.all().select_related('user')
    tasks = project.tasks.all().select_related('assignee')
    milestones = project.milestones.all()
    documents = project.documents.all()
    feedbacks = project.feedbacks.all()
    activity_logs = ActivityLog.objects.filter(entity_id=str(project.id))[:15]

    can_edit = user_can_edit_project(request.user, project)
    is_leader = (project.created_by == request.user)

    available_students = User.objects.filter(role=UserRole.STUDENT).exclude(project_memberships__project=project)
    mentors = User.objects.filter(role=UserRole.MENTOR)

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
def project_create_view(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        category = request.POST.get('category', ProjectCategory.WEB)
        technology = request.POST.get('technology', '')
        mentor_id = request.POST.get('mentor_id') or request.POST.get('mentor')
        start_date = request.POST.get('start_date') or timezone.now().date()
        end_date = request.POST.get('end_date') or (timezone.now() + timezone.timedelta(days=90)).date()

        project = Project.objects.create(
            code=code,
            name=name,
            description=description,
            category=category,
            technology=technology,
            start_date=start_date,
            end_date=end_date,
            created_by=request.user,
            mentor_id=mentor_id if mentor_id else None,
            mentor_status=MentorStatus.PENDING if mentor_id else MentorStatus.NONE,
            status=ProjectStatus.PLANNING
        )

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
            request=request
        )

        messages.success(request, f'Tạo đồ án "{project.name}" thành công!')
        return redirect(request.META.get('HTTP_REFERER') or 'project_list')

    return redirect('project_list')

@login_required
def project_edit_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not user_can_edit_project(request.user, project):
        return render(request, 'errors/403.html', status=403)

    if request.method == 'POST':
        project.name = request.POST.get('name', project.name)
        project.code = request.POST.get('code', project.code)
        project.description = request.POST.get('description', project.description)
        project.category = request.POST.get('category', project.category)
        project.technology = request.POST.get('technology', project.technology)
        project.status = request.POST.get('status', project.status)
        
        mentor_id = request.POST.get('mentor_id')
        if mentor_id:
            if str(project.mentor_id) != str(mentor_id):
                project.mentor_id = mentor_id
                project.mentor_status = MentorStatus.PENDING

        end_date = request.POST.get('end_date')
        if end_date:
            project.end_date = end_date

        project.save()

        log_action(
            user=request.user,
            action=ActionType.UPDATE_PROJECT,
            entity_type='Project',
            entity_id=project.id,
            description=f'Cập nhật thông tin đồ án: {project.name}',
            request=request
        )

        messages.success(request, f'Cập nhật đồ án "{project.name}" thành công!')
        return redirect(request.META.get('HTTP_REFERER') or 'project_detail', project_id=project.id)

    return redirect('project_detail', project_id=project.id)

@login_required
def project_delete_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not (request.user == project.created_by or request.user.is_admin_user):
        return render(request, 'errors/403.html', status=403)

    if request.method == 'POST':
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

    return redirect('project_list')

@login_required
def project_add_member_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not user_can_edit_project(request.user, project):
        return render(request, 'errors/403.html', status=403)

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        user_to_add = get_object_or_404(User, id=user_id)
        
        pm, created = ProjectMember.objects.get_or_create(
            project=project,
            user=user_to_add,
            defaults={'role': MemberRole.MEMBER, 'status': MemberStatus.PENDING}
        )
        
        Notification.objects.create(
            recipient=user_to_add,
            sender=request.user,
            title=f'Lời mời tham gia đồ án [{project.code}]',
            message=f'{request.user.display_name} đã mời bạn tham gia đồ án "{project.name}". Vui lòng xác nhận.',
            link=f'/projects/{project.id}/member-accept/',
            notification_type=NotificationType.PROJECT_INVITE
        )
        log_action(
            user=request.user,
            action=ActionType.UPDATE_PROJECT,
            entity_type='ProjectMember',
            entity_id=pm.id,
            description=f'Mời thành viên {user_to_add.display_name} vào đồ án {project.code}',
            request=request
        )
        messages.success(request, f'Đã gửi lời mời tham gia cho {user_to_add.display_name}!')

    return redirect('project_detail', project_id=project.id)

@login_required
def project_member_accept_view(request, project_id):
    pm = get_object_or_404(ProjectMember, project_id=project_id, user=request.user)
    pm.status = MemberStatus.ACCEPTED
    pm.save()
    messages.success(request, 'Bạn đã chấp nhận tham gia đồ án!')
    return redirect('project_detail', project_id=project_id)

@login_required
def project_mentor_accept_view(request, project_id):
    project = get_object_or_404(Project, id=project_id, mentor=request.user)
    project.mentor_status = MentorStatus.ACCEPTED
    project.status = ProjectStatus.IN_PROGRESS
    project.save()

    Notification.objects.create(
        recipient=project.created_by,
        sender=request.user,
        title=f'Mentor đã chấp nhận hướng dẫn đồ án [{project.code}]',
        message=f'Giảng viên {request.user.display_name} đã đồng ý hướng dẫn đồ án "{project.name}".',
        link=f'/projects/{project.id}/',
        notification_type=NotificationType.PROJECT_ACCEPTED
    )
    messages.success(request, 'Bạn đã chấp nhận hướng dẫn đồ án này!')
    return redirect('project_detail', project_id=project_id)

@login_required
def project_mentor_reject_view(request, project_id):
    project = get_object_or_404(Project, id=project_id, mentor=request.user)
    project.mentor_status = MentorStatus.REJECTED
    project.save()
    messages.warning(request, 'Bạn đã từ chối hướng dẫn đồ án này.')
    return redirect('project_list')

@login_required
def team_page_view(request):
    user = request.user
    role_filter = request.GET.get('role')
    dept_filter = request.GET.get('department')
    query = request.GET.get('q', '').strip()

    users_qs = User.objects.filter(status='ACTIVE')
    if role_filter:
        users_qs = users_qs.filter(role=role_filter)
    if dept_filter:
        users_qs = users_qs.filter(department=dept_filter)
    if query:
        users_qs = users_qs.filter(Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(email__icontains=query) | Q(student_id__icontains=query))

    member_data = []
    for u in users_qs.order_by('role', 'last_name', 'first_name'):
        assigned_tasks = Task.objects.filter(assignee=u)
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

    if user.is_admin_user:
        my_projects = Project.objects.all()
    elif user.is_mentor:
        my_projects = Project.objects.filter(
            Q(mentor=user, mentor_status=MentorStatus.ACCEPTED) | Q(created_by=user)
        ).distinct()
    else:
        my_projects = Project.objects.filter(
            Q(memberships__user=user, memberships__status=MemberStatus.ACCEPTED) | Q(created_by=user)
        ).distinct()

    return render(request, 'projects/team.html', {
        'members_data': member_data,
        'role_filter': role_filter,
        'dept_filter': dept_filter,
        'query': query,
        'my_projects': my_projects,
    })

@login_required
def project_chat_send_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not user_can_access_project(request.user, project):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
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
    return JsonResponse({'status': 'error', 'message': 'Yêu cầu không hợp lệ'}, status=400)

@login_required
def project_chat_messages_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not user_can_access_project(request.user, project):
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

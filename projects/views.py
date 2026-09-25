from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from projects.models import Project, ProjectMember, MemberRole, MentorStatus, MemberStatus
from projects.forms import ProjectForm
from projects.permissions import user_can_access_project, user_can_edit_project
from accounts.models import User, UserRole
from audit_log.models import ActionType
from audit_log.utils import log_action
from notifications.models import Notification, NotificationType

@login_required
def project_list_view(request):
    user = request.user
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    category_filter = request.GET.get('category', '')
    
    pending_invites = []
    if user.is_admin_user:
        projects = Project.objects.all()
    elif user.is_mentor:
        projects = Project.objects.filter(Q(mentor=user, mentor_status='ACCEPTED') | Q(created_by=user))
        pending_invites = Project.objects.filter(mentor=user, mentor_status='PENDING')
    else:
        projects = Project.objects.filter(memberships__user=user, memberships__status='ACCEPTED')
        
    if query:
        projects = projects.filter(Q(name__icontains=query) | Q(code__icontains=query) | Q(technology__icontains=query))
    if status_filter:
        projects = projects.filter(status=status_filter)
    if category_filter:
        projects = projects.filter(category=category_filter)
        
    return render(request, 'projects/project_list.html', {
        'projects': projects.distinct(),
        'pending_invites': pending_invites,
        'query': query,
        'status_filter': status_filter,
        'category_filter': category_filter,
    })

@login_required
def project_detail_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not user_can_access_project(request.user, project):
        return render(request, 'errors/403.html', status=403)

    milestones = project.milestones.all().order_by('due_date')
    members = project.memberships.all()
    documents = project.documents.all()[:5]
    feedbacks = project.feedbacks.all()[:5]
    recent_tasks = project.tasks.all()[:6]
    
    context = {
        'project': project,
        'milestones': milestones,
        'members': members,
        'documents': documents,
        'feedbacks': feedbacks,
        'recent_tasks': recent_tasks,
        'available_students': User.objects.filter(role=UserRole.STUDENT).exclude(project_memberships__project=project),
    }
    return render(request, 'projects/project_detail.html', context)

@login_required
def project_create_view(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            if project.mentor:
                project.mentor_status = MentorStatus.PENDING
            else:
                project.mentor_status = MentorStatus.NONE
            project.save()
            
            # Auto-add creator as LEADER
            ProjectMember.objects.create(project=project, user=request.user, role=MemberRole.LEADER, status=MemberStatus.ACCEPTED)
            
            if project.mentor:
                Notification.objects.create(
                    recipient=project.mentor,
                    sender=request.user,
                    title=f'Bạn được mời làm Mentor cho đồ án [{project.code}]',
                    message=f'Sinh viên {request.user.display_name} đã chọn bạn hướng dẫn đồ án "{project.name}". Vui lòng xác nhận.',
                    link=f'/projects/{project.id}/mentor-accept/',
                    notification_type=NotificationType.PROJECT_INVITE
                )

            log_action(
                user=request.user,
                action=ActionType.CREATE_PROJECT,
                entity_type='Project',
                entity_id=project.id,
                description=f'Khởi tạo đồ án mới: {project.name} ({project.code})',
                request=request
            )

            messages.success(request, 'Khởi tạo đồ án mới thành công!')
            return redirect('project_detail', project_id=project.id)
        else:
            messages.error(request, 'Vui lòng kiểm tra lại thông tin đồ án.')
    else:
        form = ProjectForm()
        
    return render(request, 'projects/project_form.html', {'form': form, 'title': 'Tạo Đồ án Mới'})

@login_required
def project_edit_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not user_can_edit_project(request.user, project):
        return render(request, 'errors/403.html', status=403)

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            p = form.save(commit=False)
            if p.mentor and p.mentor_status == MentorStatus.NONE:
                p.mentor_status = MentorStatus.PENDING
            p.save()
            messages.success(request, 'Cập nhật thông tin đồ án thành công!')
            return redirect('project_detail', project_id=project.id)
    else:
        form = ProjectForm(instance=project)
        
    return render(request, 'projects/project_form.html', {'form': form, 'project': project, 'title': 'Chỉnh sửa Đồ án'})

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
            description=f'Gửi lời mời tham gia đồ án {project.code} cho sinh viên {user_to_add.display_name}',
            request=request
        )
        messages.success(request, f'Đã gửi lời mời tham gia đồ án cho {user_to_add.display_name}.')
    return redirect('project_detail', project_id=project.id)

@login_required
def project_member_accept_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    membership = ProjectMember.objects.filter(project=project, user=request.user, status=MemberStatus.PENDING).first()
    if not membership and not request.user.is_admin_user:
        return render(request, 'errors/403.html', status=403)
    
    if membership:
        membership.status = MemberStatus.ACCEPTED
        membership.save()
        
        Notification.objects.create(
            recipient=project.created_by,
            sender=request.user,
            title=f'Thành viên đã chấp nhận tham gia đồ án [{project.code}]',
            message=f'Sinh viên {request.user.display_name} đã đồng ý tham gia đồ án "{project.name}".',
            link=f'/projects/{project.id}/',
            notification_type=NotificationType.PROJECT_INVITE
        )
        messages.success(request, f'Bạn đã chính thức gia nhập đồ án {project.name}.')
    return redirect('project_detail', project_id=project.id)

@login_required
def project_mentor_accept_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if project.mentor != request.user and not request.user.is_admin_user:
        return render(request, 'errors/403.html', status=403)
    
    project.mentor_status = MentorStatus.ACCEPTED
    project.save()
    
    Notification.objects.create(
        recipient=project.created_by,
        sender=request.user,
        title=f'Mentor đã chấp nhận hướng dẫn đồ án [{project.code}]',
        message=f'Giảng viên {request.user.display_name} đã đồng ý nhận hướng dẫn đồ án "{project.name}".',
        link=f'/projects/{project.id}/',
        notification_type=NotificationType.PROJECT_INVITE
    )
    messages.success(request, f'Bạn đã chấp nhận làm Mentor cho đồ án {project.name}.')
    return redirect('project_detail', project_id=project.id)

@login_required
def project_mentor_reject_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if project.mentor != request.user and not request.user.is_admin_user:
        return render(request, 'errors/403.html', status=403)
    
    project.mentor_status = MentorStatus.REJECTED
    project.mentor = None
    project.save()
    
    Notification.objects.create(
        recipient=project.created_by,
        sender=request.user,
        title=f'Mentor đã từ chối hướng dẫn đồ án [{project.code}]',
        message=f'Giảng viên {request.user.display_name} chưa thể nhận hướng dẫn đồ án "{project.name}".',
        link=f'/projects/{project.id}/',
        notification_type=NotificationType.PROJECT_INVITE
    )
    messages.warning(request, f'Bạn đã từ chối nhận hướng dẫn đồ án {project.name}.')
    return redirect('dashboard')

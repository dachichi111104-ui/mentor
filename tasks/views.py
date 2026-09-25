from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from tasks.models import Task, TaskComment, TaskStatus, TaskPriority
from projects.models import Project, ProjectMember
from projects.permissions import user_can_access_project
from audit_log.models import ActionType
from audit_log.utils import log_action
from notifications.models import Notification, NotificationType

@login_required
def project_tasks_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not user_can_access_project(request.user, project):
        return render(request, 'errors/403.html', status=403)

    tasks = project.tasks.all().select_related('assignee', 'milestone')
    
    todo_tasks = tasks.filter(status=TaskStatus.TODO)
    in_progress_tasks = tasks.filter(status=TaskStatus.IN_PROGRESS)
    review_tasks = tasks.filter(status=TaskStatus.REVIEW)
    done_tasks = tasks.filter(status=TaskStatus.DONE)
    
    members = project.memberships.all()
    milestones = project.milestones.all()
    
    context = {
        'project': project,
        'todo_tasks': todo_tasks,
        'in_progress_tasks': in_progress_tasks,
        'review_tasks': review_tasks,
        'done_tasks': done_tasks,
        'members': members,
        'milestones': milestones,
    }
    return render(request, 'tasks/kanban.html', context)

@login_required
def my_tasks_view(request):
    tasks = Task.objects.filter(assignee=request.user).order_by('due_date')
    return render(request, 'tasks/my_tasks.html', {'tasks': tasks})

@login_required
def task_create_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not user_can_access_project(request.user, project):
        return render(request, 'errors/403.html', status=403)

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        priority = request.POST.get('priority', TaskPriority.MEDIUM)
        assignee_id = request.POST.get('assignee_id')
        milestone_id = request.POST.get('milestone_id')
        due_date = request.POST.get('due_date') or None
        
        task = Task.objects.create(
            project=project,
            title=title,
            description=description,
            priority=priority,
            assignee_id=assignee_id if assignee_id else None,
            milestone_id=milestone_id if milestone_id else None,
            due_date=due_date,
            created_by=request.user,
            status=TaskStatus.TODO
        )

        log_action(
            user=request.user,
            action=ActionType.CREATE_TASK,
            entity_type='Task',
            entity_id=task.id,
            description=f'Tạo công việc mới: "{task.title}" trong đồ án {project.code}',
            request=request
        )

        if task.assignee and task.assignee != request.user:
            Notification.objects.create(
                recipient=task.assignee,
                sender=request.user,
                title=f'Bạn được giao Task mới [{task.title}]',
                message=f'{request.user.display_name} đã phân công task "{task.title}" cho bạn trong đồ án "{project.name}".',
                link=f'/projects/{project.id}/tasks/',
                notification_type=NotificationType.TASK_ASSIGNED
            )

        messages.success(request, f'Tạo task "{task.title}" thành công!')
    return redirect('project_tasks', project_id=project.id)

@login_required
def task_update_status_view(request, task_id):
    if request.method == 'POST':
        task = get_object_or_404(Task, id=task_id)
        if not user_can_access_project(request.user, task.project):
            return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

        new_status = request.POST.get('status')
        if new_status in TaskStatus.values:
            is_admin = request.user.is_admin_user
            is_mentor = (task.project.mentor == request.user)
            is_leader = (task.project.created_by == request.user) or ProjectMember.objects.filter(project=task.project, user=request.user, role='LEADER').exists()
            is_assignee = (task.assignee == request.user)

            if new_status == TaskStatus.DONE:
                if not (is_mentor or is_leader or is_admin):
                    return JsonResponse({'status': 'error', 'message': 'Chỉ Mentor, Trưởng nhóm hoặc Admin mới có quyền chuyển công việc sang DONE.'}, status=403)
            else:
                if not (is_assignee or is_leader or is_mentor or is_admin):
                    return JsonResponse({'status': 'error', 'message': 'Chỉ người thực hiện hoặc quản lý đồ án mới có quyền cập nhật công việc.'}, status=403)

            task.status = new_status
            task.save()
            
            log_action(
                user=request.user,
                action=ActionType.UPDATE_TASK,
                entity_type='Task',
                entity_id=task.id,
                description=f'Cập nhật trạng thái task "{task.title}" sang {task.get_status_display()}',
                request=request
            )
            
            return JsonResponse({'status': 'success', 'new_status_display': task.get_status_display()})
            
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def task_comment_view(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if not user_can_access_project(request.user, task.project):
        return render(request, 'errors/403.html', status=403)

    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            comment = TaskComment.objects.create(
                task=task,
                user=request.user,
                content=content
            )
            log_action(
                user=request.user,
                action=ActionType.UPDATE_TASK,
                entity_type='TaskComment',
                entity_id=comment.id,
                description=f'Bình luận về công việc "{task.title}": {content[:50]}',
                request=request
            )
            messages.success(request, 'Đã gửi bình luận!')
    return redirect('project_tasks', project_id=task.project.id)

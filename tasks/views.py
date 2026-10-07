from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib import messages
from tasks.models import Task, TaskComment, TaskStatus, TaskPriority, TaskChecklistItem
from tasks.workflow import transition
from tasks.forms import TaskForm
from projects.models import Project, ProjectMember, MemberStatus
from projects.permissions import require_can, can
from milestones.models import Milestone
from audit_log.models import ActionType
from audit_log.utils import log_action
from notifications.models import Notification, NotificationType
from notifications.services import notify


@login_required
@require_can('project.view')
def project_tasks_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    request.breadcrumb_obj = project

    tasks = project.tasks.all().select_related('assignee', 'milestone')

    todo_tasks = tasks.filter(status=TaskStatus.TODO)
    in_progress_tasks = tasks.filter(status=TaskStatus.IN_PROGRESS)
    review_tasks = tasks.filter(status=TaskStatus.REVIEW)
    done_tasks = tasks.filter(status=TaskStatus.DONE)

    members = project.memberships.filter(status=MemberStatus.ACCEPTED).select_related('user')
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
@require_POST
@require_can('task.create')
def task_create_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('accept', '')

    form = TaskForm(request.POST, project=project)
    if not form.is_valid():
        if is_ajax:
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        first_err = list(form.errors.values())[0][0] if form.errors else 'Vui lòng nhập đúng thông tin công việc!'
        messages.error(request, first_err)
        return redirect('project_tasks', project_id=project.id)

    task = form.save(commit=False)
    task.project = project
    task.created_by = request.user
    task.status = TaskStatus.TODO
    task.save()

    log_action(
        user=request.user,
        action=ActionType.CREATE_TASK,
        entity_type='Task',
        entity_id=task.id,
        description=f'Tạo công việc mới: "{task.title}" trong đồ án {project.code}',
        project=project,
        request=request
    )

    if task.assignee and task.assignee != request.user:
        notify(
            recipient=task.assignee,
            sender=request.user,
            title=f'Bạn được giao Task mới [{task.title}]',
            message=f'{request.user.display_name} đã phân công task "{task.title}" cho bạn.',
            link=f'/projects/{project.id}/tasks/',
            notification_type=NotificationType.TASK_ASSIGNED,
            project=project
        )

    messages.success(request, f'Tạo task "{task.title}" thành công!')
    if is_ajax:
        return JsonResponse({'status': 'success', 'task_id': task.id})
    return redirect('project_tasks', project_id=project.id)

@login_required
@require_POST
def task_update_status_view(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if not can(request.user, 'task.move', task):
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền chuyển trạng thái task này.'}, status=403)

    new_status = request.POST.get('status')
    reason = request.POST.get('reason', '')
    force = request.POST.get('force', 'false').lower() == 'true'

    success, msg = transition(task, new_status, request.user, reason=reason, force=force)
    if success:
        return JsonResponse({'status': 'success', 'message': msg, 'new_status_display': task.get_status_display()})
    else:
        status_code = 403 if ("vai trò" in msg or "quyền" in msg) else 400
        return JsonResponse({'status': 'error', 'message': msg}, status=status_code)

@login_required
@require_POST
def task_comment_view(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if not can(request.user, 'comment.create', task):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    content = request.POST.get('content', '').strip()
    if content:
        comment = TaskComment.objects.create(
            task=task,
            user=request.user,
            content=content
        )
        log_action(
            user=request.user,
            action=ActionType.ADD_COMMENT,
            entity_type='TaskComment',
            entity_id=comment.id,
            description=f'Bình luận về công việc "{task.title}": {content[:50]}',
            project=task.project,
            request=request
        )
        messages.success(request, 'Đã gửi bình luận!')
    return redirect('project_tasks', project_id=task.project.id)

@login_required
@require_POST
def task_reorder_view(request):
    task_id = request.POST.get('task_id')
    new_status = request.POST.get('status')
    order_index_raw = request.POST.get('order_index', 0)

    try:
        order_index = int(order_index_raw)
    except (ValueError, TypeError):
        order_index = 0

    task = get_object_or_404(Task, id=task_id)
    if not can(request.user, 'task.move', task):
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền di chuyển task này.'}, status=403)

    reason = request.POST.get('reason', '')
    success, msg = transition(task, new_status, request.user, reason=reason)
    if not success:
        status_code = 403 if ("vai trò" in msg or "quyền" in msg) else 400
        return JsonResponse({'status': 'error', 'message': msg}, status=status_code)

    task.order_index = order_index
    task.save()

    return JsonResponse({'status': 'success', 'task_id': task.id, 'new_status': new_status})

@login_required
@require_POST
def task_edit_view(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if not can(request.user, 'task.edit', task):
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền chỉnh sửa task này.'}, status=403)

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('accept', '')
    form = TaskForm(request.POST, instance=task, project=task.project)
    if not form.is_valid():
        if is_ajax:
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        first_err = list(form.errors.values())[0][0] if form.errors else 'Dữ liệu không hợp lệ!'
        messages.error(request, first_err)
        return redirect('project_tasks', project_id=task.project.id)

    task = form.save()

    log_action(
        user=request.user,
        action=ActionType.UPDATE_TASK,
        entity_type='Task',
        entity_id=task.id,
        description=f'Chỉnh sửa thông tin công việc "{task.title}"',
        project=task.project,
        request=request
    )
    messages.success(request, f'Cập nhật công việc "{task.title}" thành công!')
    if is_ajax:
        return JsonResponse({'status': 'success', 'task_id': task.id})
    return redirect('project_tasks', project_id=task.project.id)

@login_required
@require_POST
def task_delete_view(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    project_id = task.project.id
    if not can(request.user, 'task.delete', task):
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền xóa task này.'}, status=403)

    title = task.title
    task.delete()
    log_action(
        user=request.user,
        action=ActionType.DELETE_TASK,
        entity_type='Task',
        entity_id=task_id,
        description=f'Xóa công việc "{title}" khỏi dự án',
        project=task.project,
        request=request
    )
    messages.success(request, f'Đã xóa công việc "{title}".')
    return redirect('project_tasks', project_id=project_id)

@login_required
@require_POST
def task_duplicate_view(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if not can(request.user, 'task.duplicate', task):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    new_task = Task.objects.create(
        project=task.project,
        title=f"{task.title} (Bản sao)",
        description=task.description,
        priority=task.priority,
        status=TaskStatus.TODO,
        assignee=task.assignee,
        milestone=task.milestone,
        due_date=task.due_date,
        labels=task.labels,
        created_by=request.user
    )
    messages.success(request, f'Đã nhân bản công việc thành "{new_task.title}".')
    return redirect('project_tasks', project_id=task.project.id)

@login_required
def task_detail_json_view(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if not can(request.user, 'project.view', task.project):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    checklist_items = task.checklist_items.all()
    comments = task.comments.all().select_related('user')

    return JsonResponse({
        'status': 'success',
        'task': {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'status_display': task.get_status_display(),
            'priority': task.priority,
            'priority_display': task.get_priority_display(),
            'assignee_id': task.assignee.id if task.assignee else None,
            'assignee_name': task.assignee.display_name if task.assignee else 'Chưa giao',
            'due_date': task.due_date.strftime('%Y-%m-%d') if task.due_date else None,
            'labels': task.labels or '',
            'days_in_status': task.days_in_status,
            'progress': task.checklist_progress,
            'checklist': [{'id': item.id, 'title': item.title, 'is_completed': item.is_completed} for item in checklist_items],
            'comments': [{'id': c.id, 'user_name': c.user.display_name, 'user_avatar': c.user.get_avatar_url(), 'content': c.content, 'created_at': c.created_at.strftime('%H:%M %d/%m/%Y')} for c in comments],
        }
    })

@login_required
@require_POST
def task_checklist_add_view(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if not can(request.user, 'checklist.manage', task):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    title = request.POST.get('title', '').strip()
    if title:
        item = TaskChecklistItem.objects.create(task=task, title=title)
        return JsonResponse({
            'status': 'success',
            'item': {'id': item.id, 'title': item.title, 'is_completed': item.is_completed},
            'progress': task.checklist_progress
        })
    return JsonResponse({'status': 'error', 'message': 'Tiêu đề không được để trống'}, status=400)

@login_required
@require_POST
def task_checklist_toggle_view(request, item_id):
    item = get_object_or_404(TaskChecklistItem, id=item_id)
    if not can(request.user, 'checklist.toggle', item.task):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    item.is_completed = not item.is_completed
    item.save()

    return JsonResponse({
        'status': 'success',
        'is_completed': item.is_completed,
        'progress': item.task.checklist_progress
    })

@login_required
@require_POST
def task_checklist_delete_view(request, item_id):
    item = get_object_or_404(TaskChecklistItem, id=item_id)
    if not can(request.user, 'checklist.manage', item.task):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    task = item.task
    item.delete()
    return JsonResponse({
        'status': 'success',
        'progress': task.checklist_progress
    })

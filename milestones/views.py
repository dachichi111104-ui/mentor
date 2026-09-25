from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from milestones.models import Milestone, MilestoneStatus
from projects.models import Project
from projects.permissions import user_can_access_project
from audit_log.models import ActionType
from audit_log.utils import log_action

@login_required
def project_milestones_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not user_can_access_project(request.user, project):
        return render(request, 'errors/403.html', status=403)

    milestones = project.milestones.all().order_by('due_date')
    return render(request, 'milestones/milestone_list.html', {'project': project, 'milestones': milestones})

@login_required
def milestone_create_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not user_can_access_project(request.user, project):
        return render(request, 'errors/403.html', status=403)

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        start_date = request.POST.get('start_date')
        due_date = request.POST.get('due_date')
        
        ms = Milestone.objects.create(
            project=project,
            name=name,
            description=description,
            start_date=start_date,
            due_date=due_date,
            status=MilestoneStatus.PENDING
        )
        log_action(
            user=request.user,
            action=ActionType.CREATE_MILESTONE,
            entity_type='Milestone',
            entity_id=ms.id,
            description=f'Tạo mốc Milestone mới: "{name}" trong đồ án {project.code}',
            request=request
        )
        messages.success(request, f'Tạo Milestone "{name}" thành công!')
    return redirect('project_milestones', project_id=project.id)

@login_required
def milestone_delete_view(request, milestone_id):
    milestone = get_object_or_404(Milestone, id=milestone_id)
    if not user_can_access_project(request.user, milestone.project):
        return render(request, 'errors/403.html', status=403)

    project_id = milestone.project.id
    ms_name = milestone.name
    ms_id = milestone.id
    milestone.delete()
    log_action(
        user=request.user,
        action=ActionType.DELETE_MILESTONE,
        entity_type='Milestone',
        entity_id=ms_id,
        description=f'Xóa mốc Milestone: "{ms_name}" khỏi đồ án',
        request=request
    )
    messages.success(request, 'Đã xóa Milestone.')
    return redirect('project_milestones', project_id=project_id)

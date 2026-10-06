from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from milestones.models import Milestone, MilestoneStatus, Event, EventType, EventStatus
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


@login_required
def calendar_page_view(request):
    user = request.user
    my_projects = Project.objects.filter(memberships__user=user) if not user.is_admin_user else Project.objects.all()
    upcoming_events = Event.objects.filter(start__gte=timezone.now()).order_by('start')[:5]

    return render(request, 'milestones/calendar.html', {
        'my_projects': my_projects,
        'upcoming_events': upcoming_events,
    })


@login_required
def calendar_events_json_view(request):
    from tasks.models import Task
    user = request.user
    if user.is_admin_user:
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(memberships__user=user)

    events_qs = Event.objects.filter(project__in=projects)
    tasks_qs = Task.objects.filter(project__in=projects, due_date__isnull=False)
    milestones_qs = Milestone.objects.filter(project__in=projects)

    event_data = []
    for ev in events_qs:
        event_data.append({
            'id': f'evt_{ev.id}',
            'title': ev.title,
            'start': ev.start.isoformat(),
            'end': ev.end.isoformat() if ev.end else ev.start.isoformat(),
            'type': ev.event_type,
            'type_display': ev.get_event_type_display(),
            'project_name': ev.project.name,
            'link': ev.link or '',
            'status': ev.status,
            'color': '#3B82F6' if ev.event_type == 'MEETING' else '#8B5CF6'
        })

    for t in tasks_qs:
        event_data.append({
            'id': f'tsk_{t.id}',
            'title': f'Task: {t.title}',
            'start': t.due_date.strftime('%Y-%m-%d'),
            'type': 'DEADLINE',
            'type_display': 'Hạn chót công việc',
            'project_name': t.project.name,
            'color': '#EF4444' if t.priority == 'HIGH' else '#F59E0B'
        })

    for m in milestones_qs:
        event_data.append({
            'id': f'ms_{m.id}',
            'title': f'Milestone: {m.name}',
            'start': m.due_date.strftime('%Y-%m-%d'),
            'type': 'REVIEW',
            'type_display': 'Mốc Đánh Giá',
            'project_name': m.project.name,
            'color': '#10B981'
        })

    return JsonResponse({'status': 'success', 'events': event_data})


@login_required
def event_create_view(request):
    from milestones.models import Event, EventType, EventStatus
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        title = request.POST.get('title')
        event_type = request.POST.get('event_type', EventType.MEETING)
        start_str = request.POST.get('start')
        link = request.POST.get('link', '')

        project = get_object_or_404(Project, id=project_id)
        if not user_can_access_project(request.user, project):
            return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

        ev = Event.objects.create(
            project=project,
            title=title,
            event_type=event_type,
            start=start_str,
            link=link,
            created_by=request.user,
            status=EventStatus.ACCEPTED
        )
        messages.success(request, f'Đã thêm sự kiện "{ev.title}" vào lịch.')
        return redirect('calendar')
    return redirect('calendar')


@login_required
def appointment_book_view(request):
    from milestones.models import Event, EventType, EventStatus
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        title = request.POST.get('title')
        start_str = request.POST.get('start')
        link = request.POST.get('link', '')

        project = get_object_or_404(Project, id=project_id)
        ev = Event.objects.create(
            project=project,
            title=f'Lịch hẹn Mentor: {title}',
            event_type=EventType.MEETING,
            start=start_str,
            link=link,
            created_by=request.user,
            status=EventStatus.PENDING
        )
        if project.mentor:
            ev.participants.add(project.mentor)

        messages.success(request, 'Đã gửi yêu cầu đặt lịch hẹn tới Mentor.')
        return redirect('calendar')
    return redirect('calendar')


@login_required
def calendar_export_ics_view(request):
    from milestones.models import Event
    from django.http import HttpResponse
    user = request.user
    projects = Project.objects.filter(memberships__user=user) if not user.is_admin_user else Project.objects.all()
    events = Event.objects.filter(project__in=projects)

    ics_content = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ProjectHub AI//Calendar 1.0//EN"]

    for ev in events:
        ics_content.append("BEGIN:VEVENT")
        ics_content.append(f"SUMMARY:{ev.title}")
        ics_content.append(f"DESCRIPTION:{ev.project.name} - {ev.get_event_type_display()}")
        dtstart = ev.start.strftime('%Y%m%dT%H%M%SZ')
        ics_content.append(f"DTSTART:{dtstart}")
        if ev.link:
            ics_content.append(f"LOCATION:{ev.link}")
        ics_content.append("END:VEVENT")

    ics_content.append("END:VCALENDAR")

    response = HttpResponse("\r\n".join(ics_content), content_type="text/calendar")
    response['Content-Disposition'] = 'attachment; filename="projecthub_calendar.ics"'
    return response


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_date

from milestones.models import Milestone, MilestoneStatus, Event, EventType, EventStatus
from projects.models import Project
from projects.permissions import visible_projects, require_can, can
from audit_log.models import ActionType
from audit_log.utils import log_action
from notifications.models import Notification, NotificationType
from notifications.services import notify


@login_required
@require_can('project.view')
def project_milestones_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    request.breadcrumb_obj = project

    milestones = project.milestones.all().order_by('due_date')
    return render(request, 'milestones/milestone_list.html', {'project': project, 'milestones': milestones})

@login_required
@require_POST
@require_can('milestone.create')
def milestone_create_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    name = request.POST.get('name', '').strip()
    if not name:
        messages.error(request, 'Vui lòng nhập tên Cột mốc!')
        return redirect('project_milestones', project_id=project.id)

    description = request.POST.get('description', '').strip()
    start_date = request.POST.get('start_date') or None
    due_date = request.POST.get('due_date') or None

    if not start_date or not due_date:
        messages.error(request, 'Vui lòng nhập đầy đủ Ngày bắt đầu và Hạn hoàn thành!')
        return redirect('project_milestones', project_id=project.id)

    if start_date > due_date:
        messages.error(request, 'Ngày bắt đầu phải nhỏ hơn hoặc bằng Hạn hoàn thành!')
        return redirect('project_milestones', project_id=project.id)

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
        project=project,
        request=request
    )
    messages.success(request, f'Tạo Milestone "{name}" thành công!')
    return redirect('project_milestones', project_id=project.id)

@login_required
@require_POST
def milestone_edit_view(request, milestone_id):
    ms = get_object_or_404(Milestone, id=milestone_id)
    if not can(request.user, 'milestone.edit', ms):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    name = request.POST.get('name', '').strip()
    if name:
        ms.name = name
    ms.description = request.POST.get('description', ms.description)

    start_date = request.POST.get('start_date')
    due_date = request.POST.get('due_date')
    if start_date and due_date and start_date <= due_date:
        ms.start_date = start_date
        ms.due_date = due_date

    ms.save()
    log_action(
        user=request.user,
        action=ActionType.UPDATE_MILESTONE,
        entity_type='Milestone',
        entity_id=ms.id,
        description=f'Cập nhật Milestone "{ms.name}"',
        project=ms.project,
        request=request
    )
    messages.success(request, f'Đã cập nhật Milestone "{ms.name}".')
    return redirect('project_milestones', project_id=ms.project.id)

@login_required
@require_POST
def milestone_complete_view(request, milestone_id):
    ms = get_object_or_404(Milestone, id=milestone_id)
    if not can(request.user, 'milestone.complete', ms):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    ms.status = MilestoneStatus.COMPLETED
    ms.save()
    messages.success(request, f'Đã hoàn thành Milestone "{ms.name}"!')
    return redirect('project_milestones', project_id=ms.project.id)

@login_required
@require_POST
def milestone_delete_view(request, milestone_id):
    milestone = get_object_or_404(Milestone, id=milestone_id)
    if not can(request.user, 'milestone.delete', milestone):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

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
        project_id=project_id,
        request=request
    )
    messages.success(request, 'Đã xóa Milestone.')
    return redirect('project_milestones', project_id=project_id)

@login_required
def calendar_page_view(request):
    user = request.user
    my_projects = visible_projects(user)
    upcoming_events = Event.objects.filter(project__in=my_projects, start__gte=timezone.now()).order_by('start')[:5]

    month_param = request.GET.get('month')
    today = timezone.localdate()

    if month_param:
        try:
            parts = month_param.split('-')
            year, month_num = int(parts[0]), int(parts[1])
            if not (1 <= month_num <= 12):
                year, month_num = today.year, today.month
        except Exception:
            year, month_num = today.year, today.month
    else:
        year, month_num = today.year, today.month

    current_month_str = f"{year}-{month_num:02d}"
    current_month_title = f"Tháng {month_num}, {year}"

    if month_num == 1:
        prev_month_str = f"{year - 1}-12"
    else:
        prev_month_str = f"{year}-{month_num - 1:02d}"

    if month_num == 12:
        next_month_str = f"{year + 1}-01"
    else:
        next_month_str = f"{year}-{month_num + 1:02d}"

    return render(request, 'milestones/calendar.html', {
        'my_projects': my_projects,
        'upcoming_events': upcoming_events,
        'current_month_str': current_month_str,
        'current_month_title': current_month_title,
        'prev_month_str': prev_month_str,
        'next_month_str': next_month_str,
        'today_str': today.strftime('%Y-%m-%d'),
        'year': year,
        'month_num': month_num,
    })


@login_required
def calendar_events_json_view(request):
    from tasks.models import Task
    user = request.user
    projects = visible_projects(user)

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
@require_POST
def event_create_view(request):
    project_id = request.POST.get('project_id')
    title = request.POST.get('title', '').strip()
    event_type = request.POST.get('event_type', EventType.MEETING)
    start_str = request.POST.get('start')
    end_str = request.POST.get('end')
    link = request.POST.get('link', '')
    description = request.POST.get('description', '')

    if not project_id or not title or not start_str:
        messages.error(request, 'Vui lòng nhập đầy đủ tiêu đề, đồ án và thời gian bắt đầu.')
        return redirect('calendar_page')

    project = get_object_or_404(Project, id=project_id)
    if not can(request.user, 'event.create', project):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    parsed_start = parse_datetime(start_str) or parse_date(start_str)
    if not parsed_start:
        try:
            parsed_start = timezone.datetime.fromisoformat(start_str)
        except Exception:
            messages.error(request, 'Định dạng thời gian bắt đầu không hợp lệ.')
            return redirect('calendar_page')

    parsed_end = None
    if end_str:
        parsed_end = parse_datetime(end_str) or parse_date(end_str)

    ev = Event.objects.create(
        project=project,
        title=title,
        event_type=event_type,
        start=parsed_start,
        end=parsed_end,
        link=link,
        created_by=request.user,
        status=EventStatus.ACCEPTED
    )

    log_action(user=request.user, action=ActionType.CREATE_EVENT, entity_type='Event', entity_id=ev.id, description=f"Tạo sự kiện '{title}'", project=project)
    messages.success(request, f'Đã thêm sự kiện "{ev.title}" vào lịch.')
    return redirect('calendar_page')

@login_required
@require_POST
def appointment_book_view(request):
    project_id = request.POST.get('project_id')
    title = request.POST.get('title', '').strip()
    start_str = request.POST.get('start')
    link = request.POST.get('link', '')

    if not project_id or not title or not start_str:
        messages.error(request, 'Vui lòng điền thông tin đồ án, tiêu đề và thời gian hẹn.')
        return redirect('calendar_page')

    project = get_object_or_404(Project, id=project_id)
    if not can(request.user, 'appointment.request', project):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    parsed_start = parse_datetime(start_str) or parse_date(start_str)
    if not parsed_start:
        messages.error(request, 'Định dạng thời gian hẹn không hợp lệ.')
        return redirect('calendar_page')

    ev = Event.objects.create(
        project=project,
        title=f'Lịch hẹn Mentor: {title}',
        event_type=EventType.MEETING,
        start=parsed_start,
        link=link,
        created_by=request.user,
    )

    if project.mentor:

        ev.participants.add(project.mentor)
        notify(
            recipient=project.mentor,
            sender=request.user,
            title=f'Lịch hẹn mới từ Sinh viên [{project.code}]',
            message=f'{request.user.display_name} muốn đặt lịch hẹn: "{title}" vào lúc {start_str}.',
            link='/calendar/',
            notification_type=NotificationType.SYSTEM,
            project=project
        )


    messages.success(request, 'Đã gửi yêu cầu đặt lịch hẹn tới Mentor.')
    return redirect('calendar_page')

@login_required
def calendar_export_ics_view(request):
    user = request.user
    projects = visible_projects(user)
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

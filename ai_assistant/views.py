import json
import hashlib
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from projects.models import Project
from projects.permissions import visible_projects, require_can, can
from tasks.models import Task, TaskStatus, TaskPriority
from ai_assistant.models import AIRequest, AIPromptType, WeeklySummary, AIProposal, AIProposalStatus
from ai_assistant.facts_builder import build_facts
from ai_assistant.engine.service import run_task
from ai_assistant.engine.rules import calculate_metrics
from audit_log.models import ActionType
from audit_log.utils import log_action
from notifications.models import Notification, NotificationType

@login_required
@require_can('ai.view')
def ai_assistant_page_view(request):
    user = request.user
    projects = visible_projects(user)

    project_id = request.GET.get('project_id')
    selected_project = None
    if project_id:
        selected_project = projects.filter(id=project_id).first()

    if not selected_project:
        pref = getattr(user, 'preference', None)
        if pref and pref.last_ai_project and projects.filter(id=pref.last_ai_project.id).exists():
            selected_project = pref.last_ai_project
        else:
            selected_project = projects.first()

    if selected_project and hasattr(user, 'preference'):
        user.preference.last_ai_project = selected_project
        user.preference.save()

    if selected_project:
        ai_history = AIRequest.objects.filter(project=selected_project)[:20]
        weekly_summaries = WeeklySummary.objects.filter(project=selected_project)[:10]
        proposals = AIProposal.objects.filter(project=selected_project, status=AIProposalStatus.PENDING)
        facts = build_facts(selected_project)
        project_metrics = calculate_metrics(facts)
        project_risks = project_metrics.get('risks', [])
    else:
        ai_history = AIRequest.objects.none()
        weekly_summaries = WeeklySummary.objects.none()
        proposals = AIProposal.objects.none()
        project_metrics = {}
        project_risks = []

    projects_overview = []
    if user.is_mentor or user.is_admin_user:
        for p in projects[:15]:
            p_facts = build_facts(p)
            p_metrics = calculate_metrics(p_facts)
            projects_overview.append({
                'project': p,
                'metrics': p_metrics
            })

    return render(request, 'ai_assistant/ai_assistant.html', {
        'projects': projects,
        'selected_project': selected_project,
        'ai_history': ai_history,
        'weekly_summaries': weekly_summaries,
        'proposals': proposals,
        'project_risks': project_risks,
        'project_metrics': project_metrics,
        'projects_overview': projects_overview,
    })

def _execute_ai_task(user, project, prompt_type: str, user_message: str = ""):
    facts = build_facts(project)
    context_hash = hashlib.sha256(json.dumps(facts, sort_keys=True).encode('utf-8')).hexdigest()

    result = run_task(prompt_type, facts, user_message=user_message)

    ai_req = AIRequest.objects.create(
        user=user,
        project=project,
        prompt_type=prompt_type,
        input_data=user_message or json.dumps(facts, ensure_ascii=False),
        output_result=json.dumps(result['data'], ensure_ascii=False),
        provider=result['provider'],
        model=result['model'],
        status=result['status'],
        source=result['source'],
        error=result.get('error', ''),
        latency_ms=result['latency_ms'],
        tokens_in=result['tokens_in'],
        tokens_out=result['tokens_out'],
        context_hash=context_hash,
        cached=result.get('cached', False)
    )

    log_action(
        user=user,
        action=ActionType.AI_GENERATE,
        entity_type='AIRequest',
        entity_id=ai_req.id,
        description=f"Thực hiện AI task [{prompt_type}] cho đồ án {project.code} ({result['source']})",
        project=project
    )

    return result, ai_req

@login_required
@require_POST
def ai_task_breakdown_ajax(request):
    project_id = request.POST.get('project_id')
    project = get_object_or_404(Project, id=project_id)
    if not can(request.user, 'ai.generate', project):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    result, _ = _execute_ai_task(request.user, project, 'breakdown')
    return JsonResponse({
        'status': 'success',
        'source': result['source'],
        'provider': result['provider'],
        'model': result['model'],
        'tasks': result['data'].get('tasks', []),
        'suggested_tasks': result['data'].get('tasks', []),
        'warnings': result.get('warnings', []),
        'source_label': f"AI Task Breakdown ({result['source'].upper()})"
    })

@login_required
@require_POST
def ai_accept_tasks_ajax(request):
    try:
        project_id = request.POST.get('project_id')
        tasks_json = request.POST.get('tasks_json')
        if project_id and tasks_json:
            tasks_to_create = json.loads(tasks_json)
        else:
            data = json.loads(request.body.decode('utf-8'))
            project_id = data.get('project_id')
            tasks_to_create = data.get('tasks', [])

        project = get_object_or_404(Project, id=project_id)
        if not can(request.user, 'ai.generate', project):
            return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

        tasks_to_create = tasks_to_create[:10]
        existing_titles = set(project.tasks.values_list('title', flat=True))

        can_apply = can(request.user, 'ai.apply', project)
        if not can_apply:
            # Create AIProposal
            proposal = AIProposal.objects.create(
                project=project,
                proposed_by=request.user,
                kind='task_breakdown',
                payload={'tasks': tasks_to_create},
                status=AIProposalStatus.PENDING
            )

            # Notify Leader and Creator
            recipients = set()
            if project.created_by:
                recipients.add(project.created_by)
            for m in project.memberships.filter(role='LEADER', status='ACCEPTED'):
                recipients.add(m.user)

            for leader in recipients:
                Notification.objects.create(
                    recipient=leader,
                    sender=request.user,
                    title=f'Đề xuất Task AI mới cho Đồ án [{project.code}]',
                    message=f'{request.user.display_name} đã gửi đề xuất {len(tasks_to_create)} công việc từ AI Assistant.',
                    link=f'/ai/assistant/?project_id={project.id}',
                    notification_type=NotificationType.SYSTEM
                )

            return JsonResponse({
                'status': 'proposed',
                'proposal_id': proposal.id,
                'created_count': 0,
                'message': f'Đã gửi đề xuất {len(tasks_to_create)} công việc tới Trưởng nhóm đồ án duyệt!'
            })

        created_count = 0
        skipped = []
        for t_data in tasks_to_create:
            title = str(t_data.get('title', '')).strip()[:255]
            if not title:
                continue
            if title in existing_titles:
                skipped.append({'title': title, 'reason': 'Đã tồn tại trong đồ án'})
                continue

            priority = t_data.get('priority', TaskPriority.MEDIUM)
            if priority not in TaskPriority.values:
                priority = TaskPriority.MEDIUM

            Task.objects.create(
                project=project,
                title=title,
                description=t_data.get('description', '') or '',
                priority=priority,
                created_by=request.user,
                status=TaskStatus.TODO
            )
            existing_titles.add(title)
            created_count += 1

        log_action(
            user=request.user,
            action=ActionType.AI_APPLY,
            entity_type='Project',
            entity_id=project.id,
            description=f"Áp dụng tạo trực tiếp {created_count} task từ AI cho đồ án {project.code}",
            project=project
        )

        return JsonResponse({
            'status': 'success',
            'created_count': created_count,
            'skipped': skipped,
            'message': f'Đã áp dụng tạo thành công {created_count} công việc vào Đồ án!'
        })

    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Đầu vào không hợp lệ hoặc dữ liệu lỗi.'}, status=400)

@login_required
@require_POST
def ai_weekly_summary_ajax(request):
    project_id = request.POST.get('project_id')
    project = get_object_or_404(Project, id=project_id)
    if not can(request.user, 'ai.generate', project):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    result, _ = _execute_ai_task(request.user, project, 'weekly')
    data = result['data']

    now = timezone.now()
    year, week_num, _ = now.isocalendar()

    summary_str = f"**Highlights**: {data.get('highlights')}\n- **Đã xong**: {', '.join(data.get('done', []))}\n- **Đang làm**: {', '.join(data.get('in_progress', []))}\n- **Vướng mắc**: {', '.join(data.get('blockers', []))}"

    WeeklySummary.objects.update_or_create(
        project=project,
        week_number=week_num,
        year=year,
        defaults={
            'summary_text': summary_str,
            'rating': data.get('rating', 'FAIR'),
            'source': result['source'],
            'model': result['model']
        }
    )

    return JsonResponse({
        'status': 'success',
        'source': result['source'],
        'summary': summary_str,
        'summary_data': data,
        'source_label': f"AI Weekly Summary ({result['source'].upper()})"
    })

@login_required
@require_POST
def ai_risk_detection_ajax(request):
    project_id = request.POST.get('project_id')
    project = get_object_or_404(Project, id=project_id)
    if not can(request.user, 'ai.generate', project):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    result, _ = _execute_ai_task(request.user, project, 'risks')
    summary_text = result['data'].get('summary', '')
    return JsonResponse({
        'status': 'success',
        'source': result['source'],
        'risks': result['data'].get('risks', []),
        'summary': summary_text,
        'analysis': summary_text,
        'risk_html': summary_text,
        'source_label': f"AI Risk Detection ({result['source'].upper()})"
    })

@login_required
@require_POST
def ai_mentor_questions_ajax(request):
    project_id = request.POST.get('project_id')
    project = get_object_or_404(Project, id=project_id)
    if not can(request.user, 'ai.questions', project):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    result, _ = _execute_ai_task(request.user, project, 'questions')
    return JsonResponse({
        'status': 'success',
        'source': result['source'],
        'questions': result['data'].get('questions', []),
        'source_label': f"AI Questions for Mentor ({result['source'].upper()})"
    })

@login_required
@require_POST
def ai_chat_ajax(request):
    prompt = request.POST.get('prompt', '').strip()[:1000]
    project_id = request.POST.get('project_id')

    if not prompt or not project_id:
        return JsonResponse({'status': 'error', 'message': 'Thiếu thông tin đồ án hoặc nội dung câu hỏi.'}, status=400)

    project = get_object_or_404(Project, id=project_id)
    if not can(request.user, 'ai.chat', project):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    result, _ = _execute_ai_task(request.user, project, 'chat', user_message=prompt)
    return JsonResponse({
        'status': 'success',
        'source': result['source'],
        'response': result['data'].get('answer', ''),
        'citations': result['data'].get('citations', []),
        'in_scope': result['data'].get('in_scope', True),
        'source_label': f"AI Chat ({result['source'].upper()})"
    })

@login_required
def ai_health_status_view(request):
    if not request.user.is_admin_user:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    from ai_assistant.engine.llm import LLMClient
    llm = LLMClient()
    last_req = AIRequest.objects.first()

    return JsonResponse({
        'status': 'healthy',
        'provider': llm.provider,
        'model': llm.model,
        'configured': llm.is_configured(),
        'last_request_time': last_req.created_at.strftime('%Y-%m-%d %H:%M') if last_req else 'Chưa có',
        'total_requests': AIRequest.objects.count()
    })

@login_required
@require_POST
def ai_health_test_ajax(request):
    if not request.user.is_admin_user:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    p = Project.objects.first()
    if not p:
        return JsonResponse({'status': 'error', 'message': 'Không có đồ án trong hệ thống để test.'}, status=400)

    result, _ = _execute_ai_task(request.user, p, 'risks')
    return JsonResponse({
        'status': 'success',
        'test_result': result
    })

import os
import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone

from projects.models import Project, ProjectMember
from projects.permissions import user_can_access_project, user_is_leader_or_admin
from tasks.models import Task, TaskStatus, TaskPriority
from milestones.models import Milestone
from ai_assistant.models import AIRequest, AIPromptType, WeeklySummary
from ai_assistant.services import LLMService, compute_project_risks
from ai_assistant.metrics import calculate_project_metrics
from notifications.models import Notification, NotificationType

@login_required
def ai_assistant_page_view(request):
    user = request.user
    if user.is_admin_user:
        projects = Project.objects.all()
    elif user.is_mentor:
        projects = Project.objects.filter(mentor=user, mentor_status='ACCEPTED')
    else:
        projects = Project.objects.filter(memberships__user=user, memberships__status='ACCEPTED')
        
    project_id = request.GET.get('project_id')
    selected_project = None
    if project_id:
        selected_project = projects.filter(id=project_id).first()
    if not selected_project and projects.exists():
        selected_project = projects.first()

    # Per-project isolated history - NEVER leak other projects' history!
    if selected_project:
        ai_history = AIRequest.objects.filter(project=selected_project)[:20]
        weekly_summaries = WeeklySummary.objects.filter(project=selected_project)[:10]
        project_metrics = calculate_project_metrics(selected_project)
        project_risks = project_metrics.get('risks', [])
    else:
        ai_history = AIRequest.objects.none()
        weekly_summaries = WeeklySummary.objects.none()
        project_metrics = {}
        project_risks = []

    # Overview table metrics for Mentor/Admin
    projects_overview = []
    if user.is_mentor or user.is_admin_user:
        for p in projects[:15]:
            p_metrics = calculate_project_metrics(p)
            projects_overview.append({
                'project': p,
                'metrics': p_metrics
            })

    return render(request, 'ai_assistant/ai_assistant.html', {
        'projects': projects,
        'selected_project': selected_project,
        'ai_history': ai_history,
        'weekly_summaries': weekly_summaries,
        'project_risks': project_risks,
        'project_metrics': project_metrics,
        'projects_overview': projects_overview,
    })

@login_required
def ai_task_breakdown_ajax(request):
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        project = None
        if project_id:
            project = Project.objects.filter(id=project_id).first()
            if project and not user_can_access_project(request.user, project):
                return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
        
        project_name = project.name if project else request.POST.get('project_name', 'Phát triển hệ thống phần mềm')
        existing_tasks = list(project.tasks.values_list('title', flat=True)) if project else []

        prompt = (
            f"Hãy phân rã các công việc cho đồ án '{project_name}'. "
            f"Các task hiện có: {', '.join(existing_tasks[:5]) if existing_tasks else 'Chưa có'}. "
            "Trả về danh sách 5 task mới gợi ý dưới dạng JSON array các object với keys: title, description, priority (CRITICAL/HIGH/MEDIUM/LOW), estimated_hours, labels."
        )

        output_text = LLMService.call_llm(
            prompt=prompt,
            prompt_type=AIPromptType.TASK_BREAKDOWN,
            user=request.user,
            project=project,
            input_data=f"Project: {project_name}"
        )

        try:
            suggested_tasks = json.loads(output_text)
        except Exception:
            suggested_tasks = []

        return JsonResponse({
            'status': 'success',
            'tasks': suggested_tasks,
            'suggested_tasks': suggested_tasks,
            'source_label': 'AI Gợi ý Phân rã Công việc cho Đồ án'
        })

    return JsonResponse({'status': 'error'}, status=400)

@login_required
def ai_accept_tasks_ajax(request):
    """
    Creates real Task objects in DB when user clicks "Áp dụng" on AI suggestions.
    Guarantees AI only suggests, humans decide.
    Leader/Admin can create directly. Members/Mentors click "Đề xuất" -> sends notification to Leader.
    """
    if request.method == 'POST':
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
            if not user_can_access_project(request.user, project):
                return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

            # Limit max 10 tasks per request
            tasks_to_create = tasks_to_create[:10]
            existing_titles = set(project.tasks.values_list('title', flat=True))

            # Permission check: Leader or Admin applies directly
            is_leader_or_admin = user_is_leader_or_admin(request.user, project)
            if not is_leader_or_admin:
                # Member or Mentor proposed tasks -> Notify Leader
                leader_mem = project.memberships.filter(role='LEADER').first()
                if leader_mem:
                    Notification.objects.create(
                        recipient=leader_mem.user,
                        sender=request.user,
                        title=f'Đề xuất Task AI mới cho Đồ án [{project.code}]',
                        message=f'{request.user.display_name} đã gửi đề xuất {len(tasks_to_create)} công việc từ AI Assistant.',
                        link=f'/projects/{project.id}/tasks/',
                        notification_type=NotificationType.SYSTEM
                    )
                return JsonResponse({
                    'status': 'proposed',
                    'created_count': 0,
                    'message': f'Đã gửi đề xuất {len(tasks_to_create)} công việc tới Nhóm trưởng đồ án xem xét!'
                })

            created_count = 0
            for t_data in tasks_to_create:
                title = str(t_data.get('title', '')).strip()[:255]
                if title and title not in existing_titles:
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

            return JsonResponse({
                'status': 'success',
                'created_count': created_count,
                'message': f'Đã áp dụng tạo thành công {created_count} công việc vào Cơ sở dữ liệu Đồ án!'
            })
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'Lỗi khi áp dụng đề xuất công việc.'}, status=400)

    return JsonResponse({'status': 'error'}, status=400)

@login_required
def ai_weekly_summary_ajax(request):
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        project = get_object_or_404(Project, id=project_id)
        if not user_can_access_project(request.user, project):
            return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

        now = timezone.now()
        prompt = f"Hãy tổng hợp báo cáo tiến độ tuần chi tiết cho đồ án {project.code} - {project.name}."

        summary_text = LLMService.call_llm(
            prompt=prompt,
            prompt_type=AIPromptType.WEEKLY_SUMMARY,
            user=request.user,
            project=project,
            input_data=f"Project: {project.code}"
        )

        year, week_num, _ = now.isocalendar()
        WeeklySummary.objects.update_or_create(
            project=project,
            week_number=week_num,
            year=year,
            defaults={'summary_text': summary_text}
        )

        return JsonResponse({
            'status': 'success',
            'summary': summary_text,
            'summary_html': summary_text,
            'source_label': 'Báo cáo Tổng hợp Tiến độ Tuần'
        })

    return JsonResponse({'status': 'error'}, status=400)

@login_required
def ai_risk_detection_ajax(request):
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        project = get_object_or_404(Project, id=project_id)
        if not user_can_access_project(request.user, project):
            return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

        risks = compute_project_risks(project)
        prompt = f"Dưới đây là danh sách các rủi ro tiến độ được phát hiện cho đồ án {project.code}. Hãy tổng hợp giải pháp."

        analysis_text = LLMService.call_llm(
            prompt=prompt,
            prompt_type=AIPromptType.RISK_DETECTION,
            user=request.user,
            project=project,
            input_data=json.dumps(risks, ensure_ascii=False)
        )

        return JsonResponse({
            'status': 'success',
            'risks': risks,
            'analysis': analysis_text,
            'risk_html': analysis_text,
            'source_label': 'Cảnh báo Rủi ro Tiến độ'
        })

    return JsonResponse({'status': 'error'}, status=400)

@login_required
def ai_mentor_questions_ajax(request):
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        project = get_object_or_404(Project, id=project_id)
        if not user_can_access_project(request.user, project):
            return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

        prompt = f"Hãy gợi ý 5 câu hỏi phản biện chuyên sâu cho Mentor khi họp với Sinh viên đồ án {project.code}."

        questions_text = LLMService.call_llm(
            prompt=prompt,
            prompt_type=AIPromptType.MENTOR_QUESTIONS,
            user=request.user,
            project=project,
            input_data=f"Project: {project.code}"
        )

        return JsonResponse({
            'status': 'success',
            'questions': questions_text,
            'questions_html': questions_text,
            'source_label': 'Gợi ý Câu hỏi Phản biện cho Mentor'
        })

    return JsonResponse({'status': 'error'}, status=400)

@login_required
def ai_chat_ajax(request):
    """
    Interactive Project AI Chat endpoint.
    Strictly checks user permission for the specified project.
    Prevents IDOR and context leakage across projects.
    """
    if request.method == 'POST':
        prompt = request.POST.get('prompt', '').strip()
        project_id = request.POST.get('project_id')
        
        if not prompt or not project_id:
            return JsonResponse({'status': 'error', 'message': 'Thiếu thông tin đồ án hoặc câu hỏi.'}, status=400)

        project = get_object_or_404(Project, id=project_id)
        if not user_can_access_project(request.user, project):
            return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

        response_text = LLMService.call_llm(
            prompt=prompt,
            prompt_type=AIPromptType.CHAT,
            user=request.user,
            project=project,
            input_data=prompt
        )

        return JsonResponse({
            'status': 'success',
            'response': response_text,
            'source_label': f'AI Assistant [{project.code}]'
        })

    return JsonResponse({'status': 'error'}, status=400)

@login_required
def ai_health_status_view(request):
    """
    Admin health status monitor for AI Service provider configuration.
    """
    if not request.user.is_admin_user:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    from ai_assistant.providers import LLMProvider
    provider, model, key_set = LLMProvider.get_configured_provider()
    
    last_req = AIRequest.objects.first()

    return JsonResponse({
        'status': 'healthy',
        'provider': provider,
        'model': model,
        'api_key_configured': bool(key_set),
        'last_request_time': last_req.created_at.strftime('%Y-%m-%d %H:%M') if last_req else 'Chưa có',
        'total_ai_requests': AIRequest.objects.count()
    })

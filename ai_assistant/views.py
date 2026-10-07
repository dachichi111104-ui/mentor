import os
import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone

from projects.models import Project, ProjectMember
from projects.permissions import user_can_access_project
from tasks.models import Task, TaskStatus, TaskPriority
from milestones.models import Milestone
from ai_assistant.models import AIRequest, AIPromptType, WeeklySummary
from ai_assistant.services import LLMService, compute_project_risks
from audit_log.models import ActionType, ActivityLog

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

    ai_history = AIRequest.objects.filter(project=selected_project) if selected_project else AIRequest.objects.all()[:30]
    weekly_summaries = WeeklySummary.objects.filter(project=selected_project) if selected_project else WeeklySummary.objects.all()[:10]

    # Pre-compute risks using deterministic DB rules
    project_risks = compute_project_risks(selected_project) if selected_project else []

    return render(request, 'ai_assistant/ai_assistant.html', {
        'projects': projects,
        'selected_project': selected_project,
        'ai_history': ai_history[:20],
        'weekly_summaries': weekly_summaries,
        'project_risks': project_risks,
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
            "Trả về danh sách 5 task mới gợi ý dưới dạng JSON array các object với keys: title, description, priority (CRITICAL/HIGH/MEDIUM/LOW), estimated_hours."
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
            suggested_tasks = [
                {
                    'title': f'Thiết kế CSDL & Phân quyền RBAC cho {project_name}',
                    'description': 'Lập sơ đồ CSDL, ràng buộc bảng và cấu hình quyền truy cập theo vai trò.',
                    'priority': 'CRITICAL',
                    'estimated_hours': 8
                },
                {
                    'title': 'Phát triển RESTful API Core Backend',
                    'description': 'Xây dựng các API cho phép lấy dữ liệu, cập nhật trạng thái và xử lý lỗi.',
                    'priority': 'HIGH',
                    'estimated_hours': 12
                },
                {
                    'title': 'Tích hợp Giao diện Bảng Kanban kéo thả',
                    'description': 'Thiết kế giao diện bảng Kanban tương tác thời gian thực với Alpine.js.',
                    'priority': 'HIGH',
                    'estimated_hours': 10
                },
                {
                    'title': 'Viết tài liệu Hướng dẫn Sử dụng & Kiểm thử Hệ thống',
                    'description': 'Thực hiện kiểm thử đơn vị, tạo file tài liệu nghiệm thu và hoàn thiện đồ án.',
                    'priority': 'MEDIUM',
                    'estimated_hours': 6
                }
            ]

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

            created_count = 0
            for t_data in tasks_to_create:
                title = t_data.get('title')
                if title:
                    Task.objects.create(
                        project=project,
                        title=title,
                        description=t_data.get('description', ''),
                        priority=t_data.get('priority', TaskPriority.MEDIUM),
                        created_by=request.user,
                        status=TaskStatus.TODO
                    )
                    created_count += 1

            return JsonResponse({'status': 'success', 'created_count': created_count, 'message': f'Đã áp dụng tạo thành công {created_count} công việc vào Đồ án!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error'}, status=400)

@login_required
def ai_weekly_summary_ajax(request):
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        project = get_object_or_404(Project, id=project_id)
        if not user_can_access_project(request.user, project):
            return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

        now = timezone.now()
        week_ago = now - timezone.timedelta(days=7)
        done_count = project.tasks.filter(status=TaskStatus.DONE, updated_at__gte=week_ago).count()
        new_count = project.tasks.filter(created_at__gte=week_ago).count()
        stuck_count = project.tasks.filter(status__in=[TaskStatus.IN_PROGRESS, TaskStatus.REVIEW], updated_at__lt=week_ago).count()

        prompt = (
            f"Hãy viết báo cáo tóm tắt tiến độ tuần cho Đồ án '{project.code} - {project.name}'. "
            f"Dữ liệu trong 7 ngày qua: {done_count} công việc hoàn thành, {new_count} công việc mới được tạo, {stuck_count} công việc đang bị kẹt. "
            f"Tiến độ tổng thể hiện tại đạt {project.progress}%."
        )

        summary_text = LLMService.call_llm(
            prompt=prompt,
            prompt_type=AIPromptType.WEEKLY_SUMMARY,
            user=request.user,
            project=project,
            input_data=f"Progress: {project.progress}%, Done: {done_count}, New: {new_count}, Stuck: {stuck_count}"
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

        # 1. Deterministic Rule-Based Risk Evaluation from DB
        risks = compute_project_risks(project)

        # 2. LLM formatted summary
        prompt = (
            f"Dưới đây là danh sách các rủi ro đã được phát hiện của đồ án {project.code}:\n"
            f"{json.dumps(risks, ensure_ascii=False)}\n"
            "Hãy tổng hợp và đưa ra lời giải thích cùng giải pháp điều phối ngắn gọn cho Nhóm sinh viên."
        )

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

        stuck_tasks = list(project.tasks.filter(status__in=[TaskStatus.IN_PROGRESS, TaskStatus.REVIEW]).values_list('title', flat=True))

        prompt = (
            f"Hãy đưa ra 5 câu hỏi gợi ý cho Giảng viên Mentor khi họp với Sinh viên đồ án {project.code}.\n"
            f"Tiến độ hiện tại: {project.progress}%. Công việc đang làm/chờ review: {', '.join(stuck_tasks[:3]) if stuck_tasks else 'Đang triển khai'}.\n"
            "Mỗi câu hỏi tập trung vào giải quyết vấn đề kỹ thuật và tiến độ nộp bài."
        )

        questions_text = LLMService.call_llm(
            prompt=prompt,
            prompt_type=AIPromptType.MENTOR_QUESTIONS,
            user=request.user,
            project=project,
            input_data=f"Progress: {project.progress}%, Stuck: {stuck_tasks}"
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
    if request.method == 'POST':
        prompt = request.POST.get('prompt')
        project_id = request.POST.get('project_id')
        project = None
        if project_id:
            project = Project.objects.filter(id=project_id).first()

        if not prompt:
            return JsonResponse({'status': 'error', 'message': 'Prompt rỗng'}, status=400)

        response_text = LLMService.call_llm(
            prompt=prompt,
            prompt_type=AIPromptType.TASK_BREAKDOWN,
            user=request.user,
            project=project,
            input_data=prompt
        )

        return JsonResponse({
            'status': 'success',
            'response': response_text,
            'source_label': 'Trợ lý AI ProjectHub VAU'
        })

    return JsonResponse({'status': 'error'}, status=400)

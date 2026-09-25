import os
import json
import urllib.request
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from projects.models import Project
from projects.permissions import user_can_access_project
from tasks.models import Task, TaskStatus, TaskPriority
from milestones.models import Milestone
from ai_assistant.models import AIRequest, AIPromptType
from audit_log.models import ActionType, ActivityLog

def call_llm_api(prompt):
    """
    Attempts to call external LLM API if OPENAI_API_KEY, GEMINI_API_KEY, or ANTHROPIC_API_KEY is configured.
    Returns string response if successful, or None to fall back to rules.
    """
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {openai_key}"
            }
            body = json.dumps({
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            }).encode('utf-8')
            req = urllib.request.Request(url, data=body, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data['choices'][0]['message']['content']
        except Exception as e:
            print(f"OpenAI API error: {e}")

    gemini_key = os.getenv('GEMINI_API_KEY')
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            headers = {"Content-Type": "application/json"}
            body = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}]
            }).encode('utf-8')
            req = urllib.request.Request(url, data=body, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            print(f"Gemini API error: {e}")

    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    if anthropic_key:
        try:
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "Content-Type": "application/json",
                "x-api-key": anthropic_key,
                "anthropic-version": "2023-06-01"
            }
            body = json.dumps({
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            }).encode('utf-8')
            req = urllib.request.Request(url, data=body, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data['content'][0]['text']
        except Exception as e:
            print(f"Anthropic API error: {e}")

    return None

@login_required
def ai_assistant_page_view(request):
    user = request.user
    if user.is_admin_user:
        return render(request, 'errors/403.html', status=403)
        
    project_id = request.GET.get('project_id')
    if user.is_mentor:
        projects = Project.objects.filter(mentor=user, mentor_status='ACCEPTED')
    else:
        projects = Project.objects.filter(memberships__user=user, memberships__status='ACCEPTED')
        
    selected_project = None
    if project_id:
        selected_project = projects.filter(id=project_id).first()
    if not selected_project and projects.exists():
        selected_project = projects.first()
        
    return render(request, 'ai_assistant/ai_assistant.html', {
        'projects': projects,
        'selected_project': selected_project,
    })

@login_required
def ai_task_breakdown_ajax(request):
    if request.user.is_admin_user:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        project_name = request.POST.get('project_name', 'Phát triển hệ thống phần mềm')
        
        project = None
        if project_id:
            project = Project.objects.filter(id=project_id).first()
            if project and not user_can_access_project(request.user, project):
                return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
        if project:
            from django.utils import timezone
            today = timezone.now().date()
            daily_count = AIRequest.objects.filter(project=project, created_at__date=today).count()
            if daily_count >= 20:
                return JsonResponse({'status': 'error', 'message': 'Đã đạt giới hạn 20 lượt gọi AI/ngày cho đồ án này.'}, status=429)

        # Attempt LLM call if API Key set
        llm_prompt = f"Hãy chia nhỏ dự án '{project_name}' thành 6-7 công việc chính cho bảng Kanban theo định dạng JSON list các object có keys: title, description, priority (CRITICAL/HIGH/MEDIUM/LOW), labels."
        llm_response = call_llm_api(llm_prompt)
        
        if llm_response:
            try:
                suggested_tasks = json.loads(llm_response)
            except Exception:
                suggested_tasks = None
        else:
            suggested_tasks = None

        # Context-aware dynamic generator fallback
        if not suggested_tasks:
            tech = project.technology if project else 'Python, Django, Web'
            cat = project.get_category_display() if project else 'Công nghệ Thông tin'
            
            suggested_tasks = [
                {
                    'title': f'Phân tích Yêu cầu & Thiết kế ERD CSDL cho {project_name}',
                    'description': f'Xác định danh sách yêu cầu nghiệp vụ thể loại {cat}, thiết kế sơ đồ ERD và ràng buộc khóa ngoại.',
                    'priority': 'CRITICAL',
                    'labels': 'Requirement, ERD'
                },
                {
                    'title': 'Xây dựng Module Xác thực & Kiểm soát Phân quyền (RBAC)',
                    'description': 'Cấu hình Đăng ký, Đăng nhập, Session và kiểm tra quyền truy cập URL theo từng vai trò.',
                    'priority': 'HIGH',
                    'labels': 'Auth, Security'
                },
                {
                    'title': f'Thiết kế Giao diện UI/UX Chuẩn Academic Portal ({tech})',
                    'description': f'Xây dựng giao diện responsive sử dụng phông chữ Inter và công nghệ {tech}.',
                    'priority': 'HIGH',
                    'labels': 'UI/UX, Frontend'
                },
                {
                    'title': 'Phát triển Backend API & Logic Nghiệp vụ Cốt lõi',
                    'description': 'Xử lý dữ liệu CRUD, viết views, forms và kết nối dữ liệu an toàn.',
                    'priority': 'CRITICAL',
                    'labels': 'Backend, Core'
                },
                {
                    'title': 'Tích hợp Bảng công việc Kanban kéo thả tương tác',
                    'description': 'Lập trình thuật toán kéo thả JavaScript và xử lý AJAX cập nhật trạng thái Task.',
                    'priority': 'HIGH',
                    'labels': 'Kanban, AJAX'
                },
                {
                    'title': 'Quản lý Kho Tài liệu & Lịch sử Phiên bản File',
                    'description': 'Tải lên tài liệu PDF/Word/Zip, phân loại file và quản lý các bản cập nhật v1, v2.',
                    'priority': 'MEDIUM',
                    'labels': 'Document, Version'
                },
                {
                    'title': 'Kiểm thử Chức năng & Viết Báo cáo Tổng kết Đồ án',
                    'description': 'Kiểm thử bảo mật, tối ưu truy vấn CSDL và hoàn thiện thuyết minh báo cáo tốt nghiệp.',
                    'priority': 'HIGH',
                    'labels': 'Testing, SRS'
                }
            ]

        AIRequest.objects.create(
            user=request.user,
            project=project,
            prompt_type=AIPromptType.TASK_BREAKDOWN,
            input_data=project_name,
            output_result=json.dumps(suggested_tasks, ensure_ascii=False)
        )

        return JsonResponse({'status': 'success', 'tasks': suggested_tasks})
        
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def ai_accept_tasks_ajax(request):
    if request.user.is_admin_user:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        tasks_json = request.POST.get('tasks_json')
        
        project = get_object_or_404(Project, id=project_id)
        if not user_can_access_project(request.user, project):
            return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

        tasks_data = json.loads(tasks_json)
        
        created_count = 0
        for item in tasks_data:
            Task.objects.create(
                project=project,
                title=item.get('title'),
                description=item.get('description'),
                priority=item.get('priority', TaskPriority.MEDIUM),
                labels=item.get('labels', ''),
                status=TaskStatus.TODO,
                created_by=request.user
            )
            created_count += 1
            
        ActivityLog.objects.create(
            user=request.user,
            action=ActionType.CREATE_TASK,
            entity_type='Task',
            entity_id=str(project.id),
            description=f'AI Task Breakdown: Tự động tạo {created_count} task mới vào CSDL đồ án {project.code}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return JsonResponse({'status': 'success', 'created_count': created_count})
        
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def ai_weekly_summary_ajax(request):
    if request.user.is_admin_user:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        project = get_object_or_404(Project, id=project_id)
        if not user_can_access_project(request.user, project):
            return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

        from django.utils import timezone
        today = timezone.now().date()
        daily_count = AIRequest.objects.filter(project=project, created_at__date=today).count()
        if daily_count >= 20:
            return JsonResponse({'status': 'error', 'message': 'Đã đạt giới hạn 20 lượt gọi AI/ngày cho đồ án này.'}, status=429)

        done_tasks = project.tasks.filter(status=TaskStatus.DONE)
        in_progress_tasks = project.tasks.filter(status=TaskStatus.IN_PROGRESS)
        overdue_tasks = [t for t in project.tasks.all() if t.is_overdue]
        
        summary_html = f"""
        <div class="space-y-3 text-xs">
            <h4 class="font-bold text-slate-900 text-sm border-b border-slate-200 pb-2">Báo cáo Tiến độ Tuần - Đồ án [{project.code}] {project.name}</h4>
            
            <div class="p-3 bg-emerald-50 rounded-lg border border-emerald-200">
                <span class="font-bold text-emerald-900">Công việc đã Hoàn thành ({done_tasks.count()} tasks):</span>
                <ul class="list-disc list-inside mt-1 text-slate-700 space-y-1">
                    {''.join([f"<li>{t.title}</li>" for t in done_tasks]) if done_tasks.exists() else '<li>Chưa có task hoàn thành trong tuần này.</li>'}
                </ul>
            </div>

            <div class="p-3 bg-amber-50 rounded-lg border border-amber-200">
                <span class="font-bold text-amber-900">Công việc đang Thực hiện ({in_progress_tasks.count()} tasks):</span>
                <ul class="list-disc list-inside mt-1 text-slate-700 space-y-1">
                    {''.join([f"<li>{t.title} (Người làm: {t.assignee.display_name if t.assignee else 'Chưa giao'})</li>" for t in in_progress_tasks]) if in_progress_tasks.exists() else '<li>Không có task đang thực hiện.</li>'}
                </ul>
            </div>

            <div class="p-3 bg-rose-50 rounded-lg border border-rose-200">
                <span class="font-bold text-rose-900">Vấn đề & Rủi ro ({len(overdue_tasks)} tasks quá hạn):</span>
                <ul class="list-disc list-inside mt-1 text-slate-700 space-y-1">
                    {''.join([f"<li>Công việc '{t.title}' đã bị quá hạn chót ({t.due_date})</li>" for t in overdue_tasks]) if overdue_tasks else '<li>Tiến độ đảm bảo, không có công việc quá hạn.</li>'}
                </ul>
            </div>

            <div class="p-3 bg-slate-100 rounded-lg border border-slate-200">
                <span class="font-bold text-slate-900">Đề xuất công việc tuần tới:</span>
                <p class="mt-1 text-slate-700">Hoàn thiện các mốc Milestone đúng hạn chót và gửi Mentor review bản thảo sản phẩm.</p>
            </div>
        </div>
        """

        AIRequest.objects.create(
            user=request.user,
            project=project,
            prompt_type=AIPromptType.WEEKLY_SUMMARY,
            input_data=str(project.id),
            output_result=summary_html
        )
        return JsonResponse({'status': 'success', 'summary_html': summary_html})

    return JsonResponse({'status': 'error'}, status=400)

@login_required
def ai_risk_detection_ajax(request):
    if request.user.is_admin_user:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        project = get_object_or_404(Project, id=project_id)
        if not user_can_access_project(request.user, project):
            return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

        # Rate Limit check: Max 20 AI calls per day per project
        from django.utils import timezone
        today = timezone.now().date()
        daily_count = AIRequest.objects.filter(project=project, created_at__date=today).count() if project else 0
        if daily_count >= 20:
            return JsonResponse({'status': 'error', 'message': 'Đã đạt giới hạn 20 lượt gọi AI/ngày cho đồ án này.'}, status=429)

        done_tasks = project.tasks.filter(status=TaskStatus.DONE)
        in_progress_tasks = project.tasks.filter(status=TaskStatus.IN_PROGRESS)
        overdue_tasks = [t for t in project.tasks.all() if t.is_overdue]

        # Attempt LLM call
        prompt = f"Phân tích rủi ro đồ án '{project.name}' (Mã {project.code}, Công nghệ {project.technology}). Thống kê: {done_tasks.count()} tasks hoàn thành, {in_progress_tasks.count()} đang làm, {len(overdue_tasks)} quá hạn. Hãy viết câu đánh giá rủi ro ngắn gọn (3-4 dòng)."
        llm_res = call_llm_api(prompt)

        if llm_res:
            risk_html = f"<div class='p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800'><p class='font-bold text-navy-900 mb-1'>Phân tích AI:</p>{llm_res}</div>"
        else:
            risks = []
            for ms in project.milestones.all():
                if ms.is_overdue:
                    risks.append(f"<b>Cảnh báo Milestone:</b> Milestone '{ms.name}' đã trễ hạn ({ms.due_date}). Tiến độ hiện tại đạt {ms.progress_percentage}%.")
                    
            overdue_tasks_count = sum(1 for t in project.tasks.all() if t.is_overdue)
            if overdue_tasks_count > 0:
                risks.append(f"<b>Cảnh báo Task:</b> Hiện tại có {overdue_tasks_count} công việc quá hạn chưa hoàn thành.")
                
            if not risks:
                risks.append("<b>Trạng thái An toàn:</b> Tiến độ đồ án đảm bảo đúng thời hạn, không phát hiện rủi ro chậm trễ.")

            risk_html = "<div class='space-y-2 text-xs text-slate-800'>" + "".join([f"<div class='p-3 bg-slate-50 border border-slate-200 rounded-lg'>{r}</div>" for r in risks]) + "</div>"
        
        AIRequest.objects.create(
            user=request.user,
            project=project,
            prompt_type=AIPromptType.RISK_DETECTION,
            input_data=str(project.id),
            output_result=risk_html
        )
        return JsonResponse({'status': 'success', 'risk_html': risk_html})

    return JsonResponse({'status': 'error'}, status=400)

@login_required
def ai_mentor_questions_ajax(request):
    if request.user.is_admin_user:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        project = get_object_or_404(Project, id=project_id)
        if not user_can_access_project(request.user, project):
            return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

        from django.utils import timezone
        today = timezone.now().date()
        daily_count = AIRequest.objects.filter(project=project, created_at__date=today).count()
        if daily_count >= 20:
            return JsonResponse({'status': 'error', 'message': 'Đã đạt giới hạn 20 lượt gọi AI/ngày cho đồ án này.'}, status=429)

        prompt = f"Tạo 4 câu hỏi phản biện ngắn cho Mentor hỏi sinh viên làm đồ án '{project.name}' (Thể loại: {project.get_category_display()}, Công nghệ: {project.technology})."
        llm_res = call_llm_api(prompt)

        if llm_res:
            q_html = f"<div class='space-y-2 text-xs text-slate-800 bg-slate-50 p-4 rounded-lg border border-slate-200'><p class='font-bold text-navy-900 mb-2'>Gợi ý câu hỏi phản biện từ AI cho '{project.name}':</p>{llm_res}</div>"
        else:
            questions = [
                f"1. Cấu trúc tổng thể và sơ đồ thiết kế CSDL của đồ án '{project.name}' ({project.technology}) đã tuân thủ chuẩn hóa chưa?",
                f"2. Nhóm sinh viên đã triển khai các biện pháp bảo mật nào trong đồ án {project.code} để ngăn chặn lỗ hổng SQL Injection và RBAC?",
                f"3. Quy trình kiểm thử sản phẩm {project.name} được thực hiện như thế nào trước khi nộp cho Mentor?",
                f"4. Phần tích hợp API ngoài có phương án dự phòng xử lý khi xảy ra mất kết nối mạng hoặc phản hồi chậm không?"
            ]
            q_html = "<div class='space-y-2 text-xs text-slate-800 bg-slate-50 p-4 rounded-lg border border-slate-200'>" + "".join([f"<p class='font-medium text-slate-800'>- {q}</p>" for q in questions]) + "</div>"
        
        AIRequest.objects.create(
            user=request.user,
            project=project,
            prompt_type=AIPromptType.MENTOR_QUESTIONS,
            input_data=str(project.id),
            output_result=q_html
        )
        return JsonResponse({'status': 'success', 'questions_html': q_html})

    return JsonResponse({'status': 'error'}, status=400)

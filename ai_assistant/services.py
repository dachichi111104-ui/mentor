import os
import json
import urllib.request
from datetime import timedelta
from django.utils import timezone
from tasks.models import Task, TaskStatus, TaskPriority
from milestones.models import Milestone
from audit_log.models import ActivityLog
from ai_assistant.models import AIRequest, AIPromptType

def compute_project_risks(project):
    """
    Rule-based deterministic risk evaluation directly from database records.
    Ensures 100% facts-based risk detection without relying on LLM hallucination.
    """
    today = timezone.now().date()
    now = timezone.now()
    risks = []

    # Rule 1: Task in IN_PROGRESS or REVIEW for > 3 days without updates
    stuck_tasks = project.tasks.filter(status__in=[TaskStatus.IN_PROGRESS, TaskStatus.REVIEW])
    for t in stuck_tasks:
        last_update = t.updated_at
        days_stuck = (now - last_update).days
        if days_stuck >= 3:
            risks.append({
                'type': 'STUCK_TASK',
                'severity': 'CRITICAL' if days_stuck >= 5 else 'WARNING',
                'task_id': t.id,
                'title': t.title,
                'status': t.get_status_display(),
                'days_stuck': days_stuck,
                'reason': f'Task "{t.title}" nằm ở trạng thái [{t.get_status_display()}] đã {days_stuck} ngày chưa có cập nhật mới.'
            })

    # Rule 2: Overdue tasks
    overdue_tasks = project.tasks.filter(due_date__lt=today).exclude(status=TaskStatus.DONE)
    for t in overdue_tasks:
        days_overdue = (today - t.due_date).days
        risks.append({
            'type': 'OVERDUE_TASK',
            'severity': 'CRITICAL',
            'task_id': t.id,
            'title': t.title,
            'days_overdue': days_overdue,
            'reason': f'Task "{t.title}" đã quá hạn {days_overdue} ngày (Hạn chót: {t.due_date.strftime("%d/%m/%Y")}).'
        })

    # Rule 3: Milestone approaching due date (within 7 days) with progress < 50%
    milestones = project.milestones.all()
    for m in milestones:
        if m.due_date and not m.is_completed:
            days_until = (m.due_date - today).days
            progress = m.progress
            if 0 <= days_until <= 7 and progress < 50:
                risks.append({
                    'type': 'MILESTONE_RISK',
                    'severity': 'WARNING',
                    'milestone_id': m.id,
                    'title': m.title,
                    'progress': progress,
                    'days_until': days_until,
                    'reason': f'Mốc tiến độ "{m.title}" chỉ còn {days_until} ngày nhưng tiến độ mới đạt {progress}%.'
                })

    # Rule 4: Project inactive in past 7 days
    recent_activity = ActivityLog.objects.filter(entity_id=str(project.id), created_at__gte=now - timedelta(days=7)).exists()
    if not recent_activity:
        risks.append({
            'type': 'INACTIVE_PROJECT',
            'severity': 'INFO',
            'reason': f'Đồ án {project.code} không phát sinh nhật ký hoạt động nào trong 7 ngày qua.'
        })

    # Rule 5: Workload overload (single member assigned >= 5 active tasks)
    memberships = project.memberships.filter(status='ACCEPTED')
    for mem in memberships:
        u = mem.user
        assigned_cnt = project.tasks.filter(assignee=u).exclude(status=TaskStatus.DONE).count()
        if assigned_cnt >= 5:
            risks.append({
                'type': 'MEMBER_OVERLOAD',
                'severity': 'WARNING',
                'user': u.display_name,
                'count': assigned_cnt,
                'reason': f'Thành viên {u.display_name} đang được phân công {assigned_cnt} công việc chưa hoàn thành.'
            })

    return risks


class LLMService:
    """
    Unified LLM Service Provider supporting Gemini, OpenAI, and Anthropic APIs.
    Fallback to deterministic rule-based generator when offline or without API keys.
    Saves all logs into AIRequest table.
    """

    @staticmethod
    def call_llm(prompt, prompt_type, user, project=None, input_data=""):
        start_time = timezone.now()
        output_result = None
        status = 'SUCCESS'

        # 1. Try Gemini API
        gemini_key = os.getenv('GEMINI_API_KEY')
        if gemini_key and not output_result:
            models = ["gemini-1.5-flash", "gemini-2.0-flash"]
            for m in models:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={gemini_key}"
                    headers = {"Content-Type": "application/json"}
                    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode('utf-8')
                    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        data = json.loads(resp.read().decode('utf-8'))
                        output_result = data['candidates'][0]['content']['parts'][0]['text']
                        break
                except Exception as e:
                    pass

        # 2. Try OpenAI API
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key and not output_result:
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
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    output_result = data['choices'][0]['message']['content']
            except Exception as e:
                pass

        # 3. Try Anthropic API
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_key and not output_result:
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
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    output_result = data['content'][0]['text']
            except Exception as e:
                pass

        # 4. Fallback Rule-Based Response Generator if LLM unavailable
        if not output_result:
            output_result = LLMService._generate_fallback(prompt_type, project)
            status = 'FALLBACK'

        # Log into AIRequest DB
        latency_ms = int((timezone.now() - start_time).total_seconds() * 1000)
        try:
            AIRequest.objects.create(
                user=user,
                project=project,
                prompt_type=prompt_type,
                input_data=input_data[:2000] if input_data else prompt[:2000],
                output_result=output_result
            )
        except Exception:
            pass

        return output_result

    @staticmethod
    def _generate_fallback(prompt_type, project):
        """
        Generates clean, structured Vietnamese fallback content based on DB state.
        Guarantees app never crashes when offline or API keys missing.
        """
        if not project:
            return "Trợ lý AI đang sẵn sàng hỗ trợ bạn quản lý công việc và đồ án tốt nghiệp VAU."

        if prompt_type == AIPromptType.TASK_BREAKDOWN:
            return json.dumps([
                {"title": "Khảo sát và thiết kế sơ đồ CSDL chuẩn RBAC", "priority": "HIGH", "estimated_hours": 8},
                {"title": "Xây dựng RESTful API cho quản lý đồ án", "priority": "CRITICAL", "estimated_hours": 12},
                {"title": "Tích hợp giao diện Kanban kéo thả Alpine.js", "priority": "MEDIUM", "estimated_hours": 10},
                {"title": "Viết tài liệu báo cáo nghiệm thu và kiểm thử system", "priority": "LOW", "estimated_hours": 6}
            ], ensure_ascii=False)

        elif prompt_type == AIPromptType.RISK_DETECTION:
            risks = compute_project_risks(project)
            if not risks:
                return "Đồ án hiện tại đang tiến triển rất tốt. Chưa ghi nhận rủi ro trễ hạn hay kẹt công việc."
            res_lines = ["BÁO CÁO PHÂN TÍCH RỦI RO ĐỒ ÁN (ĐỘC LẬP TỪ CSDL THẬT):\n"]
            for r in risks:
                res_lines.append(f"• [{r['severity']}] {r['reason']}")
            res_lines.append("\nĐề xuất hướng xử lý: Trưởng nhóm họp rà soát task kẹt và điều phối khối lượng việc hợp lý.")
            return "\n".join(res_lines)

        elif prompt_type == AIPromptType.WEEKLY_SUMMARY:
            done_tasks = project.tasks.filter(status=TaskStatus.DONE).count()
            total_tasks = project.tasks.count()
            progress = project.progress
            return (
                f"BÁO CÁO TIẾN ĐỘ TUẦN - ĐỒ ÁN {project.code}:\n"
                f"- Tiến độ tổng thể: {progress}%\n"
                f"- Số công việc đã hoàn thành: {done_tasks}/{total_tasks}\n"
                f"- Đánh giá: Nhóm sinh viên đang bám sát tiến độ đề ra, cần duy trì tiến độ báo cáo định kỳ cho Mentor."
            )

        elif prompt_type == AIPromptType.MENTOR_QUESTIONS:
            return (
                "5 CÂU HỎI GỢI Ý CHO SINH VIÊN KHI THAM GIA BUỔI REVIEW VỚI MENTOR:\n"
                "1. Sơ đồ CSDL và phân quyền RBAC đã tối ưu hóa cho bài toán quy mô lớn chưa?\n"
                "2. Các rủi ro trễ hạn của các task trong tuần được nhóm giải quyết theo hướng nào?\n"
                "3. Kiến trúc RESTful API đã đáp ứng đầy đủ yêu cầu tính năng đồ án chưa?\n"
                "4. Tiến độ hoàn thành mốc (Milestone) hiện tại có đảm bảo đúng hạn nộp không?\n"
                "5. Nhóm cần Mentor hỗ trợ tháo gỡ khó khăn về mặt kĩ thuật nào trong tuần tới?"
            )

        return "Phản hồi dự phòng từ Trợ lý AI ProjectHub."

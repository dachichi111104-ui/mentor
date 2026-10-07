import json
import logging
from django.utils import timezone
from tasks.models import Task, TaskStatus, TaskPriority
from milestones.models import MilestoneStatus
from ai_assistant.models import AIRequest, AIPromptType
from ai_assistant.facts_builder import build_facts as build_project_context
from ai_assistant.engine.rules import calculate_metrics as calculate_project_metrics
from ai_assistant.engine.llm import LLMClient

logger = logging.getLogger(__name__)

def compute_project_risks(project):
    """
    Returns deterministic risk list computed from database state for a project.
    """
    facts = build_project_context(project)
    metrics = calculate_project_metrics(facts)
    return metrics.get('risks', [])

class LLMService:
    @staticmethod
    def call_llm(prompt, prompt_type, user, project=None, input_data=""):
        start_time = timezone.now()
        
        # 1. Build Isolated Facts Context
        p_context = build_project_context(project) if project else {}
        p_metrics = calculate_project_metrics(p_context) if project else {}

        # 2. System Prompt enforcing ground-truth facts
        system_prompt = (
            "Bạn là Trợ lý AI Assistant Học thuật của Học viện Hàng không Việt Nam (VAU).\n"
            "NGUYÊN TẮC BẮT BUỘC:\n"
            "1. Chỉ sử dụng dữ kiện dữ liệu thật được cung cấp. Không tự bịa ra tên người, mã task hay con số không có trong dữ liệu.\n"
            "2. Trả lời ngắn gọn, chuyên nghiệp, tiếng Việt chuẩn mực.\n"
            "3. Khi đề xuất task hoặc phân tích rủi ro, viện dẫn mã task/mốc cụ thể nếu có.\n"
        )
        if p_context:
            system_prompt += f"\nDỮ LIỆU ĐỒ ÁN HIỆN TẠI:\n{json.dumps(p_context, ensure_ascii=False, default=str)}\n"

        client = LLMClient()
        raw_output = ""
        source_label = "Tính từ dữ liệu hệ thống (Rules)"
        if client.is_configured():
            try:
                raw_output, _, _ = client.complete(f"{system_prompt}\nUser request: {prompt}")
                source_label = f"AI ({client.model})"
            except Exception as e:
                logger.warning(f"LLM call failed: {e}")
                raw_output = ""

        parsed_data = None
        status = 'SUCCESS'

        if raw_output:
            try:
                from ai_assistant.engine.parse import extract_json_block
                parsed_data = json.loads(extract_json_block(raw_output))
            except Exception:
                parsed_data = None

        if not raw_output or (prompt_type in [AIPromptType.TASK_BREAKDOWN] and not parsed_data):
            status = 'FALLBACK'
            source_label = 'Tính từ dữ liệu hệ thống (Rules)'
            raw_output = LLMService._generate_dynamic_fallback(prompt_type, project, p_context, p_metrics)
            try:
                from ai_assistant.engine.parse import extract_json_block
                parsed_data = json.loads(extract_json_block(raw_output))
            except Exception:
                parsed_data = None

        # 5. Log into AIRequest table
        latency_ms = int((timezone.now() - start_time).total_seconds() * 1000)
        try:
            AIRequest.objects.create(
                user=user,
                project=project,
                prompt_type=prompt_type,
                input_data=input_data[:2000] if input_data else prompt[:2000],
                output_result=raw_output
            )
        except Exception as e:
            logger.error(f"Error saving AIRequest: {e}")

        return raw_output

    @staticmethod
    def _generate_dynamic_fallback(prompt_type, project, p_context, p_metrics):
        """
        Generates dynamic fallback outputs using factual context when LLM is unavailable.
        Guarantees distinct results for different projects based on their database facts.
        """
        if not project:
            return "Trợ lý AI sẵn sàng hỗ trợ đồ án của bạn."

        p_info = p_context.get('project', {})
        p_name = p_info.get('name', project.name)
        p_code = p_info.get('code', project.code)
        p_cat = p_info.get('category', 'Công nghệ thông tin')
        empty_ms = p_context.get('milestones_without_tasks', [])

        if prompt_type == AIPromptType.TASK_BREAKDOWN:
            tasks = []
            # Generate tasks from empty milestones first
            for ms_name in empty_ms[:2]:
                tasks.append({
                    "title": f"Triển khai mốc: {ms_name}",
                    "description": f"Xây dựng và hoàn thiện các hạng mục thuộc mốc tiến độ {ms_name} cho đồ án {p_name}.",
                    "priority": "HIGH",
                    "estimated_hours": 10,
                    "labels": "Mốc tiến độ"
                })

            # Domain specific task suggestions
            if "Web" in p_cat or "Web" in p_name:
                tasks.extend([
                    {"title": f"Thiết kế CSDL & RESTful API Core cho {p_code}", "description": "Lập sơ đồ ERD, định nghĩa bảng và xây dựng API xử lý dữ liệu.", "priority": "CRITICAL", "estimated_hours": 12, "labels": "Backend"},
                    {"title": f"Tích hợp Giao diện người dùng cho {p_name}", "description": "Phát triển giao diện tương tác mượt mà với Tailwind & Alpine.js.", "priority": "HIGH", "estimated_hours": 10, "labels": "Frontend"},
                    {"title": f"Kiểm thử và Đóng gói Tài liệu Đồ án {p_code}", "description": "Viết tài liệu hướng dẫn và thực hiện test nghiệm thu.", "priority": "MEDIUM", "estimated_hours": 8, "labels": "Báo cáo"}
                ])
            elif "Di động" in p_cat or "Mobile" in p_name:
                tasks.extend([
                    {"title": f"Thiết kế Giao diện App Mobile cho {p_code}", "description": "Xây dựng các screen UI và điều hướng ứng dụng di động.", "priority": "CRITICAL", "estimated_hours": 12, "labels": "UI/UX"},
                    {"title": f"Tích hợp API và Lưu trữ CSDL Local", "description": "Kết nối API backend và đồng bộ dữ liệu ngoại tuyến.", "priority": "HIGH", "estimated_hours": 10, "labels": "Mobile Core"},
                    {"title": f"Kiểm thử trên Thiết bị thật & Đóng gói APK/IPA", "description": "Kiểm thử hiệu năng ứng dụng di động.", "priority": "MEDIUM", "estimated_hours": 8, "labels": "Testing"}
                ])
            else:
                tasks.extend([
                    {"title": f"Phân tích Yêu cầu & Thiết kế Hệ thống {p_code}", "description": "Định nghĩa yêu cầu kỹ thuật và mô hình bài toán.", "priority": "CRITICAL", "estimated_hours": 10, "labels": "Phân tích"},
                    {"title": f"Phát triển Chức năng Cốt lõi cho {p_name}", "description": "Lập trình khối xử lý nghiệp vụ chính của đồ án.", "priority": "HIGH", "estimated_hours": 14, "labels": "Thực hiện"},
                    {"title": f"Viết Báo cáo Thuyết minh & Chuẩn bị Slide Bảo vệ", "description": "Hoàn thiện quyển báo cáo và bài trình chiếu.", "priority": "MEDIUM", "estimated_hours": 8, "labels": "Báo cáo"}
                ])
            return json.dumps(tasks[:5], ensure_ascii=False)

        elif prompt_type == AIPromptType.RISK_DETECTION:
            risks = p_metrics.get('risks', [])
            score = p_metrics.get('risk_score', 0)
            if not risks:
                return (
                    f"BÁO CÁO PHÂN TÍCH RỦI RO ĐỒ ÁN [{p_code}]:\n"
                    f"• Điểm rủi ro: {score}/100 (An toàn)\n"
                    "• Đánh giá: Đồ án đang duy trì tiến độ tốt. Chưa ghi nhận công việc quá hạn hay kẹt nghiêm trọng."
                )
            lines = [f"BÁO CÁO PHÂN TÍCH RỦI RO ĐỒ ÁN [{p_code}] (Điểm rủi ro: {score}/100):\n"]
            for r in risks:
                lines.append(f"• [{r.get('severity', 'WARNING')}] {r.get('detail', r.get('reason', ''))}")
                if r.get('recommendation'):
                    lines.append(f"  ➔ Đề xuất: {r['recommendation']}")
            return "\n".join(lines)

        elif prompt_type == AIPromptType.WEEKLY_SUMMARY:
            t_data = p_context.get('tasks', {})
            done_cnt = t_data.get('done_count', 0)
            total_cnt = t_data.get('total_count', 0)
            overdue_cnt = len(t_data.get('overdue', []))
            stuck_cnt = len(t_data.get('stuck', []))
            prog = p_info.get('progress', 0)

            return (
                f"BÁO CÁO TỔNG HỢP TIẾN ĐỘ TUẦN - ĐỒ ÁN {p_code} ({p_name}):\n"
                f"1. Tiến độ tổng thể: {prog}%\n"
                f"2. Công việc hoàn thành: {done_cnt}/{total_cnt} task\n"
                f"3. Công việc quá hạn: {overdue_cnt} task\n"
                f"4. Công việc bị kẹt (>=3 ngày): {stuck_cnt} task\n"
                f"5. Nhận xét & Đề xuất: Nhóm sinh viên cần ưu tiên xử lý các task quá hạn và duy trì báo cáo tiến độ với Mentor."
            )

        elif prompt_type == AIPromptType.MENTOR_QUESTIONS:
            t_data = p_context.get('tasks', {})
            overdue = t_data.get('overdue', [])
            stuck = t_data.get('stuck', [])
            
            q1 = f"1. Vấn đề kỹ thuật nào đang khiến task '{stuck[0]['title']}' bị chững lại {stuck[0]['days_stuck']} ngày?" if stuck else f"1. Mô hình CSDL và phân quyền RBAC của đồ án {p_code} đã hoàn thiện đến đâu?"
            q2 = f"2. Kế hoạch tháo gỡ cho task quá hạn '{overdue[0]['title']}' như thế nào?" if overdue else f"2. Nhóm đã thực hiện những bước kiểm thử nào cho các tính năng hoàn thành?"
            
            return (
                f"5 CÂU HỎI GỢI Ý PHẢN BIỆN DÀNH CHO MENTOR KHI HỌP NHÓM ĐỒ ÁN [{p_code}]:\n"
                f"{q1}\n"
                f"{q2}\n"
                f"3. Khối lượng công việc còn lại có đảm bảo tiến độ mốc nộp bài sắp tới không?\n"
                f"4. Sự phân công công việc giữa các thành viên trong nhóm đã cân bằng chưa?\n"
                f"5. Nhóm có đề xuất hay khó khăn gì cần Giảng viên hướng dẫn hỗ trợ trong tuần tới không?"
            )

        return f"Phản hồi phân tích cho đồ án {p_code}."

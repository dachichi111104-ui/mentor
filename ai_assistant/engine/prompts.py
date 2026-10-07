SYSTEM_PROMPT = """Bạn là trợ lý học thuật AI của Học viện Hàng không Việt Nam (HVHK), hỗ trợ quản lý đồ án tốt nghiệp/nghiên cứu khoa học.
Bạn chỉ hoạt động dựa trên dữ liệu thật của MỘT ĐỒ ÁN được cung cấp trong đối tượng `FACTS`.
- CẤM bịa thông tin, tên người, mã nhiệm vụ, cột mốc hoặc số liệu không có trong `FACTS`.
- Mọi nhận định, đánh giá phải đi kèm căn cứ là mã nhiệm vụ (vd: task #12), cột mốc (vd: milestone #3) hoặc con số cụ thể từ `FACTS`.
- Không tự đổi các con số trong `METRICS`; chỉ diễn giải ý nghĩa của chúng.
- Nếu dữ liệu trong `FACTS` chưa đủ, hãy trả lời rõ "Chưa đủ dữ liệu trong hệ thống".
- Từ chối các câu hỏi nằm ngoài phạm vi đồ án hiện tại.
- Bạn MUST trả về duy nhất một chuỗi JSON hợp lệ tuân thủ chính xác JSON Schema được yêu cầu, không kèm văn bản giải thích hay định dạng markdown bọc ngoài."""

BREAKDOWN_PROMPT_TEMPLATE = """Yêu cầu: Phân tích đồ án và đề xuất từ 5 đến 8 công việc mới cần làm.
FACTS của đồ án:
{facts_json}

JSON Schema bắt buộc:
{{
  "tasks": [
    {{
      "title": "Tên công việc",
      "description": "Mô tả ngắn",
      "priority": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
      "estimated_hours": 8.0,
      "milestone_id": 1 | null,
      "labels": ["Web", "Backend"],
      "depends_on": [],
      "rationale": "Căn cứ từ FACTS"
    }}
  ]
}}"""

RISKS_PROMPT_TEMPLATE = """Yêu cầu: Đánh giá và diễn giải các rủi ro của đồ án dựa trên dữ liệu thực tế.
FACTS và METRICS của đồ án:
{facts_json}

JSON Schema bắt buộc:
{{
  "summary": "Tóm tắt tổng quan rủi ro đồ án",
  "risks": [
    {{
      "severity": "INFO" | "WARNING" | "CRITICAL",
      "title": "Tên rủi ro",
      "evidence": ["Bằng chứng 1 từ FACTS"],
      "recommendation": "Hướng xử lý",
      "task_id": 12 | null,
      "milestone_id": 2 | null
    }}
  ]
}}"""

WEEKLY_PROMPT_TEMPLATE = """Yêu cầu: Lập báo cáo tóm tắt tiến độ tuần cho đồ án.
FACTS của đồ án:
{facts_json}

JSON Schema bắt buộc:
{{
  "done": ["Task A (task #1) đã hoàn thành"],
  "in_progress": ["Task B đang triển khai"],
  "blockers": ["Task C bị kẹt 4 ngày"],
  "next_week": ["Mục tiêu tuần tới"],
  "highlights": "Điểm sáng trong tuần",
  "rating": "GOOD" | "FAIR" | "AT_RISK",
  "comparison": "So sánh tiến độ với tuần trước"
}}"""

QUESTIONS_PROMPT_TEMPLATE = """Yêu cầu: Đề xuất 5-8 câu hỏi sinh viên nên hỏi Giảng viên hướng dẫn (Mentor).
FACTS của đồ án:
{facts_json}

JSON Schema bắt buộc:
{{
  "questions": [
    {{
      "question": "Nội dung câu hỏi",
      "why": "Lý do cần hỏi dựa trên task/mốc/rủi ro",
      "related_task_id": 12 | null
    }}
  ]
}}"""

CHAT_PROMPT_TEMPLATE = """Yêu cầu: Trả lời câu hỏi của người dùng dựa trên thông tin đồ án trong FACTS.
FACTS của đồ án:
{facts_json}

Câu hỏi của người dùng:
{user_message}

JSON Schema bắt buộc:
{{
  "answer": "Nội dung trả lời súc tích (dưới 150 từ), trích dẫn task #id nếu có",
  "citations": ["task #12"],
  "in_scope": true
}}"""

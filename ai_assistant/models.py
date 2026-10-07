from django.db import models
from django.conf import settings
from projects.models import Project

class AIPromptType(models.TextChoices):
    TASK_BREAKDOWN = 'TASK_BREAKDOWN', 'Phân rã Task (AI Task Breakdown)'
    WEEKLY_SUMMARY = 'WEEKLY_SUMMARY', 'Báo cáo tuần (AI Weekly Summary)'
    RISK_DETECTION = 'RISK_DETECTION', 'Cảnh báo rủi ro (AI Risk Detection)'
    MENTOR_QUESTIONS = 'MENTOR_QUESTIONS', 'Gợi ý câu hỏi Mentor (AI Questions)'
    CHAT = 'CHAT', 'Trò chuyện AI (AI Chat)'

class AIRequestStatus(models.TextChoices):
    SUCCESS = 'SUCCESS', 'Thành công (LLM)'
    FALLBACK = 'FALLBACK', 'Dự phòng (Rules)'
    ERROR = 'ERROR', 'Thất bại'

class AIRequest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_requests', verbose_name="Người yêu cầu")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name='ai_requests', verbose_name="Đồ án liên quan")
    prompt_type = models.CharField(max_length=30, choices=AIPromptType.choices, verbose_name="Loại tác vụ AI")
    input_data = models.TextField(verbose_name="Dữ liệu đầu vào")
    output_result = models.TextField(verbose_name="Kết quả AI tạo ra")
    
    provider = models.CharField(max_length=50, default='none', verbose_name="Nhà cung cấp")
    model = models.CharField(max_length=100, default='none', verbose_name="Mô hình LLM")
    status = models.CharField(max_length=20, choices=AIRequestStatus.choices, default=AIRequestStatus.SUCCESS, verbose_name="Trạng thái")
    source = models.CharField(max_length=20, default='rules', verbose_name="Nguồn tạo kết quả (llm/rules)")
    error = models.TextField(blank=True, null=True, verbose_name="Thông tin lỗi")
    latency_ms = models.IntegerField(default=0, verbose_name="Độ trễ (ms)")
    tokens_in = models.IntegerField(default=0, verbose_name="Tokens đầu vào")
    tokens_out = models.IntegerField(default=0, verbose_name="Tokens đầu ra")
    context_hash = models.CharField(max_length=64, blank=True, null=True, db_index=True, verbose_name="Hash ngữ cảnh")
    cached = models.BooleanField(default=False, verbose_name="Lấy từ Cache")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Yêu cầu AI"
        verbose_name_plural = "Lịch sử Yêu cầu AI"

    def __str__(self):
        return f"AI [{self.get_prompt_type_display()}] by {self.user.display_name} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class WeeklySummary(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='weekly_summaries', verbose_name="Đồ án")
    week_number = models.IntegerField(verbose_name="Tuần thứ")
    year = models.IntegerField(verbose_name="Năm")
    iso_year = models.IntegerField(verbose_name="Năm ISO", null=True, blank=True)
    iso_week = models.IntegerField(verbose_name="Tuần ISO", null=True, blank=True)
    summary_text = models.TextField(verbose_name="Nội dung tóm tắt tiến độ")
    rating = models.CharField(max_length=20, default='FAIR', verbose_name="Đánh giá chung (GOOD/FAIR/AT_RISK)")
    source = models.CharField(max_length=20, default='rules', verbose_name="Nguồn (llm/rules)")
    model = models.CharField(max_length=100, blank=True, null=True, verbose_name="Model LLM")
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_weekly_summaries', verbose_name="Người tạo")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-year', '-week_number', '-created_at']
        unique_together = ('project', 'week_number', 'year')
        verbose_name = "Tóm tắt tiến độ tuần"
        verbose_name_plural = "Danh sách Tóm tắt tiến độ tuần"

    def save(self, *args, **kwargs):
        if self.year and not self.iso_year:
            self.iso_year = self.year
        if self.week_number and not self.iso_week:
            self.iso_week = self.week_number
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Tóm tắt Tuần {self.week_number}/{self.year} - {self.project.code}"


class AIProposalStatus(models.TextChoices):
    PENDING = 'PENDING', 'Chờ duyệt'
    APPLIED = 'APPLIED', 'Đã áp dụng'
    REJECTED = 'REJECTED', 'Từ chối'
    CANCELLED = 'CANCELLED', 'Đã hủy'

class AIProposal(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='ai_proposals', verbose_name="Đồ án")
    proposed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_proposals', verbose_name="Người đề xuất")
    kind = models.CharField(max_length=50, default='task_breakdown', verbose_name="Loại đề xuất")
    payload = models.JSONField(default=dict, verbose_name="Dữ liệu JSON đề xuất")
    status = models.CharField(max_length=20, choices=AIProposalStatus.choices, default=AIProposalStatus.PENDING, verbose_name="Trạng thái")
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_ai_proposals', verbose_name="Người xử lý")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời điểm xử lý")
    note = models.TextField(blank=True, null=True, verbose_name="Ghi chú xử lý")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Đề xuất AI"
        verbose_name_plural = "Danh sách Đề xuất AI"



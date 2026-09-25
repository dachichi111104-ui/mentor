from django.db import models
from django.conf import settings
from projects.models import Project

class AIPromptType(models.TextChoices):
    TASK_BREAKDOWN = 'TASK_BREAKDOWN', 'Phân rã Task (AI Task Breakdown)'
    WEEKLY_SUMMARY = 'WEEKLY_SUMMARY', 'Báo cáo tuần (AI Weekly Summary)'
    RISK_DETECTION = 'RISK_DETECTION', 'Cảnh báo rủi ro (AI Risk Detection)'
    MENTOR_QUESTIONS = 'MENTOR_QUESTIONS', 'Gợi ý câu hỏi Mentor (AI Questions)'

class AIRequest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_requests', verbose_name="Người yêu cầu")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name='ai_requests', verbose_name="Đồ án liên quan")
    prompt_type = models.CharField(max_length=30, choices=AIPromptType.choices, verbose_name="Loại tác vụ AI")
    input_data = models.TextField(verbose_name="Dữ liệu đầu vào")
    output_result = models.TextField(verbose_name="Kết quả AI tạo ra")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Yêu cầu AI"
        verbose_name_plural = "Lịch sử Yêu cầu AI"

    def __str__(self):
        return f"AI [{self.get_prompt_type_display()}] by {self.user.display_name} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"

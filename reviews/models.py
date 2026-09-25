from django.db import models
from django.conf import settings
from projects.models import Project
from tasks.models import Task
from milestones.models import Milestone

class ReviewStatus(models.TextChoices):
    PENDING = 'PENDING', 'Đang chờ Review'
    APPROVED = 'APPROVED', 'Đã duyệt (Approved)'
    NEED_REVISION = 'NEED_REVISION', 'Cần chỉnh sửa (Need Revision)'

class Feedback(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='feedbacks', verbose_name="Đồ án")
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, related_name='feedbacks', verbose_name="Công việc liên quan")
    milestone = models.ForeignKey(Milestone, on_delete=models.SET_NULL, null=True, blank=True, related_name='feedbacks', verbose_name="Milestone liên quan")
    mentor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='given_feedbacks', verbose_name="Mentor đánh giá")
    
    content = models.TextField(verbose_name="Nội dung nhận xét & Nhận xét chi tiết")
    rating = models.IntegerField(default=5, choices=[(i, f"{i} Sao") for i in range(1, 6)], verbose_name="Đánh giá (1-5 Sao)")
    status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.APPROVED, verbose_name="Kết quả đánh giá")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Nhận xét & Review"
        verbose_name_plural = "Danh sách Review & Feedback"

    def __str__(self):
        return f"Review by {self.mentor.display_name} for {self.project.name} [{self.get_status_display()}]"

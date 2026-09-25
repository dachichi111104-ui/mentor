from django.db import models
from django.conf import settings

class NotificationType(models.TextChoices):
    TASK_ASSIGNED = 'TASK_ASSIGNED', 'Được phân công Task'
    TASK_OVERDUE = 'TASK_OVERDUE', 'Task quá hạn'
    MENTOR_FEEDBACK = 'MENTOR_FEEDBACK', 'Phản hồi từ Mentor'
    PROJECT_INVITE = 'PROJECT_INVITE', 'Lời mời vào Đồ án'
    COMMENT = 'COMMENT', 'Bình luận mới'
    MILESTONE_DUE = 'MILESTONE_DUE', 'Milestone sắp đến hạn'
    PROJECT_APPROVED = 'PROJECT_APPROVED', 'Đồ án được thông qua'
    SYSTEM = 'SYSTEM', 'Thông báo hệ thống'

class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications', verbose_name="Người nhận")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications', verbose_name="Người gửi")
    title = models.CharField(max_length=255, verbose_name="Tiêu đề thông báo")
    message = models.TextField(verbose_name="Nội dung thông báo")
    link = models.CharField(max_length=500, blank=True, null=True, verbose_name="Đường dẫn chuyển hướng")
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices, default=NotificationType.SYSTEM, verbose_name="Loại thông báo")
    is_read = models.BooleanField(default=False, verbose_name="Đã đọc")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Thông báo"
        verbose_name_plural = "Danh sách Thông báo"

    def __str__(self):
        return f"Notify to {self.recipient.username}: {self.title}"

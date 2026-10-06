from django.db import models
from django.conf import settings
from django.utils import timezone
from projects.models import Project
from tasks.models import Task


class TimeLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='time_logs', verbose_name="Người dùng")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='time_logs', verbose_name="Đồ án")
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, related_name='time_logs', verbose_name="Công việc")
    started_at = models.DateTimeField(default=timezone.now, verbose_name="Thời điểm bắt đầu")
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời điểm kết thúc")
    duration = models.PositiveIntegerField(default=0, verbose_name="Thời lượng (giây)")
    note = models.CharField(max_length=255, blank=True, null=True, verbose_name="Ghi chú công việc")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-started_at']
        verbose_name = "Nhật ký thời gian (Time Log)"
        verbose_name_plural = "Danh sách Nhật ký thời gian"

    def __str__(self):
        return f"{self.user.display_name} - {self.project.code} ({self.duration}s)"


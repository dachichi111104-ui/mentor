from django.db import models
from django.utils import timezone
from projects.models import Project

class MilestoneStatus(models.TextChoices):
    PENDING = 'PENDING', 'Chưa bắt đầu'
    IN_PROGRESS = 'IN_PROGRESS', 'Đang thực hiện'
    COMPLETED = 'COMPLETED', 'Đã hoàn thành'
    OVERDUE = 'OVERDUE', 'Quá hạn'

class Milestone(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones', verbose_name="Đồ án")
    name = models.CharField(max_length=255, verbose_name="Tên Giai đoạn / Milestone")
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả công việc")
    start_date = models.DateField(verbose_name="Ngày bắt đầu")
    due_date = models.DateField(verbose_name="Hạn hoàn thành")
    status = models.CharField(max_length=20, choices=MilestoneStatus.choices, default=MilestoneStatus.PENDING, db_index=True, verbose_name="Trạng thái")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date']
        verbose_name = "Milestone"
        verbose_name_plural = "Danh sách Milestone"

    def __str__(self):
        return f"{self.project.code} - {self.name}"

    @property
    def is_overdue(self):
        if self.status != MilestoneStatus.COMPLETED and self.due_date < timezone.now().date():
            return True
        return False

    @property
    def progress_percentage(self):
        total_tasks = self.tasks.count()
        if total_tasks == 0:
            return 100 if self.status == MilestoneStatus.COMPLETED else 0
        completed_tasks = self.tasks.filter(status='DONE').count()
        return int((completed_tasks / total_tasks) * 100)

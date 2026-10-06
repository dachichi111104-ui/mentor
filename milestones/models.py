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


class EventType(models.TextChoices):
    MEETING = 'MEETING', 'Họp nhóm / Mentor'
    REVIEW = 'REVIEW', 'Đánh giá / Nộp bản thảo'
    DEADLINE = 'DEADLINE', 'Hạn chót công việc'
    PERSONAL = 'PERSONAL', 'Cá nhân / Lịch hẹn'


class EventStatus(models.TextChoices):
    PENDING = 'PENDING', 'Chờ xác nhận'
    ACCEPTED = 'ACCEPTED', 'Đã xác nhận'
    REJECTED = 'REJECTED', 'Đã từ chối'


class Event(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='events', verbose_name="Đồ án")
    title = models.CharField(max_length=255, verbose_name="Tiêu đề sự kiện")
    event_type = models.CharField(max_length=20, choices=EventType.choices, default=EventType.MEETING, verbose_name="Loại sự kiện")
    start = models.DateTimeField(verbose_name="Bắt đầu")
    end = models.DateTimeField(null=True, blank=True, verbose_name="Kết thúc")
    participants = models.ManyToManyField('accounts.User', blank=True, related_name='calendar_events', verbose_name="Thành viên tham gia")
    link = models.CharField(max_length=500, blank=True, null=True, verbose_name="Link Họp trực tuyến")
    status = models.CharField(max_length=20, choices=EventStatus.choices, default=EventStatus.ACCEPTED, verbose_name="Trạng thái xác nhận")
    created_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='created_events', verbose_name="Người tạo")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start']
        verbose_name = "Sự kiện lịch"
        verbose_name_plural = "Danh sách Sự kiện lịch"

    def __str__(self):
        return f"[{self.get_event_type_display()}] {self.title} ({self.start.strftime('%d/%m/%Y %H:%M')})"


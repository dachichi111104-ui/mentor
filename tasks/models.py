from django.db import models
from django.conf import settings
from django.utils import timezone
from projects.models import Project
from milestones.models import Milestone

class TaskPriority(models.TextChoices):
    LOW = 'LOW', 'Thấp'
    MEDIUM = 'MEDIUM', 'Trung bình'
    HIGH = 'HIGH', 'Cao'
    CRITICAL = 'CRITICAL', 'Khẩn cấp'

class TaskStatus(models.TextChoices):
    TODO = 'TODO', 'Cần làm'
    IN_PROGRESS = 'IN_PROGRESS', 'Đang làm'
    REVIEW = 'REVIEW', 'Đang Review'
    DONE = 'DONE', 'Hoàn thành'

class Board(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='boards', verbose_name="Đồ án")
    name = models.CharField(max_length=255, default="Bảng Kanban Đồ án", verbose_name="Tên Bảng")
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bảng Kanban"
        verbose_name_plural = "Danh sách Bảng Kanban"

    def __str__(self):
        return f"{self.project.code} - {self.name}"

class Sprint(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='sprints', verbose_name="Đồ án")
    name = models.CharField(max_length=255, verbose_name="Tên Sprint")
    goal = models.TextField(blank=True, null=True, verbose_name="Mục tiêu Sprint")
    start_date = models.DateField(verbose_name="Ngày bắt đầu")
    end_date = models.DateField(verbose_name="Ngày kết thúc")
    is_active = models.BooleanField(default=True, verbose_name="Sprint đang chạy")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date']
        verbose_name = "Sprint"
        verbose_name_plural = "Danh sách Sprint"

    def __str__(self):
        return f"{self.project.code} - {self.name}"

class BoardColumn(models.Model):
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='columns', verbose_name="Bảng Kanban")
    title = models.CharField(max_length=100, verbose_name="Tên cột")
    status_code = models.CharField(max_length=50, choices=TaskStatus.choices, default=TaskStatus.TODO, verbose_name="Mã trạng thái tương ứng")
    order_index = models.IntegerField(default=0, verbose_name="Thứ tự hiển thị")

    class Meta:
        ordering = ['order_index']
        verbose_name = "Cột Bảng Kanban"
        verbose_name_plural = "Danh sách Cột Bảng Kanban"

    def __str__(self):
        return f"{self.board.name} - Cột {self.title}"

class Task(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks', verbose_name="Đồ án")
    milestone = models.ForeignKey(Milestone, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks', verbose_name="Milestone")
    sprint = models.ForeignKey(Sprint, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks', verbose_name="Sprint (Scrum)")
    board_column = models.ForeignKey(BoardColumn, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks', verbose_name="Cột Kanban")
    
    title = models.CharField(max_length=255, verbose_name="Tiêu đề công việc")
    description = models.TextField(blank=True, null=True, verbose_name="Chi tiết công việc")
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        verbose_name="Người thực hiện"
    )
    priority = models.CharField(max_length=20, choices=TaskPriority.choices, default=TaskPriority.MEDIUM, verbose_name="Độ ưu tiên")
    status = models.CharField(max_length=20, choices=TaskStatus.choices, default=TaskStatus.TODO, db_index=True, verbose_name="Trạng thái")
    due_date = models.DateField(blank=True, null=True, db_index=True, verbose_name="Hạn hoàn thành")
    labels = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nhãn (cách nhau bởi dấu phẩy)")
    order_index = models.IntegerField(default=0, verbose_name="Thứ tự Kanban")
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_tasks',
        verbose_name="Người tạo"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order_index', '-created_at']
        verbose_name = "Công việc"
        verbose_name_plural = "Danh sách Công việc"

    def __str__(self):
        return f"{self.project.code} - {self.title}"

    @property
    def is_overdue(self):
        if self.status != TaskStatus.DONE and self.due_date and self.due_date < timezone.now().date():
            return True
        return False

class TaskComment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments', verbose_name="Công việc")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField(verbose_name="Nội dung bình luận")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = "Bình luận"
        verbose_name_plural = "Bình luận công việc"

    def __str__(self):
        return f"{self.user.display_name} on {self.task.title}"

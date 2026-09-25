from django.db import models
from django.conf import settings

class ProjectStatus(models.TextChoices):
    PLANNING = 'PLANNING', 'Lập kế hoạch'
    IN_PROGRESS = 'IN_PROGRESS', 'Đang thực hiện'
    REVIEW = 'REVIEW', 'Đang chờ Review'
    COMPLETED = 'COMPLETED', 'Hoàn thành'
    ARCHIVED = 'ARCHIVED', 'Lưu trữ'

class ProjectCategory(models.TextChoices):
    WEB = 'WEB', 'Phát triển Web'
    MOBILE = 'MOBILE', 'Lập trình Di động'
    AI_ML = 'AI_ML', 'Trí tuệ nhân tạo & Machine Learning'
    IOT = 'IOT', 'Internet of Things'
    SYSTEM = 'SYSTEM', 'Hệ thống & Mạng'
    OTHER = 'OTHER', 'Khác'

class MentorStatus(models.TextChoices):
    NONE = 'NONE', 'Chưa chọn Mentor'
    PENDING = 'PENDING', 'Chờ Mentor xác nhận'
    ACCEPTED = 'ACCEPTED', 'Đã nhận hướng dẫn'
    REJECTED = 'REJECTED', 'Mentor từ chối'

class Project(models.Model):
    name = models.CharField(max_length=255, verbose_name="Tên đồ án")
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã đồ án")
    description = models.TextField(verbose_name="Mô tả đồ án")
    category = models.CharField(max_length=50, choices=ProjectCategory.choices, default=ProjectCategory.WEB, verbose_name="Thể loại")
    technology = models.CharField(max_length=255, verbose_name="Công nghệ sử dụng")
    start_date = models.DateField(verbose_name="Ngày bắt đầu")
    end_date = models.DateField(verbose_name="Ngày kết thúc (Deadline)")
    status = models.CharField(max_length=20, choices=ProjectStatus.choices, default=ProjectStatus.PLANNING, verbose_name="Trạng thái")
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_projects',
        verbose_name="Trưởng nhóm / Người tạo"
    )
    mentor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mentored_projects',
        verbose_name="Mentor / Giảng viên hướng dẫn"
    )
    mentor_status = models.CharField(
        max_length=20,
        choices=MentorStatus.choices,
        default=MentorStatus.NONE,
        verbose_name="Trạng thái xác nhận Mentor"
    )
    
    repo_url = models.URLField(blank=True, null=True, verbose_name="URL Repository (GitHub/GitLab)")
    demo_url = models.URLField(blank=True, null=True, verbose_name="URL Demo (Live Site)")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Ngày cập nhật")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Đồ án"
        verbose_name_plural = "Danh sách Đồ án"

    def __str__(self):
        return f"[{self.code}] {self.name}"

    @property
    def progress_percentage(self):
        total_tasks = self.tasks.count()
        if total_tasks == 0:
            return 0
        completed_tasks = self.tasks.filter(status='DONE').count()
        return int((completed_tasks / total_tasks) * 100)

class MemberRole(models.TextChoices):
    LEADER = 'LEADER', 'Trưởng nhóm'
    MEMBER = 'MEMBER', 'Thành viên'

class MemberStatus(models.TextChoices):
    PENDING = 'PENDING', 'Chờ xác nhận'
    ACCEPTED = 'ACCEPTED', 'Đã tham gia'

class ProjectMember(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='project_memberships')
    role = models.CharField(max_length=20, choices=MemberRole.choices, default=MemberRole.MEMBER)
    status = models.CharField(max_length=20, choices=MemberStatus.choices, default=MemberStatus.PENDING)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'user')
        indexes = [
            models.Index(fields=['user', 'status']),
        ]
        verbose_name = "Thành viên đồ án"
        verbose_name_plural = "Danh sách Thành viên đồ án"

    def __str__(self):
        return f"{self.user.display_name} - {self.project.name} ({self.get_role_display()})"

from django.contrib.auth.models import AbstractUser
from django.db import models

class UserRole(models.TextChoices):
    STUDENT = 'STUDENT', 'Sinh viên'
    MENTOR = 'MENTOR', 'Giảng viên / Mentor'
    ADMIN = 'ADMIN', 'Quản trị viên'

class UserStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Hoạt động'
    SUSPENDED = 'SUSPENDED', 'Đã khóa'

class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.STUDENT,
        verbose_name="Vai trò"
    )
    status = models.CharField(
        max_length=20,
        choices=UserStatus.choices,
        default=UserStatus.ACTIVE,
        verbose_name="Trạng thái"
    )
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Số điện thoại")
    student_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="Mã sinh viên / Mã GV")
    department = models.CharField(max_length=100, blank=True, null=True, verbose_name="Khoa / Viện")
    class_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Lớp chuyên ngành")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="Ảnh đại diện")
    avatar_url = models.CharField(max_length=500, blank=True, null=True, verbose_name="Avatar URL fallback")
    bio = models.TextField(blank=True, null=True, verbose_name="Giới thiệu bản thân")
    skills = models.CharField(max_length=255, blank=True, null=True, verbose_name="Kỹ năng chuyên môn")
    specialization = models.CharField(max_length=255, blank=True, null=True, verbose_name="Lĩnh vực nghiên cứu / Hướng dẫn")
    experience = models.TextField(blank=True, null=True, verbose_name="Kinh nghiệm (Mentor)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Ngày cập nhật")

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    @property
    def is_student(self):
        return self.role == UserRole.STUDENT

    @property
    def is_mentor(self):
        return self.role == UserRole.MENTOR

    @property
    def is_admin_user(self):
        return self.role == UserRole.ADMIN or self.is_superuser

    def get_avatar_url(self):
        if self.avatar:
            from django.urls import reverse
            try:
                return reverse('user_avatar', args=[self.id])
            except Exception:
                if hasattr(self.avatar, 'url'):
                    return self.avatar.url
        if self.avatar_url:
            return self.avatar_url
        name = self.display_name.replace(' ', '+')
        return f"https://ui-avatars.com/api/?name={name}&background=0F172A&color=F59E0B&font-size=0.35&bold=true"

    @property
    def profile_completion(self):
        if self.is_mentor:
            items = [
                {'field': 'avatar', 'label': 'Ảnh đại diện', 'val': self.avatar, 'anchor': '#id_avatar'},
                {'field': 'phone', 'label': 'Số điện thoại', 'val': self.phone, 'anchor': '#id_phone'},
                {'field': 'department', 'label': 'Khoa / Viện', 'val': self.department, 'anchor': '#id_department'},
                {'field': 'bio', 'label': 'Giới thiệu bản thân', 'val': self.bio, 'anchor': '#id_bio'},
                {'field': 'specialization', 'label': 'Hướng nghiên cứu', 'val': self.specialization, 'anchor': '#id_specialization'},
                {'field': 'experience', 'label': 'Kinh nghiệm Hướng dẫn', 'val': self.experience, 'anchor': '#id_experience'},
            ]
        else:
            items = [
                {'field': 'avatar', 'label': 'Ảnh đại diện', 'val': self.avatar, 'anchor': '#id_avatar'},
                {'field': 'phone', 'label': 'Số điện thoại', 'val': self.phone, 'anchor': '#id_phone'},
                {'field': 'department', 'label': 'Khoa / Viện', 'val': self.department, 'anchor': '#id_department'},
                {'field': 'bio', 'label': 'Giới thiệu bản thân', 'val': self.bio, 'anchor': '#id_bio'},
                {'field': 'student_id', 'label': 'Mã sinh viên', 'val': self.student_id, 'anchor': '#id_student_id'},
                {'field': 'class_name', 'label': 'Lớp chuyên ngành', 'val': self.class_name, 'anchor': '#id_class_name'},
            ]
        
        filled = sum(1 for item in items if bool(item['val']))
        total = len(items)
        percent = int(filled / total * 100) if total > 0 else 0
        missing = [item for item in items if not bool(item['val'])]
        
        return {
            'filled': filled,
            'completed': filled,
            'total': total,
            'percent': percent,
            'percentage': percent,
            'items': items,
            'missing': missing,
            'is_fully_completed': filled == total
        }


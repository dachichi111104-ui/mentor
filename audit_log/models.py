from django.db import models
from django.conf import settings

class ActionType(models.TextChoices):
    LOGIN = 'LOGIN', 'Đăng nhập hệ thống'
    LOGOUT = 'LOGOUT', 'Đăng xuất hệ thống'
    CREATE_PROJECT = 'CREATE_PROJECT', 'Tạo đồ án mới'
    UPDATE_PROJECT = 'UPDATE_PROJECT', 'Cập nhật đồ án'
    DELETE_PROJECT = 'DELETE_PROJECT', 'Xóa đồ án'
    CREATE_TASK = 'CREATE_TASK', 'Tạo công việc'
    UPDATE_TASK = 'UPDATE_TASK', 'Cập nhật công việc'
    DELETE_TASK = 'DELETE_TASK', 'Xóa công việc'
    UPLOAD_DOCUMENT = 'UPLOAD_DOCUMENT', 'Tải lên tài liệu'
    DELETE_DOCUMENT = 'DELETE_DOCUMENT', 'Xóa tài liệu'
    SUBMIT_REVIEW = 'SUBMIT_REVIEW', 'Gửi nhận xét Review'
    LOCK_USER = 'LOCK_USER', 'Khóa tài khoản'
    UNLOCK_USER = 'UNLOCK_USER', 'Mở khóa tài khoản'
    SYSTEM_CONFIG = 'SYSTEM_CONFIG', 'Cấu hình hệ thống'

class ActivityLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs', verbose_name="Người thực hiện")
    action = models.CharField(max_length=50, choices=ActionType.choices, verbose_name="Hành động")
    entity_type = models.CharField(max_length=100, blank=True, null=True, verbose_name="Đối tượng tác động")
    entity_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="ID Đối tượng")
    description = models.TextField(verbose_name="Chi tiết nhật ký")
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="Địa chỉ IP")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Nhật ký hệ thống"
        verbose_name_plural = "Lịch sử hoạt động (Audit Logs)"

    def __str__(self):
        user_str = self.user.display_name if self.user else "Hệ thống"
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M')}] {user_str} - {self.get_action_display()}"

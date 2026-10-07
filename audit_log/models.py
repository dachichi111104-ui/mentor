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
    CREATE_MILESTONE = 'CREATE_MILESTONE', 'Tạo mốc Milestone'
    UPDATE_MILESTONE = 'UPDATE_MILESTONE', 'Cập nhật mốc Milestone'
    DELETE_MILESTONE = 'DELETE_MILESTONE', 'Xóa mốc Milestone'
    LOCK_USER = 'LOCK_USER', 'Khóa tài khoản'
    UNLOCK_USER = 'UNLOCK_USER', 'Mở khóa tài khoản'
    SYSTEM_CONFIG = 'SYSTEM_CONFIG', 'Cấu hình hệ thống'
    CREATE_USER = 'CREATE_USER', 'Tạo người dùng'
    UPDATE_USER = 'UPDATE_USER', 'Cập nhật người dùng'
    CHANGE_ROLE = 'CHANGE_ROLE', 'Đổi vai trò người dùng'
    APPROVE_USER = 'APPROVE_USER', 'Duyệt giảng viên'
    REJECT_USER = 'REJECT_USER', 'Từ chối đăng ký'
    RESET_PASSWORD = 'RESET_PASSWORD', 'Đặt lại mật khẩu'
    ADD_COMMENT = 'ADD_COMMENT', 'Thêm bình luận'
    CHANGE_STATUS = 'CHANGE_STATUS', 'Chuyển trạng thái'
    CREATE_EVENT = 'CREATE_EVENT', 'Tạo sự kiện lịch'
    UPDATE_EVENT = 'UPDATE_EVENT', 'Cập nhật sự kiện lịch'
    DELETE_EVENT = 'DELETE_EVENT', 'Xóa sự kiện lịch'
    MEMBER_CHANGE = 'MEMBER_CHANGE', 'Thay đổi thành viên'
    AI_GENERATE = 'AI_GENERATE', 'Yêu cầu AI phân tích'
    AI_APPLY = 'AI_APPLY', 'Áp dụng đề xuất AI'
    AI_PROPOSE = 'AI_PROPOSE', 'Gửi đề xuất AI'

class ActivityLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs', verbose_name="Người thực hiện")
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, null=True, blank=True, related_name='activity_logs', verbose_name="Đồ án liên quan")
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

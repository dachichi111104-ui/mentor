from django.db import models
from django.conf import settings
from projects.models import Project

class FileCategory(models.TextChoices):
    PDF = 'PDF', 'Tài liệu PDF'
    WORD = 'WORD', 'Word (DOC/DOCX)'
    EXCEL = 'EXCEL', 'Excel (XLS/XLSX)'
    POWERPOINT = 'POWERPOINT', 'PowerPoint (PPT/PPTX)'
    ZIP = 'ZIP', 'File Nén (ZIP/RAR)'
    IMAGE = 'IMAGE', 'Hình ảnh'
    CODE = 'CODE', 'Mã nguồn / Text'
    OTHER = 'OTHER', 'Khác'

class Document(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='documents', verbose_name="Đồ án")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_documents', verbose_name="Người tải lên")
    title = models.CharField(max_length=255, verbose_name="Tên tài liệu")
    file = models.FileField(upload_to='project_documents/', verbose_name="Tệp đính kèm")
    file_type = models.CharField(max_length=20, choices=FileCategory.choices, default=FileCategory.PDF, verbose_name="Loại tệp")
    file_size = models.CharField(max_length=50, blank=True, null=True, verbose_name="Dung lượng")
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả tài liệu")
    current_version = models.IntegerField(default=1, verbose_name="Phiên bản hiện tại")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Tài liệu"
        verbose_name_plural = "Danh sách Tài liệu"

    def __str__(self):
        return f"{self.project.code} - {self.title}"

class DocumentVersion(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='versions', verbose_name="Tài liệu")
    file = models.FileField(upload_to='project_documents/versions/', verbose_name="Tệp phiên bản")
    version_number = models.IntegerField(verbose_name="Số phiên bản")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Người cập nhật")
    change_log = models.TextField(blank=True, null=True, verbose_name="Ghi chú thay đổi")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version_number']
        verbose_name = "Phiên bản tài liệu"
        verbose_name_plural = "Lịch sử phiên bản tài liệu"

    def __str__(self):
        return f"{self.document.title} (v{self.version_number})"

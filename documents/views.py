import mimetypes
import hashlib
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import Http404, FileResponse, HttpResponse
from django.utils import timezone

from documents.models import Document, DocumentVersion, FileCategory
from projects.models import Project
from projects.permissions import visible_projects, require_can, can
from audit_log.models import ActionType
from audit_log.utils import log_action

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'zip', 'rar', 'png', 'jpg', 'jpeg', 'py', 'js', 'java', 'cpp', 'md', 'txt'}
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20MB

MAGIC_BYTES = {
    'pdf': b'%PDF',
    'png': b'\x89PNG\r\n\x1a\n',
    'jpg': b'\xff\xd8\xff',
    'jpeg': b'\xff\xd8\xff',
    'zip': b'PK\x03\x04',
    'docx': b'PK\x03\x04',
    'xlsx': b'PK\x03\x04',
    'pptx': b'PK\x03\x04',
}

def validate_uploaded_file(file_obj):
    if not file_obj:
        return False, "Vui lòng chọn file."
    if file_obj.size > MAX_FILE_SIZE_BYTES:
        size_mb = round(file_obj.size / (1024 * 1024), 2)
        return False, f"Dung lượng file ({size_mb} MB) vượt quá giới hạn cho phép (tối đa 20 MB)."

    ext = file_obj.name.split('.')[-1].lower() if '.' in file_obj.name else ''
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Định dạng file .{ext} không hợp lệ. Các định dạng được phép: {', '.join(sorted(ALLOWED_EXTENSIONS))}."

    # Magic Bytes Validation (SEC-14)
    if ext in MAGIC_BYTES:
        expected_header = MAGIC_BYTES[ext]
        file_obj.seek(0)
        header = file_obj.read(len(expected_header))
        file_obj.seek(0)
        if not header.startswith(expected_header):
            return False, f"Tệp tin .{ext} không khớp với chữ ký nhị phân thực tế."

    file_obj.seek(0)
    file_sha256 = hashlib.sha256(file_obj.read()).hexdigest()
    file_obj.seek(0)
    file_obj.sha256 = file_sha256

    return True, None

def _deduce_category(ext):
    ext = ext.lower()
    if ext == 'pdf':
        return FileCategory.PDF
    elif ext in {'doc', 'docx'}:
        return FileCategory.WORD
    elif ext in {'xls', 'xlsx'}:
        return FileCategory.EXCEL
    elif ext in {'ppt', 'pptx'}:
        return FileCategory.POWERPOINT
    elif ext in {'zip', 'rar', '7z'}:
        return FileCategory.ZIP
    elif ext in {'png', 'jpg', 'jpeg', 'gif', 'webp'}:
        return FileCategory.IMAGE
    elif ext in {'py', 'js', 'java', 'cpp', 'html', 'css', 'json', 'sql'}:
        return FileCategory.CODE
    return FileCategory.OTHER

@login_required
@require_can('document.view')
def project_documents_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    request.breadcrumb_obj = project

    documents = project.documents.all()
    file_type = request.GET.get('type')
    if file_type:
        documents = documents.filter(file_type=file_type)
    return render(request, 'documents/document_list.html', {'project': project, 'documents': documents, 'file_type': file_type})

@login_required
def all_documents_view(request):
    user = request.user
    upload_projects = visible_projects(user)
    documents = Document.objects.filter(project__in=upload_projects).distinct()

    return render(request, 'documents/all_documents.html', {
        'documents': documents,
        'upload_projects': upload_projects,
    })

@login_required
@require_POST
def all_document_upload_view(request):
    project_id = request.POST.get('project_id')
    if not project_id:
        messages.error(request, 'Vui lòng chọn đồ án.')
        return redirect('document_list')

    return document_upload_view(request, project_id)

from core.ratelimit import ratelimit
import hashlib

@login_required
@require_POST
@ratelimit('document_upload', limit=30, period=3600)
def document_upload_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not can(request.user, 'document.upload', project):
        return render(request, 'errors/403.html', status=403)

    title = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    file_obj = request.FILES.get('file')

    is_valid, err_msg = validate_uploaded_file(file_obj)
    if not is_valid:
        messages.error(request, err_msg)
        return redirect('project_documents', project_id=project.id)

    ext = file_obj.name.split('.')[-1].lower() if '.' in file_obj.name else ''
    file_category = _deduce_category(ext)

    if not title:
        title = file_obj.name

    size_mb = round(file_obj.size / (1024 * 1024), 2)
    doc = Document.objects.create(
        project=project,
        uploaded_by=request.user,
        title=title,
        file=file_obj,
        file_type=file_category,
        file_size=f"{size_mb} MB" if size_mb > 0.1 else f"{round(file_obj.size/1024, 1)} KB",
        description=description,
        current_version=1
    )

    DocumentVersion.objects.create(
        document=doc,
        file=file_obj,
        version_number=1,
        uploaded_by=request.user,
        change_log="Phiên bản khởi tạo ban đầu."
    )

    log_action(
        user=request.user,
        action=ActionType.UPLOAD_DOCUMENT,
        entity_type='Document',
        entity_id=doc.id,
        description=f'Tải lên tài liệu mới "{doc.title}" ({doc.file_size})',
        project=project,
        request=request
    )
    messages.success(request, f'Tải lên tài liệu "{doc.title}" thành công!')
    return redirect('project_documents', project_id=project.id)

@login_required
@require_POST
def document_version_upload_view(request, document_id):
    doc = get_object_or_404(Document, id=document_id)
    if not can(request.user, 'document.version', doc.project):
        return render(request, 'errors/403.html', status=403)

    file_obj = request.FILES.get('file')
    change_log = request.POST.get('change_log', '').strip()

    is_valid, err_msg = validate_uploaded_file(file_obj)
    if not is_valid:
        messages.error(request, err_msg)
        return redirect('project_documents', project_id=doc.project.id)

    new_version_num = doc.current_version + 1
    size_mb = round(file_obj.size / (1024 * 1024), 2)

    doc.file = file_obj
    doc.file_size = f"{size_mb} MB" if size_mb > 0.1 else f"{round(file_obj.size/1024, 1)} KB"
    doc.current_version = new_version_num
    doc.updated_at = timezone.now()
    doc.save()

    DocumentVersion.objects.create(
        document=doc,
        file=file_obj,
        version_number=new_version_num,
        uploaded_by=request.user,
        change_log=change_log or f"Cập nhật phiên bản v{new_version_num}"
    )

    log_action(
        user=request.user,
        action=ActionType.UPLOAD_DOCUMENT,
        entity_type='DocumentVersion',
        entity_id=doc.id,
        description=f'Cập nhật phiên bản v{new_version_num} cho tài liệu "{doc.title}"',
        project=doc.project,
        request=request
    )
    messages.success(request, f'Đã cập nhật tài liệu "{doc.title}" lên phiên bản v{new_version_num}!')
    return redirect('project_documents', project_id=doc.project.id)

@login_required
@require_POST
def document_delete_view(request, document_id):
    doc = get_object_or_404(Document, id=document_id)
    if not can(request.user, 'document.delete', doc):
        return render(request, 'errors/403.html', status=403)

    project_id = doc.project.id
    title = doc.title
    doc.delete()
    log_action(
        user=request.user,
        action=ActionType.DELETE_DOCUMENT,
        entity_type='Document',
        entity_id=document_id,
        description=f'Xóa tài liệu "{title}" khỏi đồ án',
        project=doc.project,
        request=request
    )
    messages.success(request, f'Đã xóa tài liệu "{title}".')
    return redirect('project_documents', project_id=project_id)

@login_required
def document_download_view(request, document_id):
    doc = get_object_or_404(Document, id=document_id)
    if not can(request.user, 'document.view', doc):
        return render(request, 'errors/403.html', status=403)

    if not doc.file:
        return render(request, 'errors/410.html', {'message': 'Tệp không còn tồn tại trên máy chủ.'}, status=410)

    try:
        f = doc.file.open('rb')
        ext = doc.file.name.split('.')[-1] if '.' in doc.file.name else 'bin'
        return FileResponse(f, as_attachment=True, filename=f"{doc.title}.{ext}")
    except Exception:
        return render(request, 'errors/410.html', {'message': 'Tệp không còn tồn tại hoặc bị lỗi đĩa lưu trữ.'}, status=410)

@login_required
@xframe_options_sameorigin
def document_preview_view(request, document_id):
    doc = get_object_or_404(Document, id=document_id)
    if not can(request.user, 'document.view', doc):
        return render(request, 'errors/403.html', status=403)

    request.breadcrumb_obj = doc

    ext = doc.file.name.split('.')[-1].lower() if doc.file and '.' in doc.file.name else 'pdf'
    is_pdf = ext == 'pdf'
    is_image = ext in {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    is_text = ext in {'txt', 'md', 'py', 'js', 'json', 'cpp', 'java', 'css', 'xml', 'sql', 'sh', 'yml', 'yaml'}
    is_office = ext in {'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}

    text_content = ""
    if doc.file and is_text:
        try:
            with doc.file.open('rb') as f:
                text_content = f.read(50000).decode('utf-8', errors='ignore')
        except Exception:
            text_content = "Không thể đọc nội dung văn bản của tập tin này."

    raw_url = request.build_absolute_uri(f"/documents/{doc.id}/raw/")

    return render(request, 'documents/document_preview.html', {
        'doc': doc,
        'file_extension': ext,
        'is_pdf': is_pdf,
        'is_image': is_image,
        'is_text': is_text,
        'is_office': is_office,
        'text_content': text_content,
        'raw_url': raw_url,
    })

@login_required
@xframe_options_sameorigin
def document_raw_view(request, document_id):
    doc = get_object_or_404(Document, id=document_id)
    if not can(request.user, 'document.view', doc):
        return render(request, 'errors/403.html', status=403)

    if not doc.file:
        return render(request, 'errors/410.html', {'message': 'Tệp không còn tồn tại.'}, status=410)

    filename = doc.file.name
    content_type, _ = mimetypes.guess_type(filename)
    content_type = content_type or 'application/octet-stream'

    # Security: Do NOT serve html, js, or svg as raw inline HTML (prevent XSS SEC-9)
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    if ext in {'html', 'htm', 'js', 'svg'}:
        content_type = 'text/plain; charset=utf-8'

    try:
        f = doc.file.open('rb')
        response = FileResponse(f, as_attachment=False, content_type=content_type)
        response['X-Content-Type-Options'] = 'nosniff'
        return response
    except Exception:
        return render(request, 'errors/410.html', {'message': 'Tệp tin không thể mở từ đĩa.'}, status=410)

@login_required
def document_version_download_view(request, version_id):
    version = get_object_or_404(DocumentVersion, id=version_id)
    if not can(request.user, 'document.view', version.document):
        return render(request, 'errors/403.html', status=403)

    if not version.file:
        return render(request, 'errors/410.html', {'message': 'Phiên bản tệp không tồn tại.'}, status=410)

    try:
        f = version.file.open('rb')
        ext = version.file.name.split('.')[-1] if '.' in version.file.name else 'bin'
        return FileResponse(f, as_attachment=True, filename=f"{version.document.title}_v{version.version_number}.{ext}")
    except Exception:
        return render(request, 'errors/410.html', {'message': 'Phiên bản tệp không tồn tại trên đĩa.'}, status=410)

@login_required
def document_version_preview_view(request, version_id):
    version = get_object_or_404(DocumentVersion, id=version_id)
    return document_preview_view(request, version.document.id)

@login_required
def document_version_raw_view(request, version_id):
    version = get_object_or_404(DocumentVersion, id=version_id)
    return document_raw_view(request, version.document.id)

@login_required
@require_POST
def document_rollback_view(request, document_id, version_id):
    doc = get_object_or_404(Document, id=document_id)
    if not can(request.user, 'document.rollback', doc):
        return render(request, 'errors/403.html', status=403)

    target_version = get_object_or_404(DocumentVersion, id=version_id, document=doc)
    doc.file = target_version.file
    doc.current_version = target_version.version_number
    doc.save()

    log_action(
        user=request.user,
        action=ActionType.UPLOAD_DOCUMENT,
        entity_type='Document',
        entity_id=doc.id,
        description=f'Khôi phục tài liệu "{doc.title}" về phiên bản v{target_version.version_number}',
        project=doc.project,
        request=request
    )
    messages.success(request, f'Đã khôi phục tài liệu "{doc.title}" về phiên bản v{target_version.version_number}.')
    return redirect('project_documents', project_id=doc.project.id)

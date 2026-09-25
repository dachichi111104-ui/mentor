from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from documents.models import Document, DocumentVersion, FileCategory
from projects.models import Project
from projects.permissions import user_can_access_project
from audit_log.models import ActionType
from audit_log.utils import log_action

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'zip', 'rar', 'png', 'jpg', 'jpeg', 'py', 'js', 'java', 'cpp', 'md', 'txt'}
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20MB

def validate_uploaded_file(file_obj):
    if not file_obj:
        return False, "Vui lòng chọn file."
    if file_obj.size > MAX_FILE_SIZE_BYTES:
        size_mb = round(file_obj.size / (1024 * 1024), 2)
        return False, f"Dung lượng file ({size_mb} MB) vượt quá giới hạn cho phép (tối đa 20 MB)."
    ext = file_obj.name.split('.')[-1].lower() if '.' in file_obj.name else ''
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Định dạng file .{ext} không hợp lệ. Các định dạng được phép: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
    return True, None

@login_required
def project_documents_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not user_can_access_project(request.user, project):
        return render(request, 'errors/403.html', status=403)

    documents = project.documents.all()
    file_type = request.GET.get('type')
    if file_type:
        documents = documents.filter(file_type=file_type)
    return render(request, 'documents/document_list.html', {'project': project, 'documents': documents, 'file_type': file_type})

@login_required
def all_documents_view(request):
    user = request.user
    if user.is_admin_user:
        documents = Document.objects.all()
        upload_projects = Project.objects.all()
    elif user.is_mentor:
        documents = Document.objects.filter(project__mentor=user, project__mentor_status='ACCEPTED')
        upload_projects = Project.objects.filter(mentor=user, mentor_status='ACCEPTED')
    else:
        documents = Document.objects.filter(project__memberships__user=user, project__memberships__status='ACCEPTED')
        upload_projects = Project.objects.filter(memberships__user=user, memberships__status='ACCEPTED')
        
    return render(request, 'documents/all_documents.html', {
        'documents': documents.distinct(),
        'upload_projects': upload_projects.distinct(),
    })

@login_required
def document_upload_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not user_can_access_project(request.user, project):
        return render(request, 'errors/403.html', status=403)

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        file_obj = request.FILES.get('file')
        file_type = request.POST.get('file_type', FileCategory.PDF)
        
        is_valid, err_msg = validate_uploaded_file(file_obj)
        if not is_valid:
            messages.error(request, err_msg)
            return redirect('project_documents', project_id=project.id)

        size_mb = round(file_obj.size / (1024 * 1024), 2)
        doc = Document.objects.create(
            project=project,
            uploaded_by=request.user,
            title=title,
            file=file_obj,
            file_type=file_type,
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
            description=f'Tải lên tài liệu mới: {title} cho đồ án {project.code}',
            request=request
        )
        messages.success(request, f'Tải lên tài liệu "{title}" thành công!')
    return redirect('project_documents', project_id=project.id)

@login_required
def document_version_upload_view(request, document_id):
    doc = get_object_or_404(Document, id=document_id)
    if not user_can_access_project(request.user, doc.project):
        return render(request, 'errors/403.html', status=403)

    if request.method == 'POST':
        file_obj = request.FILES.get('file')
        change_log = request.POST.get('change_log', '')
        
        is_valid, err_msg = validate_uploaded_file(file_obj)
        if not is_valid:
            messages.error(request, err_msg)
            return redirect('project_documents', project_id=doc.project.id)

        new_version_number = doc.current_version + 1
        doc.file = file_obj
        doc.current_version = new_version_number
        size_mb = round(file_obj.size / (1024 * 1024), 2)
        doc.file_size = f"{size_mb} MB" if size_mb > 0.1 else f"{round(file_obj.size/1024, 1)} KB"
        doc.save()

        DocumentVersion.objects.create(
            document=doc,
            file=file_obj,
            version_number=new_version_number,
            uploaded_by=request.user,
            change_log=change_log
        )

        log_action(
            user=request.user,
            action=ActionType.UPLOAD_DOCUMENT,
            entity_type='DocumentVersion',
            entity_id=doc.id,
            description=f'Cập nhật tài liệu "{doc.title}" lên phiên bản v{new_version_number}',
            request=request
        )

        messages.success(request, f'Đã cập nhật tài liệu "{doc.title}" lên phiên bản v{new_version_number}!')
    return redirect('project_documents', project_id=doc.project.id)

@login_required
def document_delete_view(request, document_id):
    doc = get_object_or_404(Document, id=document_id)
    if not (doc.uploaded_by == request.user or doc.project.mentor == request.user or request.user.is_admin_user):
        return render(request, 'errors/403.html', status=403)

    if request.method == 'POST':
        project_id = doc.project.id
        doc_title = doc.title
        doc_id = doc.id
        doc.delete()
        log_action(
            user=request.user,
            action=ActionType.DELETE_DOCUMENT,
            entity_type='Document',
            entity_id=doc_id,
            description=f'Xóa tài liệu: "{doc_title}"',
            request=request
        )
        messages.success(request, 'Đã xóa tài liệu.')
        return redirect('project_documents', project_id=project_id)
    return redirect('project_documents', project_id=doc.project.id)

import mimetypes

@login_required
def document_download_view(request, document_id):
    doc = get_object_or_404(Document, id=document_id)
    if not user_can_access_project(request.user, doc.project):
        return render(request, 'errors/403.html', status=403)
    if not doc.file:
        raise Http404("Tài liệu không tồn tại.")
    ext = doc.file.name.split('.')[-1]
    return FileResponse(doc.file.open('rb'), as_attachment=True, filename=f"{doc.title}.{ext}")

@login_required
def document_preview_view(request, document_id):
    doc = get_object_or_404(Document, id=document_id)
    if not user_can_access_project(request.user, doc.project):
        return render(request, 'errors/403.html', status=403)
    if not doc.file:
        raise Http404("Tài liệu không tồn tại.")

    ext = doc.file.name.split('.')[-1].lower() if '.' in doc.file.name else ''
    is_pdf = ext == 'pdf'
    is_image = ext in {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}
    is_text = ext in {'txt', 'md', 'py', 'js', 'json', 'cpp', 'java', 'html', 'css', 'xml'}

    text_content = ""
    if is_text:
        try:
            with doc.file.open('r') as f:
                text_content = f.read(50000)
        except Exception:
            text_content = "Không thể đọc nội dung văn bản này."

    return render(request, 'documents/document_preview.html', {
        'doc': doc,
        'file_extension': ext,
        'is_pdf': is_pdf,
        'is_image': is_image,
        'is_text': is_text,
        'text_content': text_content,
    })

@login_required
def document_raw_view(request, document_id):
    doc = get_object_or_404(Document, id=document_id)
    if not user_can_access_project(request.user, doc.project):
        return render(request, 'errors/403.html', status=403)
    if not doc.file:
        raise Http404("Tài liệu không tồn tại.")
    content_type, _ = mimetypes.guess_type(doc.file.name)
    content_type = content_type or 'application/octet-stream'
    return FileResponse(doc.file.open('rb'), as_attachment=False, content_type=content_type)

@login_required
def document_version_download_view(request, version_id):
    version = get_object_or_404(DocumentVersion, id=version_id)
    if not user_can_access_project(request.user, version.document.project):
        return render(request, 'errors/403.html', status=403)
    if not version.file:
        raise Http404("Tài liệu phiên bản không tồn tại.")
    ext = version.file.name.split('.')[-1]
    return FileResponse(version.file.open('rb'), as_attachment=True, filename=f"{version.document.title}_v{version.version_number}.{ext}")

@login_required
def document_version_preview_view(request, version_id):
    version = get_object_or_404(DocumentVersion, id=version_id)
    if not user_can_access_project(request.user, version.document.project):
        return render(request, 'errors/403.html', status=403)
    if not version.file:
        raise Http404("Tài liệu phiên bản không tồn tại.")
    return redirect('document_preview', document_id=version.document.id)

@login_required
def document_version_raw_view(request, version_id):
    version = get_object_or_404(DocumentVersion, id=version_id)
    if not user_can_access_project(request.user, version.document.project):
        return render(request, 'errors/403.html', status=403)
    if not version.file:
        raise Http404("Tài liệu phiên bản không tồn tại.")
    content_type, _ = mimetypes.guess_type(version.file.name)
    content_type = content_type or 'application/octet-stream'
    return FileResponse(version.file.open('rb'), as_attachment=False, content_type=content_type)

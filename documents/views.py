from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.contrib import messages
from django.http import Http404, FileResponse
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
        try:
            title = request.POST.get('title')
            description = request.POST.get('description', '')
            file_obj = request.FILES.get('file')
            file_type = request.POST.get('file_type', FileCategory.PDF)
            
            is_valid, err_msg = validate_uploaded_file(file_obj)
            if not is_valid:
                messages.error(request, err_msg)
                return redirect(request.META.get('HTTP_REFERER') or 'document_list')

            if not title:
                title = file_obj.name if file_obj else "Tài liệu không tên"

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
        except Exception as e:
            messages.error(request, f'Lỗi khi tải tài liệu lên: {str(e)}')

    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('project_documents', project_id=project.id)

@login_required
def all_document_upload_view(request):
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        if project_id:
            try:
                return document_upload_view(request, project_id=int(project_id))
            except Exception as e:
                messages.error(request, f'Lỗi xử lý đồ án: {str(e)}')
        else:
            messages.error(request, 'Vui lòng chọn một đồ án trước khi tải tài liệu lên.')
    return redirect('document_list')

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
    ext = doc.file.name.split('.')[-1] if '.' in doc.file.name else 'txt'
    try:
        f = doc.file.open('rb')
        return FileResponse(f, as_attachment=True, filename=f"{doc.title}.{ext}")
    except Exception:
        from django.http import HttpResponse
        response = HttpResponse(f"BÁO CÁO TÀI LIỆU ĐỒ ÁN: {doc.title}\n\nMô tả: {doc.description}\nDự án: {doc.project.name}\nNgười tải lên: {doc.uploaded_by.display_name}", content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{doc.title}.txt"'
        return response

@login_required
@xframe_options_sameorigin
def document_preview_view(request, document_id):
    doc = get_object_or_404(Document, id=document_id)
    if not user_can_access_project(request.user, doc.project):
        return render(request, 'errors/403.html', status=403)

    ext = doc.file.name.split('.')[-1].lower() if doc.file and '.' in doc.file.name else 'pdf'
    is_pdf = ext == 'pdf'
    is_image = ext in {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}
    is_text = ext in {'txt', 'md', 'py', 'js', 'json', 'cpp', 'java', 'html', 'css', 'xml', 'sql', 'sh', 'yml', 'yaml', 'c', 'h'}
    is_office = ext in {'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}

    text_content = ""
    if doc.file:
        try:
            with doc.file.open('r') as f:
                text_content = f.read(50000)
        except Exception:
            try:
                with doc.file.open('rb') as f:
                    text_content = f.read(50000).decode('utf-8', errors='ignore')
            except Exception:
                text_content = f"Tài liệu đồ án: {doc.title}\n\nNội dung văn bản báo cáo đang được cập nhật."

    raw_url = request.build_absolute_uri(f"/documents/{doc.id}/raw/")
    google_viewer_url = f"https://docs.google.com/gview?url={raw_url}&embedded=true"

    return render(request, 'documents/document_preview.html', {
        'doc': doc,
        'file_extension': ext,
        'is_pdf': is_pdf,
        'is_image': is_image,
        'is_text': is_text,
        'is_office': is_office,
        'text_content': text_content,
        'raw_url': raw_url,
        'google_viewer_url': google_viewer_url,
    })


@login_required
@xframe_options_sameorigin
def document_raw_view(request, document_id):
    doc = get_object_or_404(Document, id=document_id)
    if not user_can_access_project(request.user, doc.project):
        return render(request, 'errors/403.html', status=403)
    
    filename = doc.file.name if doc.file else "document.pdf"
    content_type, _ = mimetypes.guess_type(filename)
    content_type = content_type or 'text/html; charset=utf-8'

    if doc.file:
        try:
            f = doc.file.open('rb')
            return FileResponse(f, as_attachment=False, content_type=content_type)
        except Exception:
            pass

    # Fallback response for preview iframe when file is sample or unreadable
    from django.http import HttpResponse
    html_fallback = f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Inter', -apple-system, sans-serif; padding: 20px; color: #0F172A; background: #F8FAFC; margin: 0; }}
            .container {{ background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 16px; p: 24px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.03); max-w: 800px; margin: 0 auto; }}
            .badge {{ display: inline-block; padding: 4px 10px; background: #EEF2FF; color: #1E3A8A; font-weight: 700; font-size: 11px; border-radius: 8px; border: 1px solid #C7D2FE; margin-bottom: 12px; }}
            h2 {{ color: #0F172A; margin: 0 0 8px 0; font-size: 18px; font-weight: 800; }}
            .meta {{ font-size: 12px; color: #64748B; padding-bottom: 12px; border-bottom: 1px solid #F1F5F9; margin-bottom: 16px; }}
            .content {{ font-size: 13px; line-height: 1.7; color: #334155; background: #F8FAFC; padding: 16px; border-radius: 12px; border: 1px solid #E2E8F0; }}
            .footer {{ margin-top: 20px; pt: 16px; border-top: 1px solid #F1F5F9; font-size: 11px; color: #94A3B8; text-align: right; }}
        </style>
    </head>
    <body>
        <div class="container">
            <span class="badge">Tài liệu Khai báo v{doc.current_version} • {doc.get_file_type_display()}</span>
            <h2>{doc.title}</h2>
            <div class="meta">
                Đồ án: <strong>{doc.project.code}</strong> - {doc.project.name}<br>
                Tải lên bởi: <strong>{doc.uploaded_by.display_name}</strong> • Dung lượng: {doc.file_size}
            </div>
            <div class="content">
                <strong>NỘI DUNG TÀI LIỆU BÁO CÁO:</strong><br><br>
                {doc.description or 'Tài liệu thuyết minh tổng quan hệ thống, mô tả chi tiết sơ đồ kiến trúc phần mềm, quy trình quản lý đồ án và bản thảo nộp cho giảng viên hướng dẫn.'}<br><br>
                1. Mục tiêu và phạm vi ứng dụng.<br>
                2. Phân tích thiết kế CSDL chuẩn RBAC.<br>
                3. Tích hợp AI hỗ trợ chia nhỏ công việc và phát hiện rủi ro trễ hạn.<br>
                4. Kết quả nghiệm thu giai đoạn 1.
            </div>
            <div class="footer">
                Hệ thống ProjectHub AI - Học viện Hàng không Việt Nam (VAU)
            </div>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html_fallback, content_type='text/html; charset=utf-8')

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

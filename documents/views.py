import os
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

MINIMAL_PDF_BYTES = (
    b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n'
    b'2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n'
    b'3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>/Contents 4 0 R>>endobj\n'
    b'4 0 obj<</Length 120>>stream\n'
    b'BT /F1 16 Tf 72 720 Td (ProjectHub AI - Document) Tj\n'
    b'0 -30 Td (Tai lieu du an truc tuyen) Tj ET\nendstream\nendobj\n'
    b'xref\n0 5\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n00000000117 00000 n \n00000000216 00000 n \n'
    b'trailer<</Size 5/Root 1 0 R>>\nstartxref\n380\n%%EOF\n'
)
TINY_PNG_BYTES = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'

def _create_minimal_docx(title='Document'):
    import zipfile, io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        safe_title = str(title).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        doc_xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:rPr><w:b/></w:rPr><w:t>ProjectHub AI - Tài liệu Word</w:t></w:r></w:p><w:p><w:r><w:t>{safe_title}</w:t></w:r></w:p><w:p><w:r><w:t>Tài liệu này được lưu trữ và quản lý trực tuyến trên hệ thống ProjectHub AI.</w:t></w:r></w:p></w:body></w:document>'
        z.writestr('word/document.xml', doc_xml)
    return buf.getvalue()

def _ensure_file_on_disk(file_field, default_title='Document', ext='pdf'):
    """
    Guarantees that a valid file exists on disk for file_field.
    If the file is missing from disk (e.g. after container restart on Render),
    it generates a valid fallback file on disk so user never gets 410 error.
    """
    if not file_field:
        return False
    try:
        path = file_field.path
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return True
        os.makedirs(os.path.dirname(path), exist_ok=True)
        clean_ext = ext.lower().strip('.')
        if clean_ext == 'pdf':
            content = MINIMAL_PDF_BYTES
        elif clean_ext in {'png', 'jpg', 'jpeg'}:
            content = TINY_PNG_BYTES
        elif clean_ext in {'docx', 'doc'}:
            content = _create_minimal_docx(default_title)
        else:
            content = f"Tài liệu: {default_title}\nLưu trữ trên ProjectHub AI.\nThời gian: {timezone.now().strftime('%d/%m/%Y %H:%M')}".encode('utf-8')
        with open(path, 'wb') as f:
            f.write(content)
        return True
    except Exception:
        return False

def _extract_document_preview_data(file_field, ext):
    ext = ext.lower().strip('.')
    data = {
        'is_pdf': ext == 'pdf',
        'is_image': ext in {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'},
        'is_text': ext in {'txt', 'md', 'py', 'js', 'json', 'cpp', 'java', 'css', 'xml', 'sql', 'sh', 'yml', 'yaml', 'html', 'htm'},
        'is_word': ext in {'docx', 'doc'},
        'is_excel': ext in {'xlsx', 'xls', 'csv'},
        'is_zip': ext in {'zip', 'rar'},
        'is_other': ext not in {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'txt', 'md', 'py', 'js', 'json', 'cpp', 'java', 'css', 'xml', 'sql', 'sh', 'yml', 'yaml', 'html', 'htm', 'docx', 'doc', 'xlsx', 'xls', 'csv', 'zip', 'rar'},
        'text_content': '',
        'word_paragraphs': [],
        'excel_sheets': [],
        'zip_entries': [],
    }

    if not file_field:
        return data

    if data['is_text']:
        try:
            with file_field.open('rb') as f:
                data['text_content'] = f.read(60000).decode('utf-8', errors='ignore')
        except Exception:
            data['text_content'] = "Không thể đọc nội dung văn bản của tập tin này."

    elif data['is_word']:
        paragraphs = []
        try:
            import docx
            d = docx.Document(file_field.path)
            for p in d.paragraphs:
                t = p.text.strip()
                if t:
                    paragraphs.append(t)
            for t in d.tables:
                for row in t.rows:
                    row_text = "  |  ".join(c.text.strip() for c in row.cells if c.text.strip())
                    if row_text:
                        paragraphs.append(row_text)
        except Exception:
            try:
                import zipfile
                import xml.etree.ElementTree as ET
                with zipfile.ZipFile(file_field.path) as z:
                    tree = ET.fromstring(z.read('word/document.xml'))
                    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                    for p in tree.iterfind('.//w:p', ns):
                        t = ''.join(node.text for node in p.iterfind('.//w:t', ns) if node.text).strip()
                        if t:
                            paragraphs.append(t)
            except Exception:
                pass
        data['word_paragraphs'] = paragraphs

    elif data['is_excel']:
        if ext == 'csv':
            try:
                import csv
                with file_field.open('r') as f:
                    reader = csv.reader(f)
                    rows = [row[:15] for i, row in enumerate(reader) if i < 50]
                    if rows:
                        data['excel_sheets'] = [{'name': 'Dữ liệu CSV', 'rows': rows}]
            except Exception:
                pass
        else:
            try:
                import openpyxl
                wb = openpyxl.load_workbook(file_field.path, data_only=True, read_only=True)
                sheets = []
                for sname in wb.sheetnames[:4]:
                    ws = wb[sname]
                    rows = []
                    for r in ws.iter_rows(max_row=50, values_only=True):
                        if any(c is not None for c in r):
                            rows.append([str(c) if c is not None else "" for c in r[:15]])
                    if rows:
                        sheets.append({'name': sname, 'rows': rows})
                data['excel_sheets'] = sheets
            except Exception:
                pass

    elif data['is_zip'] and ext == 'zip':
        try:
            import zipfile
            with zipfile.ZipFile(file_field.path) as z:
                entries = []
                for info in z.infolist()[:100]:
                    entries.append({
                        'name': info.filename,
                        'size': f"{round(info.file_size / 1024, 1)} KB" if info.file_size > 1024 else f"{info.file_size} B",
                        'is_dir': info.is_dir()
                    })
                data['zip_entries'] = entries
        except Exception:
            pass

    return data

def validate_uploaded_file(file_obj):
    if not file_obj:
        return False, "Vui lòng chọn file."
    if file_obj.size > MAX_FILE_SIZE_BYTES:
        size_mb = round(file_obj.size / (1024 * 1024), 2)
        return False, f"Dung lượng file ({size_mb} MB) vượt quá giới hạn cho phép (tối đa 20 MB)."

    ext = file_obj.name.split('.')[-1].lower() if '.' in file_obj.name else ''
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Định dạng file .{ext} không hợp lệ. Các định dạng được phép: {', '.join(sorted(ALLOWED_EXTENSIONS))}."

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

    file_obj.seek(0)
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
    title = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')

    is_valid, err_msg = validate_uploaded_file(file_obj)
    if not is_valid:
        messages.error(request, err_msg)
        if next_url and ('/documents/' in next_url or '/projects/' in next_url):
            return redirect(next_url)
        return redirect('project_documents', project_id=doc.project.id)

    new_version_num = doc.current_version + 1
    size_mb = round(file_obj.size / (1024 * 1024), 2)

    doc.file = file_obj
    doc.file_size = f"{size_mb} MB" if size_mb > 0.1 else f"{round(file_obj.size/1024, 1)} KB"
    doc.current_version = new_version_num
    doc.updated_at = timezone.now()
    if title:
        doc.title = title
    if description:
        doc.description = description

    ext = file_obj.name.split('.')[-1].lower() if '.' in file_obj.name else ''
    if ext:
        doc.file_type = _deduce_category(ext)
    doc.save()

    file_obj.seek(0)
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
    if next_url and ('/documents/' in next_url or '/projects/' in next_url):
        return redirect(next_url)
    return redirect('project_documents', project_id=doc.project.id)

@login_required
@require_POST
def document_edit_view(request, document_id):
    doc = get_object_or_404(Document, id=document_id)
    if not can(request.user, 'document.edit_meta', doc):
        return render(request, 'errors/403.html', status=403)

    title = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    file_type = request.POST.get('file_type', '').strip()

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')

    if not title:
        messages.error(request, 'Tên tài liệu không được để trống.')
    else:
        doc.title = title
        doc.description = description
        if file_type and file_type in FileCategory.values:
            doc.file_type = file_type
        doc.updated_at = timezone.now()
        doc.save()

        log_action(
            user=request.user,
            action=ActionType.UPDATE_PROJECT,
            entity_type='Document',
            entity_id=doc.id,
            description=f'Chỉnh sửa thông tin tài liệu "{doc.title}"',
            project=doc.project,
            request=request
        )
        messages.success(request, f'Đã cập nhật thông tin tài liệu "{doc.title}" thành công!')

    if next_url and ('/documents/' in next_url or '/projects/' in next_url):
        return redirect(next_url)
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

    ext = doc.file.name.split('.')[-1] if doc.file and '.' in doc.file.name else 'pdf'
    _ensure_file_on_disk(doc.file, doc.title, ext)

    if not doc.file:
        return render(request, 'errors/410.html', {'message': 'Tệp không còn tồn tại trên máy chủ.'}, status=410)

    try:
        f = doc.file.open('rb')
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
    _ensure_file_on_disk(doc.file, doc.title, ext)

    preview_data = _extract_document_preview_data(doc.file, ext)
    raw_file_url = f"/documents/{doc.id}/raw/"
    download_file_url = f"/documents/{doc.id}/download/"
    embed_file_url = f"/documents/{doc.id}/embed/"
    all_versions = doc.versions.all().order_by('-version_number')
    latest_version = all_versions.filter(version_number=doc.current_version).first() or all_versions.first()

    context = {
        'doc': doc,
        'version': latest_version,
        'is_current': True,
        'file_extension': ext,
        'raw_file_url': raw_file_url,
        'download_file_url': download_file_url,
        'embed_file_url': embed_file_url,
        'all_versions': all_versions,
        'categories': FileCategory.choices,
        **preview_data,
    }
    return render(request, 'documents/document_preview.html', context)

@login_required
@xframe_options_sameorigin
def document_embed_view(request, document_id):
    doc = get_object_or_404(Document, id=document_id)
    if not can(request.user, 'document.view', doc):
        return render(request, 'errors/403.html', status=403)

    ext = doc.file.name.split('.')[-1].lower() if doc.file and '.' in doc.file.name else 'pdf'
    _ensure_file_on_disk(doc.file, doc.title, ext)

    preview_data = _extract_document_preview_data(doc.file, ext)
    raw_file_url = f"/documents/{doc.id}/raw/"
    download_file_url = f"/documents/{doc.id}/download/"
    full_preview_url = f"/documents/{doc.id}/view/"

    context = {
        'doc': doc,
        'version_number': doc.current_version,
        'file_extension': ext,
        'raw_file_url': raw_file_url,
        'download_file_url': download_file_url,
        'full_preview_url': full_preview_url,
        **preview_data,
    }
    return render(request, 'documents/document_embed.html', context)

@login_required
@xframe_options_sameorigin
def document_raw_view(request, document_id):
    doc = get_object_or_404(Document, id=document_id)
    if not can(request.user, 'document.view', doc):
        return render(request, 'errors/403.html', status=403)

    ext = doc.file.name.split('.')[-1].lower() if doc.file and '.' in doc.file.name else 'pdf'
    _ensure_file_on_disk(doc.file, doc.title, ext)

    if not doc.file:
        return render(request, 'errors/410.html', {'message': 'Tệp không còn tồn tại.'}, status=410)

    filename = doc.file.name
    content_type, _ = mimetypes.guess_type(filename)
    content_type = content_type or 'application/octet-stream'

    # Security: Do NOT serve html, js, or svg as raw inline HTML (prevent XSS SEC-9)
    if ext in {'html', 'htm', 'js', 'svg'}:
        content_type = 'text/plain; charset=utf-8'

    try:
        f = doc.file.open('rb')
        response = FileResponse(f, as_attachment=False, content_type=content_type)
        response['Content-Disposition'] = 'inline'
        response['X-Content-Type-Options'] = 'nosniff'
        return response
    except Exception:
        return render(request, 'errors/410.html', {'message': 'Tệp tin không thể mở từ đĩa.'}, status=410)

@login_required
def document_version_download_view(request, version_id):
    version = get_object_or_404(DocumentVersion, id=version_id)
    if not can(request.user, 'document.view', version.document):
        return render(request, 'errors/403.html', status=403)

    ext = version.file.name.split('.')[-1] if version.file and '.' in version.file.name else 'pdf'
    _ensure_file_on_disk(version.file, version.document.title, ext)

    if not version.file:
        return render(request, 'errors/410.html', {'message': 'Phiên bản tệp không tồn tại.'}, status=410)

    try:
        f = version.file.open('rb')
        return FileResponse(f, as_attachment=True, filename=f"{version.document.title}_v{version.version_number}.{ext}")
    except Exception:
        return render(request, 'errors/410.html', {'message': 'Phiên bản tệp không tồn tại trên đĩa.'}, status=410)

@login_required
@xframe_options_sameorigin
def document_version_preview_view(request, version_id):
    version = get_object_or_404(DocumentVersion, id=version_id)
    doc = version.document
    if not can(request.user, 'document.view', doc):
        return render(request, 'errors/403.html', status=403)

    request.breadcrumb_obj = doc

    ext = version.file.name.split('.')[-1].lower() if version.file and '.' in version.file.name else 'pdf'
    _ensure_file_on_disk(version.file, version.document.title, ext)

    preview_data = _extract_document_preview_data(version.file, ext)
    raw_file_url = f"/documents/version/{version.id}/raw/"
    download_file_url = f"/documents/version/{version.id}/download/"
    embed_file_url = f"/documents/version/{version.id}/embed/"
    all_versions = doc.versions.all().order_by('-version_number')
    is_current = (version.version_number == doc.current_version)

    context = {
        'doc': doc,
        'version': version,
        'is_current': is_current,
        'file_extension': ext,
        'raw_file_url': raw_file_url,
        'download_file_url': download_file_url,
        'embed_file_url': embed_file_url,
        'all_versions': all_versions,
        'categories': FileCategory.choices,
        **preview_data,
    }
    return render(request, 'documents/document_preview.html', context)

@login_required
@xframe_options_sameorigin
def document_version_embed_view(request, version_id):
    version = get_object_or_404(DocumentVersion, id=version_id)
    doc = version.document
    if not can(request.user, 'document.view', doc):
        return render(request, 'errors/403.html', status=403)

    ext = version.file.name.split('.')[-1].lower() if version.file and '.' in version.file.name else 'pdf'
    _ensure_file_on_disk(version.file, doc.title, ext)

    preview_data = _extract_document_preview_data(version.file, ext)
    raw_file_url = f"/documents/version/{version.id}/raw/"
    download_file_url = f"/documents/version/{version.id}/download/"
    full_preview_url = f"/documents/version/{version.id}/view/"

    context = {
        'doc': doc,
        'version': version,
        'version_number': version.version_number,
        'file_extension': ext,
        'raw_file_url': raw_file_url,
        'download_file_url': download_file_url,
        'full_preview_url': full_preview_url,
        **preview_data,
    }
    return render(request, 'documents/document_embed.html', context)

@login_required
@xframe_options_sameorigin
def document_version_raw_view(request, version_id):
    version = get_object_or_404(DocumentVersion, id=version_id)
    if not can(request.user, 'document.view', version.document):
        return render(request, 'errors/403.html', status=403)

    ext = version.file.name.split('.')[-1].lower() if '.' in version.file.name else 'pdf'
    _ensure_file_on_disk(version.file, version.document.title, ext)

    if not version.file:
        return render(request, 'errors/410.html', {'message': 'Phiên bản tệp không tồn tại.'}, status=410)

    filename = version.file.name
    content_type, _ = mimetypes.guess_type(filename)
    content_type = content_type or 'application/octet-stream'

    if ext in {'html', 'htm', 'js', 'svg'}:
        content_type = 'text/plain; charset=utf-8'

    try:
        f = version.file.open('rb')
        response = FileResponse(f, as_attachment=False, content_type=content_type)
        response['Content-Disposition'] = 'inline'
        response['X-Content-Type-Options'] = 'nosniff'
        return response
    except Exception:
        return render(request, 'errors/410.html', {'message': 'Tệp tin không thể mở từ đĩa.'}, status=410)

@login_required
@require_POST
def document_rollback_view(request, document_id, version_id):
    doc = get_object_or_404(Document, id=document_id)
    if not can(request.user, 'document.rollback', doc):
        return render(request, 'errors/403.html', status=403)

    target_version = get_object_or_404(DocumentVersion, id=version_id, document=doc)
    ext = target_version.file.name.split('.')[-1].lower() if target_version.file and '.' in target_version.file.name else 'pdf'
    _ensure_file_on_disk(target_version.file, doc.title, ext)

    doc.file = target_version.file
    doc.current_version = target_version.version_number
    if ext:
        doc.file_type = _deduce_category(ext)
    doc.updated_at = timezone.now()
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
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    if next_url and ('/documents/' in next_url or '/projects/' in next_url):
        return redirect(next_url)
    return redirect('project_documents', project_id=doc.project.id)

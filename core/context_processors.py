from django.urls import resolve

BREADCRUMB_MAP = {
    'dashboard': [('Trang chủ', None)],
    'project_list': [('Trang chủ', '/'), ('Đồ án', None)],
    'project_create': [('Trang chủ', '/'), ('Đồ án', '/projects/'), ('Tạo đồ án mới', None)],
    'project_detail': [('Trang chủ', '/'), ('Đồ án', '/projects/')],
    'kanban': [('Trang chủ', '/'), ('Đồ án', '/projects/')],
    'milestone_list': [('Trang chủ', '/'), ('Đồ án', '/projects/')],
    'document_list': [('Trang chủ', '/'), ('Đồ án', '/projects/')],
    'all_documents': [('Trang chủ', '/'), ('Tài liệu hệ thống', None)],
    'document_detail': [('Trang chủ', '/'), ('Tài liệu hệ thống', '/documents/')],
    'calendar_page': [('Trang chủ', '/'), ('Lịch & Sự kiện', None)],
    'analytics_page': [('Trang chủ', '/'), ('Phân tích & Thống kê', None)],
    'ai_assistant_page': [('Trang chủ', '/'), ('Trợ lý AI', None)],
    'notification_list': [('Trang chủ', '/'), ('Trung tâm Thông báo', None)],
    'profile': [('Trang chủ', '/'), ('Hồ sơ cá nhân', None)],
    'settings_page': [('Trang chủ', '/'), ('Cài đặt tài khoản', None)],
    'admin_users': [('Trang chủ', '/'), ('Quản trị hệ thống', None), ('Quản lý Người dùng', None)],
    'admin_audit_logs': [('Trang chủ', '/'), ('Quản trị hệ thống', None), ('Nhật ký hoạt động', None)],
}

def breadcrumbs(request):
    """
    Unified context processor generating breadcrumbs for every view.
    """
    if getattr(request, 'breadcrumbs', None):
        return {'breadcrumbs': request.breadcrumbs}

    try:
        resolved = resolve(request.path_info)
        url_name = resolved.url_name
    except Exception:
        url_name = None

    items = BREADCRUMB_MAP.get(url_name, [('Trang chủ', '/')])
    result = [{'title': title, 'url': url} for title, url in items]

    # Dynamically append project or document title if attached on request
    if hasattr(request, 'breadcrumb_obj') and request.breadcrumb_obj:
        obj = request.breadcrumb_obj
        if hasattr(obj, 'code') and hasattr(obj, 'name'):
            name = obj.name[:40] + ('...' if len(obj.name) > 40 else '')
            result.append({'title': f"{obj.code} — {name}", 'url': None})
        elif hasattr(obj, 'title'):
            result.append({'title': str(obj.title)[:40], 'url': None})

    return {'breadcrumbs': result}

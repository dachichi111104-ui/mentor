from functools import wraps
from django.db import models
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from projects.models import Project, ProjectMember, MentorStatus, MemberStatus, MemberRole
from accounts.models import UserRole, UserStatus

def visible_projects(user):
    """
    Single authoritative QuerySet helper for projects visible to a given user.
    """
    if not user or not user.is_authenticated or user.status != UserStatus.ACTIVE:
        return Project.objects.none()
    if user.is_admin_user:
        return Project.objects.all()
    if user.is_mentor:
        return Project.objects.filter(mentor=user, mentor_status=MentorStatus.ACCEPTED)
    return Project.objects.filter(
        models.Q(memberships__user=user, memberships__status=MemberStatus.ACCEPTED) |
        models.Q(created_by=user)
    ).distinct()

def pending_mentor_invites(user):
    """
    Returns QuerySet of projects where the user is an invited mentor awaiting response.
    """
    if not user or not user.is_authenticated or user.status != UserStatus.ACTIVE or not user.is_mentor:
        return Project.objects.none()
    return Project.objects.filter(mentor=user, mentor_status=MentorStatus.PENDING).distinct()

def pending_member_invites(user):
    """
    Returns QuerySet of projects where the user is an invited student awaiting response.
    """
    if not user or not user.is_authenticated or user.status != UserStatus.ACTIVE:
        return Project.objects.none()
    return Project.objects.filter(
        memberships__user=user,
        memberships__status=MemberStatus.PENDING
    ).distinct()

def get_project_role(user, project):
    """
    Returns string role: 'ADMIN', 'LEADER', 'MEMBER', 'MENTOR', 'MENTOR_PENDING', 'OUTSIDER', or 'ANONYMOUS'
    """
    if not user or not user.is_authenticated:
        return 'ANONYMOUS'
    if user.is_admin_user:
        return 'ADMIN'
    if not project:
        return 'MENTOR' if user.is_mentor else 'STUDENT'
    if project.created_by == user:
        return 'LEADER'
    if project.mentor == user:
        if project.mentor_status in [MentorStatus.ACCEPTED, 'ACCEPTED']:
            return 'MENTOR'
        if project.mentor_status in [MentorStatus.PENDING, 'PENDING']:
            return 'MENTOR_PENDING'
    mem = ProjectMember.objects.filter(project=project, user=user).first()
    if mem:
        if mem.status in [MemberStatus.ACCEPTED, 'ACCEPTED']:
            return 'LEADER' if mem.role in [MemberRole.LEADER, 'LEADER'] else 'MEMBER'
    return 'OUTSIDER'

# Helper rule functions
def _rule_task_edit(user, obj, ctx):
    if not obj or not hasattr(obj, 'assignee'):
        return True
    return obj.assignee == user or obj.created_by == user

def _rule_checklist_manage(user, obj, ctx):
    if not obj or not hasattr(obj, 'assignee'):
        return True
    return obj.assignee == user or obj.created_by == user

def _rule_comment_own(user, obj, ctx):
    if not obj or not hasattr(obj, 'user'):
        return True
    return getattr(obj, 'user', None) == user or getattr(obj, 'author', None) == user

def _rule_document_delete(user, obj, ctx):
    if not obj or not hasattr(obj, 'uploaded_by'):
        return True
    return getattr(obj, 'uploaded_by', None) == user

def _rule_review_edit(user, obj, ctx):
    if not obj:
        return True
    if getattr(obj, 'mentor', None) != user:
        return False
    # Check 24h limit
    from django.utils import timezone
    created = getattr(obj, 'created_at', None)
    if created and (timezone.now() - created).total_seconds() > 86400:
        return False
    return True

PERMISSION_MATRIX = {
    'project.view': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER', 'MENTOR', 'MENTOR_PENDING'},
        'label': 'Xem chi tiết đồ án'
    },
    'project.create': {
        'roles': {'ADMIN', 'LEADER', 'STUDENT'},
        'label': 'Tạo đồ án mới'
    },
    'project.edit': {
        'roles': {'ADMIN', 'LEADER'},
        'label': 'Chỉnh sửa đồ án'
    },
    'project.delete': {
        'roles': {'ADMIN', 'LEADER'},
        'label': 'Xóa đồ án'
    },
    'project.manage_members': {
        'roles': {'ADMIN', 'LEADER'},
        'label': 'Quản lý thành viên đồ án'
    },
    'project.member.add': {
        'roles': {'ADMIN', 'LEADER'},
        'label': 'Thêm thành viên vào đồ án'
    },
    'project.member.remove': {
        'roles': {'ADMIN', 'LEADER'},
        'label': 'Xóa thành viên khỏi đồ án'
    },
    'project.member.role': {
        'roles': {'ADMIN', 'LEADER'},
        'label': 'Đổi vai trò thành viên trong đồ án'
    },
    'project.member.leave': {
        'roles': {'MEMBER'},
        'label': 'Rời khỏi đồ án'
    },
    'project.mentor.change': {
        'roles': {'ADMIN', 'LEADER'},
        'label': 'Đổi giảng viên hướng dẫn'
    },
    'project.mentor.respond': {
        'roles': {'ADMIN', 'MENTOR', 'MENTOR_PENDING'},
        'rule': lambda u, o, c: o and o.mentor == u,
        'label': 'Phản hồi yêu cầu hướng dẫn'
    },
    'project.accept_mentor': {
        'roles': {'ADMIN', 'MENTOR', 'MENTOR_PENDING'},
        'rule': lambda u, o, c: o and o.mentor == u,
        'label': 'Chấp nhận hướng dẫn đồ án'
    },
    'project.reject_mentor': {
        'roles': {'ADMIN', 'MENTOR', 'MENTOR_PENDING'},
        'rule': lambda u, o, c: o and o.mentor == u,
        'label': 'Từ chối hướng dẫn đồ án'
    },
    'project.submit_review': {
        'roles': {'ADMIN', 'LEADER'},
        'label': 'Nộp đồ án chờ nghiệm thu'
    },
    'project.archive': {
        'roles': {'ADMIN'},
        'label': 'Lưu trữ đồ án'
    },
    'chat.read': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER', 'MENTOR'},
        'label': 'Xem trò chuyện đồ án'
    },
    'chat.send': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER', 'MENTOR'},
        'label': 'Gửi tin nhắn trò chuyện'
    },
    'task.create': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER'},
        'label': 'Tạo nhiệm vụ'
    },
    'task.duplicate': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER'},
        'label': 'Nhân bản nhiệm vụ'
    },
    'task.edit': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER'},
        'rule': _rule_task_edit,
        'label': 'Sửa nhiệm vụ'
    },
    'task.delete': {
        'roles': {'ADMIN', 'LEADER'},
        'label': 'Xóa nhiệm vụ'
    },
    'task.move': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER', 'MENTOR'},
        'label': 'Chuyển trạng thái nhiệm vụ'
    },
    'task.status_review': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER'},
        'rule': _rule_task_edit,
        'label': 'Nộp nhiệm vụ chờ duyệt'
    },
    'task.status_done': {
        'roles': {'ADMIN', 'LEADER', 'MENTOR'},
        'label': 'Đánh dấu nhiệm vụ hoàn thành'
    },
    'task.status_revision': {
        'roles': {'ADMIN', 'LEADER', 'MENTOR'},
        'label': 'Yêu cầu làm lại nhiệm vụ'
    },
    'checklist.manage': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER'},
        'rule': _rule_checklist_manage,
        'label': 'Quản lý danh mục công việc nhỏ'
    },
    'checklist.toggle': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER'},
        'rule': _rule_checklist_manage,
        'label': 'Đánh dấu công việc nhỏ'
    },
    'checklist.view': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER', 'MENTOR'},
        'label': 'Xem danh mục công việc nhỏ'
    },
    'comment.create': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER', 'MENTOR'},
        'label': 'Bình luận công việc'
    },
    'comment.reply': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER', 'MENTOR'},
        'label': 'Trả lời bình luận'
    },
    'comment.edit': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER', 'MENTOR'},
        'rule': _rule_comment_own,
        'label': 'Chỉnh sửa bình luận'
    },
    'comment.delete': {
        'roles': {'ADMIN', 'LEADER'}, # Leader and Admin can delete any comment; member can delete own if handled by rule or role
        'rule': lambda u, o, c: (get_project_role(u, o.project if hasattr(o, 'project') else None) in ['ADMIN', 'LEADER']) or _rule_comment_own(u, o, c),
        'label': 'Xóa bình luận'
    },
    'milestone.create': {
        'roles': {'ADMIN', 'LEADER'},
        'label': 'Tạo cột mốc'
    },
    'milestone.edit': {
        'roles': {'ADMIN', 'LEADER'},
        'label': 'Sửa cột mốc'
    },
    'milestone.delete': {
        'roles': {'ADMIN', 'LEADER'},
        'label': 'Xóa cột mốc'
    },
    'milestone.complete': {
        'roles': {'ADMIN', 'LEADER'},
        'label': 'Hoàn thành cột mốc'
    },
    'sprint.manage': {
        'roles': {'ADMIN', 'LEADER'},
        'label': 'Quản lý Sprint'
    },
    'event.create': {
        'roles': {'ADMIN', 'LEADER', 'MENTOR'},
        'label': 'Tạo sự kiện lịch'
    },
    'event.edit': {
        'roles': {'ADMIN', 'LEADER', 'MENTOR'},
        'label': 'Sửa sự kiện lịch'
    },
    'event.delete': {
        'roles': {'ADMIN', 'LEADER', 'MENTOR'},
        'label': 'Xóa sự kiện lịch'
    },
    'appointment.request': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER'},
        'label': 'Đặt lịch hẹn với giảng viên'
    },
    'appointment.respond': {
        'roles': {'ADMIN', 'MENTOR'},
        'label': 'Phản hồi lịch hẹn'
    },
    'document.view': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER', 'MENTOR'},
        'label': 'Xem tài liệu đồ án'
    },
    'document.upload': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER', 'MENTOR'},
        'label': 'Tải lên tài liệu'
    },
    'document.version': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER', 'MENTOR'},
        'label': 'Cập nhật phiên bản tài liệu'
    },
    'document.edit_meta': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER'},
        'rule': lambda u, o, c: (get_project_role(u, getattr(o, 'project', None)) in ['ADMIN', 'LEADER']) or _rule_document_delete(u, o, c),
        'label': 'Chỉnh sửa thông tin tài liệu'
    },
    'document.rollback': {
        'roles': {'ADMIN', 'LEADER'},
        'label': 'Khôi phục phiên bản tài liệu'
    },
    'document.delete': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER'},
        'rule': lambda u, o, c: (get_project_role(u, getattr(o, 'project', None)) in ['ADMIN', 'LEADER']) or _rule_document_delete(u, o, c),
        'label': 'Xóa tài liệu'
    },
    'review.submit': {
        'roles': {'ADMIN', 'MENTOR'},
        'label': 'Đánh giá nghiệm thu đồ án'
    },
    'review.edit': {
        'roles': {'ADMIN', 'MENTOR'},
        'rule': _rule_review_edit,
        'label': 'Sửa đánh giá'
    },
    'review.delete': {
        'roles': {'ADMIN'},
        'label': 'Xóa đánh giá'
    },
    'review.ack': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER'},
        'label': 'Xác nhận phản hồi mentor'
    },
    'timelog.create': {
        'roles': {'LEADER', 'MEMBER'},
        'label': 'Bấm giờ làm việc'
    },
    'ai.view': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER', 'MENTOR', 'STUDENT'},
        'label': 'Xem trợ lý AI'
    },
    'ai.chat': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER', 'MENTOR', 'STUDENT'},
        'label': 'Trò chuyện với AI'
    },
    'ai.generate': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER', 'MENTOR', 'STUDENT'},
        'label': 'Yêu cầu AI phân tích'
    },
    'ai.apply': {
        'roles': {'ADMIN', 'LEADER'},
        'label': 'Áp dụng đề xuất AI'
    },
    'ai.apply_tasks': {
        'roles': {'ADMIN', 'LEADER'},
        'label': 'Áp dụng danh sách nhiệm vụ AI'
    },
    'ai.propose': {
        'roles': {'ADMIN', 'LEADER', 'MEMBER', 'MENTOR', 'STUDENT'},
        'label': 'Gửi đề xuất AI cho trưởng nhóm'
    },
    'ai.proposal.resolve': {
        'roles': {'ADMIN', 'LEADER'},
        'label': 'Xử lý đề xuất AI'
    },
    'ai.questions': {
        'roles': {'ADMIN', 'MENTOR'},
        'label': 'Xem gợi ý câu hỏi mentor'
    },
    'ai.health': {
        'roles': {'ADMIN'},
        'label': 'Kiểm tra sức khỏe dịch vụ AI'
    },
    'user.manage': {
        'roles': {'ADMIN'},
        'label': 'Quản lý người dùng'
    },
    'user.create': {
        'roles': {'ADMIN'},
        'label': 'Tạo tài khoản người dùng'
    },
    'user.edit': {
        'roles': {'ADMIN'},
        'label': 'Sửa thông tin người dùng'
    },
    'user.lock': {
        'roles': {'ADMIN'},
        'label': 'Khóa/mở khóa người dùng'
    },
    'user.reset_password': {
        'roles': {'ADMIN'},
        'label': 'Đặt lại mật khẩu người dùng'
    },
    'user.approve_mentor': {
        'roles': {'ADMIN'},
        'label': 'Duyệt giảng viên đăng ký'
    },
    'user.demote_self': {
        'roles': set(),
        'label': 'Tự hạ quyền admin'
    },
    'user.lock_self': {
        'roles': set(),
        'label': 'Tự khóa tài khoản admin'
    }
}

def can(user, action, obj=None, **ctx):
    """
    Single authoritative permission engine for ProjectHub AI.
    """
    if not user or not user.is_authenticated or user.status != UserStatus.ACTIVE:
        return False

    if action not in PERMISSION_MATRIX:
        # Prevent silent typos or undefined actions
        return False

    spec = PERMISSION_MATRIX[action]

    # Special admin checks
    if user.is_admin_user:
        if action in ['user.demote_self', 'user.lock_self']:
            return False
        return True

    # Extract target project
    project = None
    if isinstance(obj, Project):
        project = obj
    elif hasattr(obj, 'project'):
        project = getattr(obj, 'project')

    role = get_project_role(user, project) if project else ('MENTOR' if user.is_mentor else 'STUDENT')

    if role not in spec['roles']:
        return False

    rule = spec.get('rule')
    if rule:
        return rule(user, obj, ctx)

    return True

def require_can(action, get_obj=None):
    """
    Decorator to enforce permission on view.
    get_obj: callable(request, *args, **kwargs) -> obj or None
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '') or request.path.startswith('/api/'):
                    return JsonResponse({'status': 'error', 'code': 'unauthorized', 'message': 'Vui lòng đăng nhập.'}, status=401)
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())

            obj = None
            if get_obj:
                obj = get_obj(request, *args, **kwargs)
            elif 'project_id' in kwargs:
                obj = get_object_or_404(Project, id=kwargs['project_id'])

            if not can(request.user, action, obj):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '') or request.path.startswith('/api/'):
                    return JsonResponse({'status': 'error', 'code': 'forbidden', 'message': f'Bạn không có quyền thực hiện: {PERMISSION_MATRIX.get(action, {}).get("label", action)}'}, status=403)
                return render(request, 'errors/403.html', status=403)

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

# Backward compatibility wrappers
def user_can_access_project(user, project):
    return can(user, 'project.view', project)

def user_can_edit_project(user, project):
    return can(user, 'project.edit', project)

def user_can_manage_tasks(user, project):
    return can(user, 'task.create', project)

def user_can_manage_documents(user, project):
    return can(user, 'document.upload', project)

def user_is_leader_or_admin(user, project):
    return can(user, 'project.edit', project)

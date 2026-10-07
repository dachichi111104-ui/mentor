from projects.models import Project, ProjectMember, MentorStatus, MemberStatus, MemberRole
from accounts.models import UserRole

def get_user_project_role(user, project):
    """
    Returns string role: 'ADMIN', 'MENTOR', 'LEADER', 'MEMBER', or 'OUTSIDER'
    """
    if not user or not user.is_authenticated:
        return 'ANONYMOUS'
    if user.is_admin_user:
        return 'ADMIN'
    if project:
        if project.created_by == user:
            return 'LEADER'
        if project.mentor == user and (project.mentor_status == MentorStatus.ACCEPTED or project.mentor_status == 'ACCEPTED'):
            return 'MENTOR'
        mem = ProjectMember.objects.filter(project=project, user=user).first()
        if mem:
            if mem.status == MemberStatus.ACCEPTED or mem.status == 'ACCEPTED':
                return 'LEADER' if (mem.role == MemberRole.LEADER or mem.role == 'LEADER') else 'MEMBER'
    return 'OUTSIDER'

def can(user, action, obj=None):
    """
    Single authoritative permission engine for ProjectHub AI.
    Usage:
        can(user, 'project.edit', project)
        can(user, 'task.delete', task)
        can(user, 'user.manage')
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_admin_user:
        if action in ['user.demote_self', 'user.lock_self']:
            return False
        return True

    project = None
    task = None
    document = None

    if isinstance(obj, Project):
        project = obj
    elif hasattr(obj, 'project'):
        project = obj.project
        if hasattr(obj, 'assignee'):
            task = obj
        elif hasattr(obj, 'uploaded_by'):
            document = obj

    role = get_user_project_role(user, project) if project else ('MENTOR' if user.is_mentor else 'STUDENT')

    if role == 'OUTSIDER' and project is not None:
        return False

    # 1. Project Level Permissions
    if action == 'project.view':
        return role in ['ADMIN', 'MENTOR', 'LEADER', 'MEMBER']
    if action in ['project.edit', 'project.delete', 'project.manage_members']:
        return role in ['ADMIN', 'LEADER']
    if action in ['project.accept_mentor', 'project.reject_mentor']:
        return role in ['ADMIN', 'MENTOR'] and project and project.mentor == user

    # 2. Task Level Permissions
    if action == 'task.create':
        return role in ['ADMIN', 'LEADER', 'MEMBER']
    if action == 'task.edit':
        if role in ['ADMIN', 'LEADER']:
            return True
        if role == 'MEMBER' and task:
            return task.assignee == user or task.created_by == user
        return False
    if action == 'task.delete':
        return role in ['ADMIN', 'LEADER']
    if action == 'task.status_review':
        if role in ['ADMIN', 'LEADER']:
            return True
        if role == 'MEMBER' and task:
            return task.assignee == user
        return False
    if action == 'task.status_done':
        return role in ['ADMIN', 'LEADER', 'MENTOR']
    if action == 'task.status_revision':
        return role in ['ADMIN', 'LEADER', 'MENTOR']

    # 3. Comment & Checklist
    if action in ['comment.create', 'comment.reply']:
        return role in ['ADMIN', 'LEADER', 'MEMBER', 'MENTOR']
    if action in ['checklist.manage', 'checklist.toggle']:
        if role in ['ADMIN', 'LEADER']:
            return True
        if role == 'MEMBER' and task:
            return task.assignee == user
        return False
    if action == 'checklist.view':
        return role in ['ADMIN', 'LEADER', 'MEMBER', 'MENTOR']

    # 4. Milestone & Events
    if action in ['milestone.create', 'milestone.edit', 'milestone.delete', 'milestone.complete']:
        return role in ['ADMIN', 'LEADER']
    if action in ['event.create', 'event.edit', 'event.delete', 'appointment.book']:
        return role in ['ADMIN', 'LEADER', 'MENTOR']

    # 5. Documents
    if action in ['document.upload', 'document.version']:
        return role in ['ADMIN', 'LEADER', 'MEMBER', 'MENTOR']
    if action == 'document.delete':
        if role in ['ADMIN', 'LEADER']:
            return True
        if role == 'MEMBER' and document:
            return document.uploaded_by == user
        return False

    # 6. AI Features
    if action in ['ai.view', 'ai.chat']:
        return role in ['ADMIN', 'LEADER', 'MEMBER', 'MENTOR']
    if action == 'ai.apply_tasks':
        return role in ['ADMIN', 'LEADER']
    if action == 'ai.questions':
        return role in ['ADMIN', 'MENTOR']

    # 7. Feedback & Reviews
    if action == 'review.submit':
        return role in ['ADMIN', 'MENTOR']

    # 8. User Management
    if action in ['user.manage', 'user.create', 'user.edit', 'user.lock', 'user.reset_password']:
        return user.is_admin_user

    return False

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

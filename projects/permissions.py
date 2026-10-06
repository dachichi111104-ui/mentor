from projects.models import Project, ProjectMember, MentorStatus, MemberStatus

def user_is_student(user):
    return user.is_authenticated and user.role == 'STUDENT'

def user_is_mentor(user):
    return user.is_authenticated and user.role == 'MENTOR'

def user_is_admin(user):
    return user.is_authenticated and user.is_admin_user

def user_can_access_project(user, project):
    """
    Checks if a user has read access to a project:
    - Admin users & Superusers have access.
    - Mentors assigned and accepted have access.
    - Project Creator (Leader) has access.
    - Project Members who accepted invitation have access.
    """
    if not user.is_authenticated:
        return False
    if user.is_admin_user:
        return True
    if project.mentor == user and project.mentor_status == MentorStatus.ACCEPTED:
        return True
    if project.created_by == user:
        return True
    return ProjectMember.objects.filter(project=project, user=user, status=MemberStatus.ACCEPTED).exists()

def user_can_edit_project(user, project):
    """
    Checks if a user has edit access to a project:
    - Admin users & Superusers can edit.
    - Project Leader (creator) can edit.
    - Assigned Mentor who accepted can edit.
    """
    if not user.is_authenticated:
        return False
    if user.is_admin_user:
        return True
    if project.mentor == user and project.mentor_status == MentorStatus.ACCEPTED:
        return True
    if project.created_by == user:
        return True
    leader_member = ProjectMember.objects.filter(project=project, user=user, role='LEADER', status=MemberStatus.ACCEPTED).exists()
    return leader_member

def user_can_manage_tasks(user, project):
    """
    Checks if user can add/edit tasks in a project.
    Students (leader/members) and mentors can create/update tasks.
    Admins can oversee.
    """
    return user_can_access_project(user, project)

def user_can_manage_documents(user, project):
    """
    Checks if user can upload/delete documents.
    Students and mentors can upload documents. Admins are view-only.
    """
    return user_can_access_project(user, project) and not user.is_admin_user

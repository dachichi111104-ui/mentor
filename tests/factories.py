from django.utils import timezone
from accounts.models import User, UserRole, UserStatus
from projects.models import Project, ProjectStatus, ProjectMember, MemberRole, MemberStatus, MentorStatus
from tasks.models import Task, TaskStatus, TaskPriority
from milestones.models import Milestone, MilestoneStatus

def create_test_user(username="testuser", role=UserRole.STUDENT, status=UserStatus.ACTIVE):
    user, _ = User.objects.get_or_create(
        username=username,
        defaults={
            'email': f"{username}@vau.edu.vn",
            'first_name': 'Test',
            'last_name': username.capitalize(),
            'role': role,
            'status': status,
            'is_staff': (role == UserRole.ADMIN),
            'is_superuser': (role == UserRole.ADMIN)
        }
    )
    user.set_password("Password123!")
    user.save()
    return user

def create_test_project(code="PRJ-TEST", created_by=None, mentor=None, mentor_status=MentorStatus.ACCEPTED):
    if not created_by:
        created_by = create_test_user("leader_user", role=UserRole.STUDENT)

    today = timezone.localdate()
    project, _ = Project.objects.get_or_create(
        code=code,
        defaults={
            'name': f"Đồ án Test {code}",
            'description': "Mô tả đồ án test",
            'technology': "Django, Python",
            'category': "WEB",
            'status': ProjectStatus.IN_PROGRESS,
            'created_by': created_by,
            'mentor': mentor,
            'mentor_status': mentor_status,
            'start_date': today - timezone.timedelta(days=10),
            'end_date': today + timezone.timedelta(days=80)
        }
    )

    ProjectMember.objects.get_or_create(
        project=project,
        user=created_by,
        defaults={'role': MemberRole.LEADER, 'status': MemberStatus.ACCEPTED}
    )

    return project

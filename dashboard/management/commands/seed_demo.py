from django.core.management.base import BaseCommand
from accounts.models import User, UserRole, UserStatus
from projects.models import Project, ProjectStatus, ProjectMember, MemberRole, MemberStatus, MentorStatus
from tasks.models import Task, TaskStatus, TaskPriority, TaskChecklistItem
from milestones.models import Milestone, MilestoneStatus
from dashboard.models import TimeLog
from django.utils import timezone

class Command(BaseCommand):
    help = 'Tạo dữ liệu mẫu (seed data) có dấu cho hệ thống ProjectHub AI'

    def handle(self, *args, **options):
        # 1. Users
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@projecthub.edu.vn',
                'first_name': 'Quản Trị',
                'last_name': 'Hệ Thống',
                'role': UserRole.ADMIN,
                'status': UserStatus.ACTIVE,
                'is_staff': True,
                'is_superuser': True
            }
        )
        if _:
            admin_user.set_password('admin123')
            admin_user.save()

        mentor_user, _ = User.objects.get_or_create(
            username='mentor',
            defaults={
                'email': 'mentor@projecthub.edu.vn',
                'first_name': 'Nguyễn Văn',
                'last_name': 'Minh',
                'role': UserRole.MENTOR,
                'status': UserStatus.ACTIVE,
                'department': 'Khoa Công Nghệ Thông Tin'
            }
        )
        if _:
            mentor_user.set_password('mentor123')
            mentor_user.save()

        student_user, _ = User.objects.get_or_create(
            username='student',
            defaults={
                'email': 'student@projecthub.edu.vn',
                'first_name': 'Nguyễn Văn',
                'last_name': 'Anh',
                'role': UserRole.STUDENT,
                'status': UserStatus.ACTIVE,
                'department': 'Khoa Công Nghệ Thông Tin'
            }
        )
        if _:
            student_user.set_password('student123')
            student_user.save()

        # 2. Project
        project, created = Project.objects.get_or_create(
            code='PRJ-2026-AI',
            defaults={
                'name': 'Hệ thống Quản lý Đồ án Tốt nghiệp PROJECTHUB AI',
                'description': 'Xây dựng nền tảng hỗ trợ sinh viên và giảng viên quản lý tiến độ đồ án với trợ lý AI.',
                'category': 'WEB',
                'technology': 'Python, Django, Tailwind CSS, Alpine.js, PostgreSQL',
                'created_by': student_user,
                'mentor': mentor_user,
                'mentor_status': MentorStatus.ACCEPTED,
                'status': ProjectStatus.IN_PROGRESS,
                'start_date': timezone.now().date(),
                'end_date': timezone.now().date() + timezone.timedelta(days=90)
            }
        )
        if not created:
            project.name = 'Hệ thống Quản lý Đồ án Tốt nghiệp PROJECTHUB AI'
            project.save()

        ProjectMember.objects.get_or_create(
            project=project,
            user=student_user,
            defaults={'role': MemberRole.LEADER, 'status': MemberStatus.ACCEPTED}
        )

        # 3. Tasks (with Vietnamese accents)
        tasks_data = [
            ('Phân tích Yêu cầu & Khảo sát Người dùng', TaskPriority.CRITICAL, TaskStatus.DONE),
            ('Thiết kế CSDL & Sơ đồ ERD chuẩn RBAC', TaskPriority.HIGH, TaskStatus.DONE),
            ('Xây dựng Giao diện Kanban kéo thả với SortableJS', TaskPriority.HIGH, TaskStatus.IN_PROGRESS),
            ('Tích hợp Trợ lý AI Phân tích Rủi ro & Task Breakdown', TaskPriority.CRITICAL, TaskStatus.IN_PROGRESS),
            ('Kiểm thử Đóng gói & Thuyết minh Đồ án', TaskPriority.MEDIUM, TaskStatus.TODO)
        ]

        for title, prio, st in tasks_data:
            t = Task.objects.filter(project=project, title__icontains=title[:10]).first()
            if not t:
                t = Task.objects.create(
                    project=project,
                    title=title,
                    priority=prio,
                    status=st,
                    assignee=student_user,
                    created_by=student_user,
                    due_date=timezone.now().date() + timezone.timedelta(days=14)
                )
                TaskChecklistItem.objects.create(task=t, title='Hoàn thiện bản nháp 1', is_completed=True)
                TaskChecklistItem.objects.create(task=t, title='Review cùng Mentor', is_completed=st == TaskStatus.DONE)
            else:
                t.title = title
                t.save()

        # 4. Milestone
        ms, _ = Milestone.objects.get_or_create(
            project=project,
            name='Giai đoạn 1: Thiết kế & Khởi tạo CSDL',
            defaults={
                'description': 'Nộp bản thảo ERD và tài liệu yêu cầu SRS',
                'start_date': timezone.now().date(),
                'due_date': timezone.now().date() + timezone.timedelta(days=15),
                'status': MilestoneStatus.IN_PROGRESS
            }
        )
        if not _:
            ms.name = 'Giai đoạn 1: Thiết kế & Khởi tạo CSDL'
            ms.save()

        # 5. Time Log
        TimeLog.objects.get_or_create(
            user=student_user,
            project=project,
            defaults={
                'duration': 7200,
                'note': 'Lập trình tính năng Kanban và SortableJS'
            }
        )

        self.stdout.write(self.style.SUCCESS("Khoi tao du lieu seed_demo thanh cong!"))

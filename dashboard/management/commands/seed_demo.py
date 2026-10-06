from django.core.management.base import BaseCommand
from accounts.models import User, UserRole, UserStatus
from projects.models import Project, ProjectStatus, ProjectMember, MemberRole, MemberStatus, MentorStatus
from tasks.models import Task, TaskStatus, TaskPriority, TaskChecklistItem
from milestones.models import Milestone, MilestoneStatus
from dashboard.models import TimeLog
from django.utils import timezone

class Command(BaseCommand):
    help = 'Tao du lieu mau (seed data) cho he thong ProjectHub AI'

    def handle(self, *args, **options):
        self.stdout.write("Bat dau khoi tao du lieu mau seed_demo...")

        # 1. Users
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@projecthub.edu.vn',
                'first_name': 'Quan Tri',
                'last_name': 'He Thong',
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
                'first_name': 'Nguyen Van',
                'last_name': 'Huong Dan',
                'role': UserRole.MENTOR,
                'status': UserStatus.ACTIVE,
                'department': 'Khoa Cong Nghe Thong Tin'
            }
        )
        if _:
            mentor_user.set_password('mentor123')
            mentor_user.save()

        student_user, _ = User.objects.get_or_create(
            username='student',
            defaults={
                'email': 'student@projecthub.edu.vn',
                'first_name': 'Tran Van',
                'last_name': 'Sinh Vien',
                'role': UserRole.STUDENT,
                'status': UserStatus.ACTIVE,
                'department': 'Khoa Cong Nghe Thong Tin'
            }
        )
        if _:
            student_user.set_password('student123')
            student_user.save()

        # 2. Project
        project, _ = Project.objects.get_or_create(
            code='PRJ-2026-AI',
            defaults={
                'name': 'He thong Quan ly Do an Tot nghiep PROJECTHUB AI',
                'description': 'Xay dung nen tang ho tro sinh vien va giang vien quan ly tien do do an voi tro ly AI.',
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

        ProjectMember.objects.get_or_create(
            project=project,
            user=student_user,
            defaults={'role': MemberRole.LEADER, 'status': MemberStatus.ACCEPTED}
        )

        # 3. Tasks
        tasks_data = [
            ('Phan tich Yeu cau & Khao sat Nguoi dung', TaskPriority.CRITICAL, TaskStatus.DONE),
            ('Thiet ke CSDL & So do ERD chuan RBAC', TaskPriority.HIGH, TaskStatus.DONE),
            ('Xay dung Giao dien Kanban keo tha voi SortableJS', TaskPriority.HIGH, TaskStatus.IN_PROGRESS),
            ('Tich hop Tro ly AI Phan tich Rui ro & Task Breakdown', TaskPriority.CRITICAL, TaskStatus.IN_PROGRESS),
            ('Kiem thu Dong goi & Thuyet minh Do an', TaskPriority.MEDIUM, TaskStatus.TODO)
        ]

        for title, prio, st in tasks_data:
            t, created = Task.objects.get_or_create(
                project=project,
                title=title,
                defaults={
                    'priority': prio,
                    'status': st,
                    'assignee': student_user,
                    'created_by': student_user,
                    'due_date': timezone.now().date() + timezone.timedelta(days=14)
                }
            )
            if created:
                TaskChecklistItem.objects.create(task=t, title='Hoan thien ban nhap 1', is_completed=True)
                TaskChecklistItem.objects.create(task=t, title='Review cung Mentor', is_completed=st == TaskStatus.DONE)

        # 4. Milestone
        Milestone.objects.get_or_create(
            project=project,
            name='Giai doan 1: Thiet ke & Khoi tao CSDL',
            defaults={
                'description': 'Nop ban thao ERD va tai lieu yeu cau SRS',
                'start_date': timezone.now().date(),
                'due_date': timezone.now().date() + timezone.timedelta(days=15),
                'status': MilestoneStatus.IN_PROGRESS
            }
        )

        # 5. Time Log
        TimeLog.objects.get_or_create(
            user=student_user,
            project=project,
            defaults={
                'duration': 7200,
                'note': 'Lap trinh tinh nang Kanban va SortableJS'
            }
        )

        self.stdout.write(self.style.SUCCESS("Khoi tao du lieu seed_demo thanh cong!"))

from django.core.management.base import BaseCommand
from accounts.models import User, UserRole, UserStatus
from projects.models import Project, ProjectStatus, ProjectMember, MemberRole, MemberStatus, MentorStatus
from tasks.models import Task, TaskStatus, TaskPriority, TaskChecklistItem
from milestones.models import Milestone, MilestoneStatus, Event
from dashboard.models import TimeLog
from documents.models import Document, DocumentVersion
from reviews.models import Feedback, ReviewStatus
from notifications.models import Notification, NotificationType
from audit_log.models import ActivityLog, ActionType
from django.utils import timezone

class Command(BaseCommand):
    help = 'Khoi tao du lieu demo chuan cho VAU ProjectHub AI'

    def handle(self, *args, **options):
        self.stdout.write("Dang xoa va dong bo du lieu theo danh sach thanh vien quy dinh...")

        # 1. ADMIN USER
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@vau.edu.vn',
                'first_name': 'Hàng Không',
                'last_name': 'Quản trị viên',
                'role': UserRole.ADMIN,
                'status': UserStatus.ACTIVE,
                'is_staff': True,
                'is_superuser': True,
                'department': 'Khoa Công Nghệ Thông Tin'
            }
        )
        admin_user.set_password('admin123')
        admin_user.first_name = 'Hàng Không'
        admin_user.last_name = 'Quản trị viên'
        admin_user.email = 'admin@vau.edu.vn'
        admin_user.save()

        # 2. STUDENTS (5 STRICT MEMBERS ONLY)
        students_data = [
            ('student', 'trinhln@vau.edu.vn', 'Ngọc Trinh', 'Lê', True),       # LEADER (Lê Ngọc Trinh)
            ('hanndn', 'hanndn@vau.edu.vn', 'Doãn Ngọc Hân', 'Nguyễn', False),
            ('nghitdg', 'nghitdg@vau.edu.vn', 'Đàm Gia Nghi', 'Trần', False),
            ('tructtt', 'tructtt@vau.edu.vn', 'Thị Thanh Trúc', 'Phạm', False),
            ('tuyetnlh', 'tuyetnlh@vau.edu.vn', 'Lâm Huyền Tuyết', 'Nguyễn', False),
        ]

        student_objs = []
        valid_usernames = {'admin'}

        for username, email, first_name, last_name, is_leader in students_data:
            valid_usernames.add(username)
            st_user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'role': UserRole.STUDENT,
                    'status': UserStatus.ACTIVE,
                    'department': 'Khoa Công Nghệ Thông Tin',
                    'class_name': 'KTPM2022'
                }
            )
            st_user.set_password('student123')
            st_user.email = email
            st_user.first_name = first_name
            st_user.last_name = last_name
            st_user.role = UserRole.STUDENT
            st_user.status = UserStatus.ACTIVE
            st_user.department = 'Khoa Công Nghệ Thông Tin'
            st_user.class_name = 'KTPM2022'
            st_user.save()
            student_objs.append((st_user, is_leader))

        leader_user = student_objs[0][0] # Lê Ngọc Trinh

        # 3. MENTORS (3 STRICT MENTORS ONLY)
        mentors_data = [
            ('mentor', 'hieunt@vau.edu.vn', 'Thanh Hiếu', 'ThS.NCS. Nguyễn'),
            ('tuannla', 'tuannla@vau.edu.vn', 'Lương Anh Tuấn', 'TS. Nguyễn'),
            ('locth', 'locth@vau.edu.vn', 'Hoàng Lộc', 'TS. Trần'),
        ]

        mentor_objs = []

        for username, email, first_name, last_name in mentors_data:
            valid_usernames.add(username)
            mt_user, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'role': UserRole.MENTOR,
                    'status': UserStatus.ACTIVE,
                    'department': 'Khoa Công Nghệ Thông Tin',
                    'specialization': 'Phát triển Phần mềm & AI'
                }
            )
            mt_user.set_password('mentor123')
            mt_user.email = email
            mt_user.first_name = first_name
            mt_user.last_name = last_name
            mt_user.role = UserRole.MENTOR
            mt_user.status = UserStatus.ACTIVE
            mt_user.department = 'Khoa Công Nghệ Thông Tin'
            mt_user.save()
            mentor_objs.append(mt_user)

        main_mentor = mentor_objs[0] # ThS.NCS. Nguyễn Thanh Hiếu

        # Clean up old projects created by legacy users
        legacy_users = User.objects.exclude(username__in=valid_usernames)
        Project.objects.filter(created_by__in=legacy_users).delete()
        Task.objects.filter(assignee__in=legacy_users).delete()
        legacy_users.delete()

        # 4. PROJECTS (Leader is ALWAYS Lê Ngọc Trinh)
        project1, _ = Project.objects.get_or_create(
            code='PRJ-2026-AI',
            defaults={
                'name': 'Hệ thống Quản lý Đồ án Tốt nghiệp PROJECTHUB AI',
                'description': 'Hệ thống hỗ trợ sinh viên Khoa CNTT - Học viện Hàng không Việt Nam quản lý tiến độ đồ án và tương tác cùng giảng viên.',
                'category': 'WEB',
                'technology': 'Python, Django 5, Tailwind CSS, Alpine.js, PostgreSQL',
                'created_by': leader_user,
                'mentor': main_mentor,
                'mentor_status': MentorStatus.ACCEPTED,
                'status': ProjectStatus.IN_PROGRESS,
                'start_date': timezone.now().date() - timezone.timedelta(days=15),
                'end_date': timezone.now().date() + timezone.timedelta(days=75)
            }
        )
        project1.name = 'Hệ thống Quản lý Đồ án Tốt nghiệp PROJECTHUB AI'
        project1.created_by = leader_user
        project1.mentor = main_mentor
        project1.mentor_status = MentorStatus.ACCEPTED
        project1.save()

        project2, _ = Project.objects.get_or_create(
            code='PRJ-2026-AVIA',
            defaults={
                'name': 'Ứng dụng Quản lý Lịch bay & Đặt chỗ Hàng không VAU',
                'description': 'Hệ thống mô phỏng quản lý phi cơ, lịch khởi hành và điều phối nhân sự hàng không.',
                'category': 'MOBILE',
                'technology': 'Flutter, Dart, Django REST Framework, Postgres',
                'created_by': leader_user,
                'mentor': mentor_objs[1],
                'mentor_status': MentorStatus.ACCEPTED,
                'status': ProjectStatus.IN_PROGRESS,
                'start_date': timezone.now().date() - timezone.timedelta(days=10),
                'end_date': timezone.now().date() + timezone.timedelta(days=80)
            }
        )
        project2.name = 'Ứng dụng Quản lý Lịch bay & Đặt chỗ Hàng không VAU'
        project2.created_by = leader_user
        project2.mentor = mentor_objs[1]
        project2.mentor_status = MentorStatus.ACCEPTED
        project2.save()

        # 5. PROJECT MEMBERS
        for st_user, is_leader in student_objs:
            role = MemberRole.LEADER if is_leader else MemberRole.MEMBER
            pm1, _ = ProjectMember.objects.get_or_create(
                project=project1,
                user=st_user,
                defaults={'role': role, 'status': MemberStatus.ACCEPTED}
            )
            pm1.role = role
            pm1.save()

            pm2, _ = ProjectMember.objects.get_or_create(
                project=project2,
                user=st_user,
                defaults={'role': role, 'status': MemberStatus.ACCEPTED}
            )
            pm2.role = role
            pm2.save()

        # 6. TASKS
        tasks_data = [
            ('Phân tích Yêu cầu & Khảo sát Người dùng', TaskPriority.CRITICAL, TaskStatus.DONE, leader_user),
            ('Thiết kế CSDL & Sơ đồ ERD chuẩn RBAC', TaskPriority.HIGH, TaskStatus.DONE, student_objs[1][0]),
            ('Xây dựng Giao diện Kanban kéo thả với SortableJS', TaskPriority.HIGH, TaskStatus.IN_PROGRESS, student_objs[2][0]),
            ('Tích hợp Trợ lý AI Phân tích Rủi ro & Task Breakdown', TaskPriority.CRITICAL, TaskStatus.IN_PROGRESS, student_objs[3][0]),
            ('Kiểm thử Đóng gói & Thuyết minh Đồ án', TaskPriority.MEDIUM, TaskStatus.TODO, student_objs[4][0]),
            ('Nộp Báo cáo Tiến độ Tuần 4 cho Mentor Review', TaskPriority.HIGH, TaskStatus.REVIEW, leader_user),
        ]

        for title, prio, st, assignee in tasks_data:
            t, _ = Task.objects.get_or_create(
                project=project1,
                title=title,
                defaults={
                    'priority': prio,
                    'status': st,
                    'assignee': assignee,
                    'created_by': leader_user,
                    'due_date': timezone.now().date() + timezone.timedelta(days=10),
                    'description': f'Nhiệm vụ thuộc đồ án ProjectHub AI do {assignee.display_name} thực hiện.'
                }
            )
            t.priority = prio
            t.status = st
            t.assignee = assignee
            t.save()

            TaskChecklistItem.objects.get_or_create(task=t, title='Khảo sát quy trình hiện tại', defaults={'is_completed': True})
            TaskChecklistItem.objects.get_or_create(task=t, title='Review cùng Mentor', defaults={'is_completed': st == TaskStatus.DONE})

        # 7. MILESTONES & EVENTS
        Milestone.objects.get_or_create(
            project=project1,
            name='Giai đoạn 1: Thiết kế Kiến trúc & Khởi tạo CSDL',
            defaults={
                'description': 'Nộp bản thảo ERD và tài liệu thiết kế hệ thống SRS',
                'start_date': timezone.now().date() - timezone.timedelta(days=15),
                'due_date': timezone.now().date() + timezone.timedelta(days=5),
                'status': MilestoneStatus.IN_PROGRESS
            }
        )

        Event.objects.get_or_create(
            project=project1,
            title='Họp Review Tiến độ Tuần với Mentor PGS.TS Nguyễn Văn Minh',
            defaults={
                'event_type': 'MEETING',
                'start': timezone.now() + timezone.timedelta(days=1),
                'end': timezone.now() + timezone.timedelta(days=1, hours=2),
                'created_by': leader_user
            }
        )

        Event.objects.get_or_create(
            project=project1,
            title='Họp Review Tiến độ Giữa Kỳ cùng Mentor',
            defaults={
                'event_type': 'MEETING',
                'start': timezone.now() + timezone.timedelta(days=2),
                'end': timezone.now() + timezone.timedelta(days=2, hours=2),
                'created_by': leader_user
            }
        )

        # 8. TIME LOG
        TimeLog.objects.get_or_create(
            user=leader_user,
            project=project1,
            defaults={
                'duration': 14400,
                'note': 'Thiết kế giao diện Dark Navy và hoàn thiện báo cáo đồ án'
            }
        )

        # 9. REVIEWS & FEEDBACK
        Feedback.objects.get_or_create(
            project=project1,
            mentor=main_mentor,
            defaults={
                'content': 'Đồ án tiến độ rất tốt. Nhóm trưởng Lê Ngọc Trinh đã phân chia công việc hợp lý.',
                'rating': 5,
                'status': ReviewStatus.APPROVED
            }
        )

        # 10. DOCUMENTS
        doc1, _ = Document.objects.get_or_create(
            project=project1,
            title='Slide Thuyết minh Đồ án Tốt nghiệp Hội đồng VAU',
            defaults={
                'file_type': 'POWERPOINT',
                'uploaded_by': leader_user,
                'file_size': '4.2 MB',
                'description': 'Slide báo cáo tổng quan kiến trúc phần mềm và demo trợ lý AI.',
                'current_version': 1
            }
        )
        DocumentVersion.objects.get_or_create(
            document=doc1,
            version_number=1,
            defaults={
                'uploaded_by': leader_user,
                'change_log': 'Khởi tạo slide trình chiếu đồ án.'
            }
        )

        doc2, _ = Document.objects.get_or_create(
            project=project1,
            title='Báo cáo SRS & Sơ đồ CSDL ERD',
            defaults={
                'file_type': 'PDF',
                'uploaded_by': leader_user,
                'file_size': '2.8 MB',
                'description': 'Tài liệu phân tích yêu cầu SRS và bản vẽ ERD cơ sở dữ liệu.',
                'current_version': 1
            }
        )
        DocumentVersion.objects.get_or_create(
            document=doc2,
            version_number=1,
            defaults={
                'uploaded_by': leader_user,
                'change_log': 'Phiên bản thiết kế hệ thống v1.'
            }
        )

        # 11. NOTIFICATIONS
        Notification.objects.get_or_create(
            recipient=leader_user,
            title='Mentor đã chấp nhận Hướng dẫn',
            defaults={
                'message': 'ThS.NCS. Nguyễn Thanh Hiếu đã chấp nhận hướng dẫn đồ án PRJ-2026-AI của bạn.',
                'notification_type': NotificationType.SYSTEM
            }
        )
        Notification.objects.get_or_create(
            recipient=main_mentor,
            title='Bản thảo Đồ án Mới được Nộp',
            defaults={
                'message': 'Lê Ngọc Trinh vừa nộp bản thảo "Nộp Báo cáo Tiến độ Tuần 4 cho Mentor Review".',
                'notification_type': NotificationType.MENTOR_FEEDBACK
            }
        )

        # 12. AUDIT LOGS
        ActivityLog.objects.create(
            user=leader_user,
            action=ActionType.LOGIN,
            description='Đăng nhập hệ thống thành công với vai trò Sinh viên',
            ip_address='127.0.0.1'
        )
        ActivityLog.objects.create(
            user=main_mentor,
            action=ActionType.LOGIN,
            description='Đăng nhập hệ thống thành công với vai trò Giảng viên / Mentor',
            ip_address='127.0.0.1'
        )
        ActivityLog.objects.create(
            user=admin_user,
            action=ActionType.LOGIN,
            description='Đăng nhập hệ thống thành công với vai trò Quản trị viên',
            ip_address='127.0.0.1'
        )

        self.stdout.write(self.style.SUCCESS("Khoi tao du lieu seed_demo VAU thanh cong!"))

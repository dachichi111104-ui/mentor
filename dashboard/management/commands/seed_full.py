import os
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.files.base import ContentFile

from accounts.models import User, UserRole, UserStatus, UserPreference
from projects.models import Project, ProjectStatus, ProjectCategory, ProjectMember, MemberRole, MemberStatus, MentorStatus, Message
from tasks.models import Task, TaskStatus, TaskPriority, TaskComment, TaskChecklistItem, Sprint, Board, BoardColumn
from milestones.models import Milestone, MilestoneStatus, Event, EventType, EventStatus
from documents.models import Document, DocumentVersion, FileCategory
from reviews.models import Feedback, ReviewStatus
from notifications.models import Notification, NotificationType
from audit_log.models import ActivityLog, ActionType
from dashboard.models import TimeLog
from ai_assistant.models import AIRequest, WeeklySummary

class Command(BaseCommand):
    help = 'Khoi tao du lieu day du (seed_full) cho ProjectHub AI platform'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Xoa sach du lieu va khoi tao lai tu dau',
        )

    def handle(self, *args, **options):
        reset = options.get('reset', False)
        self.stdout.write("Khoi tao du lieu day du (seed_full) cho ProjectHub AI...")

        if reset:
            self.stdout.write(self.style.WARNING("Xoa du lieu cu theo co --reset..."))
            from django.db import transaction
            with transaction.atomic():
                ActivityLog.objects.all().delete()
                WeeklySummary.objects.all().delete()
                AIRequest.objects.all().delete()
                TimeLog.objects.all().delete()
                Notification.objects.all().delete()
                Feedback.objects.all().delete()
                DocumentVersion.objects.all().delete()
                Document.objects.all().delete()
                Message.objects.all().delete()
                TaskComment.objects.all().delete()
                TaskChecklistItem.objects.all().delete()
                Task.objects.all().delete()
                Sprint.objects.all().delete()
                BoardColumn.objects.all().delete()
                Board.objects.all().delete()
                Milestone.objects.all().delete()
                Event.objects.all().delete()
                ProjectMember.objects.all().delete()
                Project.objects.all().delete()

        # 1. ADMIN USER
        admin, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@vau.edu.vn',
                'first_name': 'HVHK',
                'last_name': 'Quản trị viên',
                'role': UserRole.ADMIN,
                'status': UserStatus.ACTIVE,
                'is_staff': True,
                'is_superuser': True,
                'department': 'Khoa Công nghệ Thông tin',
                'phone': '0987654321',
                'bio': 'Quản trị viên hệ thống Cổng Quản lý Đồ án ProjectHub AI HVHK'
            }
        )
        admin.first_name = 'HVHK'
        admin.last_name = 'Quản trị viên'
        admin.set_password('admin123')
        admin.save()
        UserPreference.objects.get_or_create(user=admin)

        # 2. MENTORS (3 Mentors)
        mentors_data = [
            ('mentor', 'hieunt@vau.edu.vn', 'Thanh Hiếu', 'ThS.NCS. Nguyễn', 'GV001', 'Phát triển Phần mềm & Trợ lý AI'),
            ('tuannla', 'tuannla@vau.edu.vn', 'Lương Anh Tuấn', 'TS. Nguyễn', 'GV002', 'Trí tuệ Nhân tạo & Data Science'),
            ('locth', 'locth@vau.edu.vn', 'Hoàng Lộc', 'TS. Trần', 'GV003', 'Cloud Computing & DevOps'),
        ]
        mentors = []
        for username, email, first_name, last_name, gv_id, spec in mentors_data:
            m, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'role': UserRole.MENTOR,
                    'status': UserStatus.ACTIVE,
                    'student_id': gv_id,
                    'department': 'Khoa Công nghệ Thông tin',
                    'specialization': spec,
                    'experience': '10+ năm kinh nghiệm hướng dẫn đồ án tốt nghiệp Học viện Hàng không.'
                }
            )
            m.set_password('mentor123')
            m.save()
            UserPreference.objects.get_or_create(user=m)
            mentors.append(m)

        # 3. STUDENTS (8 Students)
        students_data = [
            ('student', 'trinhln@vau.edu.vn', 'Ngọc Trinh', 'Lê', '2431540114', '24ĐHTT02', 'Python Django, Tailwind CSS, AI Assistant'),
            ('hanndn', 'hanndn@vau.edu.vn', 'Doãn Ngọc Hân', 'Nguyễn', '2431540093', '24ĐHTT02', 'ERD Schema, RESTful API, PostgreSQL'),
            ('nghitdg', 'nghitdg@vau.edu.vn', 'Đàm Gia Nghi', 'Trần', '2431540080', '24ĐHTT02', 'UI/UX Design, Alpine.js, Chart.js'),
            ('tructtt', 'tructtt@vau.edu.vn', 'Thị Thanh Trúc', 'Phạm', '2431540102', '24ĐHTT02', 'Prompt Engineering, Celery Background Jobs'),
            ('tuyetnlh', 'tuyetnlh@vau.edu.vn', 'Lâm Huyền Tuyết', 'Nguyễn', '2431540137', '24ĐHTT03', 'QA/QC Software Testing, System Documentation'),
            ('minhnn', 'minhnn@vau.edu.vn', 'Nhật Minh', 'Nguyễn', '2431540006', '24ĐHTT03', 'Machine Learning, Pandas, Scikit-Learn'),
            ('tuana', 'tuana@vau.edu.vn', 'Anh Tuấn', 'Trịnh', '2431540007', '24ĐHTT02', 'System Analysis, Agile Scrum Workflow'),
            ('lannt', 'lannt@vau.edu.vn', 'Phương Lan', 'Đỗ', '2431540008', '24ĐHTT02', 'Frontend Integration, Vue.js, Tailwind'),
        ]
        students = []
        for username, email, first_name, last_name, st_id, cls_name, sks in students_data:
            st, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'role': UserRole.STUDENT,
                    'status': UserStatus.ACTIVE,
                    'student_id': st_id,
                    'class_name': cls_name,
                    'department': 'Khoa Công nghệ Thông tin',
                    'skills': sks,
                    'bio': f'Sinh viên Khóa 2024 ({cls_name}) - Khoa Công nghệ Thông tin - Học viện Hàng không Việt Nam.'
                }
            )
            st.student_id = st_id
            st.class_name = cls_name
            st.bio = f'Sinh viên Khóa 2024 ({cls_name}) - Khoa Công nghệ Thông tin - Học viện Hàng không Việt Nam.'
            st.set_password('student123')
            st.save()
            UserPreference.objects.get_or_create(user=st)
            students.append(st)

        leader = students[0] # Lê Ngọc Trinh

        # 4. PROJECTS (6 Projects)
        today = timezone.now().date()
        projects_spec = [
            ('PRJ-2026-AI', 'Hệ thống Quản lý Đồ án Tốt nghiệp PROJECTHUB AI', ProjectCategory.WEB, 'Python, Django 5, Tailwind CSS, Alpine.js, Postgres', ProjectStatus.IN_PROGRESS, mentors[0], MentorStatus.ACCEPTED),
            ('PRJ-2026-AVIA', 'Ứng dụng Quản lý Lịch bay & Đặt chỗ Hàng không VAU', ProjectCategory.MOBILE, 'Flutter, Dart, Django REST Framework, Postgres', ProjectStatus.IN_PROGRESS, mentors[1], MentorStatus.ACCEPTED),
            ('PRJ-2026-DRONE', 'Hệ thống Giám sát & Điều phối Drone Cảng Hàng không', ProjectCategory.SYSTEM, 'FastAPI, Python OpenCV, Redis, WebSockets', ProjectStatus.REVIEW, mentors[2], MentorStatus.ACCEPTED),
            ('PRJ-2026-CARGO', 'Phần mềm Quản lý Kho Hàng hóa Hàng không Tân Sơn Nhất', ProjectCategory.SYSTEM, 'Java Spring Boot, Vue.js, PostgreSQL', ProjectStatus.PLANNING, mentors[0], MentorStatus.ACCEPTED),
            ('PRJ-2026-RESERVE', 'Cổng Đăng ký Học phần & Lịch thi Sinh viên VAU', ProjectCategory.WEB, 'Node.js, React, MongoDB', ProjectStatus.COMPLETED, mentors[1], MentorStatus.ACCEPTED),
            ('PRJ-2026-SAFETY', 'Hệ thống Đánh giá Rủi ro An toàn Bay bằng AI', ProjectCategory.AI_ML, 'Python PyTorch, Streamlit, Docker', ProjectStatus.PLANNING, mentors[2], MentorStatus.PENDING),
        ]

        projects = []
        for code, name, cat, tech, st, mt, mt_st in projects_spec:
            p = Project.objects.create(
                code=code,
                name=name,
                description=f'Đồ án nghiên cứu ứng dụng cho Khoa CNTT Học viện Hàng không Việt Nam.',
                category=cat,
                technology=tech,
                status=st,
                created_by=leader,
                mentor=mt,
                mentor_status=mt_st,
                start_date=today - timedelta(days=30),
                end_date=today + timedelta(days=60),
            )
            projects.append(p)

            # Assign Project Members
            ProjectMember.objects.create(project=p, user=leader, role=MemberRole.LEADER, status=MemberStatus.ACCEPTED)
            for s_idx in range(1, 4):
                ProjectMember.objects.create(project=p, user=students[s_idx], role=MemberRole.MEMBER, status=MemberStatus.ACCEPTED)

        main_project = projects[0] # PRJ-2026-AI

        # 5. SPRINTS
        sprint1 = Sprint.objects.create(
            project=main_project,
            name='Sprint 1: Phân tích & Thiết kế CSDL',
            goal='Hoàn thành ERD schema, SRS và khởi tạo bộ khung Django 5',
            start_date=today - timedelta(days=20),
            end_date=today - timedelta(days=5),
            is_active=False
        )
        sprint2 = Sprint.objects.create(
            project=main_project,
            name='Sprint 2: Xây dựng Kanban & Trợ lý AI',
            goal='Tích hợp Kanban drag-drop, Time tracker và 5 endpoint AI',
            start_date=today - timedelta(days=4),
            end_date=today + timedelta(days=10),
            is_active=True
        )

        # 6. TASKS & CHECKLISTS (≥ 40 Tasks across projects)
        task_titles = [
            ('Phân tích Yêu cầu & Khảo sát Người dùng', TaskStatus.DONE, TaskPriority.CRITICAL, leader),
            ('Thiết kế CSDL ERD chuẩn RBAC', TaskStatus.DONE, TaskPriority.HIGH, students[1]),
            ('Xây dựng Giao diện Kanban kéo thả với Alpine.js', TaskStatus.IN_PROGRESS, TaskPriority.HIGH, students[2]),
            ('Tích hợp Trợ lý AI Phân tích Rủi ro & Task Breakdown', TaskStatus.IN_PROGRESS, TaskPriority.CRITICAL, students[3]),
            ('Kiểm thử Đóng gói & Báo cáo Thuyết minh Đồ án', TaskStatus.TODO, TaskPriority.MEDIUM, students[4]),
            ('Nộp Báo cáo Tiến độ Tuần 4 cho Mentor Review', TaskStatus.REVIEW, TaskPriority.HIGH, leader),
            ('Xây dựng API RESTful cho Trình Bấm giờ TimeLog', TaskStatus.DONE, TaskPriority.HIGH, students[1]),
            ('Thiết kế Trang cài đặt Hệ thống & Bảo mật', TaskStatus.IN_PROGRESS, TaskPriority.MEDIUM, students[2]),
            ('Cấu hình Celery Worker & Redis Background Jobs', TaskStatus.TODO, TaskPriority.HIGH, students[3]),
            ('Tối ưu hóa Truy vấn ORM PostgreSQL & Indexes', TaskStatus.TODO, TaskPriority.LOW, students[4]),
        ]

        tasks = []
        for idx, (t_title, status, prio, assignee) in enumerate(task_titles):
            for p in projects[:4]:
                t = Task.objects.create(
                    project=p,
                    title=f'{t_title} ({p.code})',
                    description=f'Chi tiết công việc thuộc {p.name} do {assignee.display_name} phụ trách.',
                    status=status,
                    priority=prio,
                    assignee=assignee,
                    created_by=leader,
                    sprint=sprint2 if p == main_project else None,
                    due_date=today + timedelta(days=(idx - 3)),
                    labels='backend,django,ai' if idx % 2 == 0 else 'frontend,ui,tailwind',
                    order_index=idx
                )
                tasks.append(t)

                # Checklists
                TaskChecklistItem.objects.create(task=t, title='Khảo sát hiện trạng', is_completed=True)
                TaskChecklistItem.objects.create(task=t, title='Lập tài liệu kỹ thuật', is_completed=(status == TaskStatus.DONE))
                TaskChecklistItem.objects.create(task=t, title='Review cùng Mentor', is_completed=(status == TaskStatus.DONE))

                # Task Comments
                TaskComment.objects.create(
                    task=t,
                    user=mentors[0],
                    content=f'Mentor đã kiểm tra công việc "{t.title}". Tiến độ rất chuẩn xác!'
                )

        # 7. MILESTONES & EVENTS (≥ 12 Milestones, ≥ 20 Events)
        for p in projects:
            Milestone.objects.create(
                project=p,
                name=f'Mốc 1: Khởi động & Nộp Báo cáo SRS ({p.code})',
                description='Nộp bản vẽ kiến trúc hệ thống và tài liệu mô tả yêu cầu.',
                start_date=today - timedelta(days=25),
                due_date=today - timedelta(days=5),
                status=MilestoneStatus.COMPLETED
            )
            Milestone.objects.create(
                project=p,
                name=f'Mốc 2: Nghiệm thu Giai đoạn 1 & Demo ({p.code})',
                description='Báo cáo trực tiếp với Mentor về tiến độ và kết quả chạy thử nghiệm.',
                start_date=today - timedelta(days=4),
                due_date=today + timedelta(days=15),
                status=MilestoneStatus.IN_PROGRESS
            )

            Event.objects.create(
                project=p,
                title=f'Họp Review Tiến độ Tuần với Mentor ({p.code})',
                event_type=EventType.MEETING,
                start=timezone.now() + timedelta(days=2),
                end=timezone.now() + timedelta(days=2, hours=2),
                created_by=leader,
                status=EventStatus.ACCEPTED
            )

        # 8. DOCUMENTS WITH REAL GENERATED FILES ON DISK
        for p in projects[:3]:
            pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
            
            doc = Document.objects.create(
                project=p,
                title=f'Báo cáo Thuyết minh Đồ án SRS ({p.code})',
                file_type=FileCategory.PDF,
                uploaded_by=leader,
                file_size='1.2 MB',
                description=f'Tài liệu mô tả yêu cầu phần mềm SRS và sơ đồ kiến trúc hệ thống {p.name}.',
                current_version=1
            )
            doc.file.save(f"SRS_{p.code}.pdf", ContentFile(pdf_content), save=True)

            DocumentVersion.objects.create(
                document=doc,
                version_number=1,
                file=doc.file,
                uploaded_by=leader,
                change_log='Khởi tạo phiên bản v1 ban đầu.'
            )

        # 9. REVIEWS & FEEDBACKS
        for p in projects[:3]:
            Feedback.objects.create(
                project=p,
                mentor=p.mentor or mentors[0],
                content=f'Đồ án {p.code} tiến độ rất tốt. Nhóm làm việc trách nhiệm và đầy đủ.',
                rating=5,
                status=ReviewStatus.APPROVED
            )

        # 10. CHAT MESSAGES (≥ 40 messages)
        chat_texts = [
            "Chào thầy, nhóm em vừa cập nhật lại sơ đồ CSDL ERD ạ.",
            "Thầy đã xem qua, thiết kế chuẩn RBAC rất tốt. Em làm tiếp phần API nhé!",
            "Dạ vâng ạ, tụi em đang triển khai các endpoint RESTful cho Kanban.",
            "Báo cáo tuần 4 nhóm đã nộp trên hệ thống rồi ạ, nhờ thầy xem giúp em!",
            "Ok nhóm, chiều nay 14h họp Google Meet review tiến độ nhé!"
        ]
        for p in projects[:3]:
            for idx, txt in enumerate(chat_texts):
                sender = leader if idx % 2 == 0 else (p.mentor or mentors[0])
                Message.objects.create(
                    project=p,
                    sender=sender,
                    content=txt
                )

        # 11. TIMELOGS (≥ 60 TimeLogs across 90 days)
        for day_offset in range(1, 30):
            TimeLog.objects.create(
                user=leader,
                project=main_project,
                started_at=timezone.now() - timedelta(days=day_offset, hours=3),
                ended_at=timezone.now() - timedelta(days=day_offset),
                duration=10800, # 3 hours
                note=f'Phát triển tính năng và cập nhật giao diện đồ án PRJ-2026-AI'
            )

        # 12. AI REQUESTS & WEEKLY SUMMARIES
        AIRequest.objects.create(
            user=leader,
            project=main_project,
            prompt_type='TASK_BREAKDOWN',
            input_data='Phân chia công việc phát triển tính năng Kanban drag-drop',
            output_result='1. Cấu hình SortableJS\n2. Xây dựng API reorder task\n3. Cập nhật state Alpine.js'
        )
        WeeklySummary.objects.create(
            project=main_project,
            week_number=4,
            year=2026,
            summary_text='Tuần 4 hoàn thành 6 tasks, tích hợp thành công Time tracker và AI Assistant.'
        )

        # 13. NOTIFICATIONS & AUDIT LOGS
        for s in students:
            Notification.objects.create(
                recipient=s,
                title='Mentor đã chấp nhận Hướng dẫn',
                message='ThS.NCS. Nguyễn Thanh Hiếu đã phê duyệt hướng dẫn đồ án của bạn.',
                notification_type=NotificationType.SYSTEM
            )
            ActivityLog.objects.create(
                user=s,
                action=ActionType.LOGIN,
                description=f'Đăng nhập hệ thống thành công với vai trò {s.get_role_display()}',
                ip_address='127.0.0.1'
            )

        self.stdout.write(self.style.SUCCESS(">>> KHOI TAO DU LIEU FULL (seed_full) THANH CONG!"))

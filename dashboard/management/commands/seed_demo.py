import os, sys
import random
import secrets
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.core.files.base import ContentFile

from django.db.models import Q
from accounts.models import User, UserRole, UserStatus
from accounts.utils import generate_mentor_email, generate_student_email
from projects.models import Project, ProjectStatus, ProjectMember, MemberRole, MemberStatus, MentorStatus
from milestones.models import Milestone, MilestoneStatus, Appointment, AppointmentStatus
from tasks.models import Task, TaskPriority, TaskStatus, Sprint, TaskComment, TaskChecklistItem
from documents.models import Document, DocumentVersion
from reviews.models import Feedback, ReviewStatus
from audit_log.models import ActionType, ActivityLog
from notifications.models import Notification, NotificationType

BLUEPRINTS = {
    'PRJ-2026-AI': {
        'title': 'Hệ thống Trợ lý AI Hỗ trợ Quản lý Đồ án Học thuật (ProjectHub AI)',
        'category': 'WEB',
        'tech': 'Python, Django, Tailwind CSS, Alpine.js, PostgreSQL'
    },
    'PRJ-2026-AVIA': {
        'title': 'Ứng dụng Giám sát & Quản lý Lịch trình Hàng không Chế độ Realtime',
        'category': 'SYSTEM',
        'tech': 'FastAPI, Redis, WebSocket, Docker, ReactJS'
    },
    'PRJ-2026-DRONE': {
        'title': 'Hệ thống Quản lý & Điều phối Drone Giao vận Hàng hóa Tự động',
        'category': 'IOT',
        'tech': 'Python, MQTT, C++, ESP32, PostgreSQL'
    },
    'PRJ-2026-CARGO': {
        'title': 'Phần mềm Tối ưu hóa Chuỗi Cung ứng & Kho Hàng không',
        'category': 'WEB',
        'tech': 'Java, Spring Boot, Vue.js, PostgreSQL'
    },
    'PRJ-2026-RESERVE': {
        'title': 'Cổng Đặt vé & Quản lý Đặt chỗ Chuyến bay Tự động',
        'category': 'WEB',
        'tech': 'Node.js, Express, MongoDB, Next.js'
    },
    'PRJ-2026-SAFETY': {
        'title': 'Hệ thống Đánh giá & Cảnh báo Rủi ro An toàn Bay HVHK',
        'category': 'SYSTEM',
        'tech': 'Python, Django, PostgreSQL, Celery'
    }
}

# Minimal valid 1-page PDF file bytes
MINIMAL_PDF_BYTES = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF\n"

# Minimal valid 1x1 PNG bytes
MINIMAL_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"

class Command(BaseCommand):
    help = "Seeds database with diverse, realistic demo projects and users (Phase D)."

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Reset existing demo data before seeding')

    def handle(self, *args, **options):
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')

        from django.conf import settings
        if not settings.DEBUG and os.getenv('SEED_DEMO') != '1':
            self.stdout.write(self.style.ERROR("Lệnh seed_demo bị từ chối khi DEBUG=False ngoại trừ khi SEED_DEMO=1 được thiết lập."))
            return

        reset = options.get('reset')
        rng = random.Random(20261007)
        today = timezone.localdate()

        demo_password = os.getenv('DEMO_PASSWORD')
        if not demo_password:
            demo_password = secrets.token_urlsafe(10)
            self.stdout.write(self.style.WARNING(f"Mật khẩu các tài khoản Demo: {demo_password}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Mật khẩu các tài khoản Demo: {demo_password}"))

        with transaction.atomic():
            if reset:
                self.stdout.write("Cleaning old demo data...")
                demo_projects = Project.objects.filter(code__startswith='PRJ-2026-')
                demo_users = User.objects.filter(Q(email__endswith='@vau.edu.vn') | Q(email__endswith='@vaa.edu.vn')).exclude(username='admin')
                
                TaskChecklistItem.objects.filter(task__project__in=demo_projects).delete()
                TaskComment.objects.filter(task__project__in=demo_projects).delete()
                Task.objects.filter(project__in=demo_projects).delete()
                Sprint.objects.filter(project__in=demo_projects).delete()
                Milestone.objects.filter(project__in=demo_projects).delete()
                DocumentVersion.objects.filter(document__project__in=demo_projects).delete()
                Document.objects.filter(project__in=demo_projects).delete()
                Feedback.objects.filter(project__in=demo_projects).delete()
                Notification.objects.filter(Q(recipient__in=demo_users) | Q(sender__in=demo_users)).delete()
                ActivityLog.objects.filter(project__in=demo_projects).delete()
                ProjectMember.objects.filter(project__in=demo_projects).delete()
                demo_projects.delete()
                demo_users.delete()

            # 1. Users
            admin, _ = User.objects.get_or_create(
                username='admin',
                defaults={
                    'email': 'admin@vaa.edu.vn',
                    'first_name': 'Quản trị viên',
                    'last_name': 'HVHK',
                    'role': UserRole.ADMIN,
                    'status': UserStatus.ACTIVE,
                    'is_staff': True,
                    'is_superuser': True
                }
            )
            admin.email = 'admin@vaa.edu.vn'
            admin.set_password(demo_password)
            admin.save()

            mentors_data = [
                ('mentor1', 'Nguyễn Thanh', 'Hiếu', 'ThS.NCS. Nguyễn Thanh Hiếu', 'ThS.NCS.'),
                ('mentor2', 'Nguyễn Lương', 'Anh Tuấn', 'TS. Nguyễn Lương Anh Tuấn', 'TS.'),
                ('mentor3', 'Trần Hoàng', 'Lộc', 'TS. Trần Hoàng Lộc', 'TS.'),
            ]
            mentors = []
            for uname, fname, lname, display, title in mentors_data:
                email = generate_mentor_email(fname, lname)
                u, _ = User.objects.get_or_create(
                    username=uname,
                    defaults={
                        'email': email,
                        'first_name': fname,
                        'last_name': lname,
                        'role': UserRole.MENTOR,
                        'status': UserStatus.ACTIVE,
                        'department': 'Khoa Công nghệ Thông tin',
                        'specialization': 'Phát triển Phần mềm & Hệ thống AI'
                    }
                )
                u.email = email
                u.set_password(demo_password)
                u.save()
                mentors.append(u)

            # Pending mentor for approval test
            m_pending_email = generate_mentor_email('Đỗ Văn', 'Nam')
            m_pending, _ = User.objects.get_or_create(
                username='mentor_pending',
                defaults={
                    'email': m_pending_email,
                    'first_name': 'Đỗ Văn',
                    'last_name': 'Nam',
                    'role': UserRole.MENTOR,
                    'status': UserStatus.PENDING_APPROVAL,
                    'department': 'Khoa Vận tải Hàng không'
                }
            )
            m_pending.email = m_pending_email
            m_pending.set_password(demo_password)
            m_pending.save()

            # Students
            students_data = [
                ('student1', 'Lê Ngọc', 'Trinh', '2431540114', '24ĐHTT02'),
                ('student2', 'Nguyễn Doãn', 'Ngọc Hân', '2431540093', '24ĐHTT02'),
                ('student3', 'Phạm Thị', 'Thanh Trúc', '2431540102', '24ĐHTT02'),
                ('student4', 'Trần Đàm', 'Gia Nghi', '2431540080', '24ĐHTT02'),
                ('student5', 'Nguyễn Lâm', 'Huyền Tuyết', '2431540137', '24ĐHTT03'),
                ('student6', 'Hoàng Minh', 'Nhật', '2431540150', '24ĐHTT01'),
                ('student7', 'Võ Văn', 'Kiệt', '2431540161', '24ĐHTT01'),
                ('student8', 'Đặng Thái', 'Sơn', '2431540172', '24ĐHTT02'),
                ('student9', 'Bùi Phương', 'Nam', '2431540183', '24ĐHTT03'),
                ('student10', 'Trịnh Công', 'Vinh', '2431540194', '24ĐHTT01'),
                ('student11', 'Đỗ Khánh', 'Linh', '2431540205', '24ĐHTT02'),
                ('student12', 'Vũ Đức', 'Anh', '2431540216', '24ĐHTT03'),
                ('student13', 'Lý Hoàng', 'Long', '2431540227', '24ĐHTT01'),
                ('student14', 'Cao Thị', 'Mai', '2431540238', '24ĐHTT02'),
            ]
            students = []
            for uname, fname, lname, sid, cname in students_data:
                email = generate_student_email(sid, uname)
                u, _ = User.objects.get_or_create(
                    username=uname,
                    defaults={
                        'email': email,
                        'first_name': fname,
                        'last_name': lname,
                        'student_id': sid,
                        'class_name': cname,
                        'role': UserRole.STUDENT,
                        'status': UserStatus.ACTIVE,
                        'department': 'Khoa CNTT'
                    }
                )
                u.email = email
                u.set_password(demo_password)
                u.save()
                students.append(u)

            # Suspended student
            s_suspended_email = generate_student_email('2431540999', 'student_locked')
            s_suspended, _ = User.objects.get_or_create(
                username='student_locked',
                defaults={
                    'email': s_suspended_email,
                    'first_name': 'Phạm Quốc',
                    'last_name': 'Bảo',
                    'role': UserRole.STUDENT,
                    'status': UserStatus.SUSPENDED
                }
            )
            s_suspended.email = s_suspended_email
            s_suspended.set_password(demo_password)
            s_suspended.save()

            # 2. Projects & Blueprints
            blueprints = [
                {
                    'code': 'PRJ-2026-AI',
                    'name': 'Hệ thống Quản lý NCKH và Đồ án Hàng không ProjectHub AI',
                    'description': 'Nền tảng quản lý đồ án thông minh cho Học viện Hàng không Việt Nam tích hợp AI gợi ý rủi ro và trợ lý học thuật.',
                    'tech': 'Django 5, Tailwind CSS, Alpine.js, PostgreSQL, FastAPI',
                    'category': 'WEB',
                    'status': ProjectStatus.IN_PROGRESS,
                    'leader': students[0],
                    'members': [students[1], students[2], students[3]],
                    'mentor': mentors[0],
                    'mentor_status': MentorStatus.ACCEPTED,
                    'progress': 45,
                    'start_days': -30,
                    'end_days': 60,
                    'milestones_names': [
                        "Mốc 1: Khảo sát Yêu cầu & Thiết kế CSDL Hàng không",
                        "Mốc 2: Phát triển Core API & Giao diện Kanban AI",
                        "Mốc 3: Kiểm thử Tích hợp & Đóng gói Báo cáo Hội đồng"
                    ],
                    'tasks_blueprint': [
                        ("Thiết kế CSDL chuẩn hóa RBAC", "Xây dựng sơ đồ CSDL PostgreSQL cho người dùng và dự án.", TaskStatus.DONE, TaskPriority.HIGH, students[0], -25, -20),
                        ("Xây dựng API Phân quyền & Matrix", "Lập ma trận phân quyền PERMISSION_MATRIX tập trung.", TaskStatus.DONE, TaskPriority.CRITICAL, students[1], -20, -15),
                        ("Giao diện Bảng Kanban kéo thả", "Phát triển Kanban board Alpine.js với hiệu ứng mượt.", TaskStatus.IN_PROGRESS, TaskPriority.HIGH, students[2], -10, 5),
                        ("Tích hợp Trợ lý AI và engine rủi ro", "Kết nối engine AI đánh giá điểm rủi ro R1-R9.", TaskStatus.IN_PROGRESS, TaskPriority.MEDIUM, students[0], -5, 10),
                        ("Kiểm thử Tích hợp & Đơn vị 19 test case", "Viết test suite kiểm tra toàn bộ luồng hệ thống.", TaskStatus.TODO, TaskPriority.HIGH, students[3], 5, 20),
                    ]
                },
                {
                    'code': 'PRJ-2026-AVIA',
                    'name': 'Ứng dụng Di động Đặt vé & Trải nghiệm Hàng không AviaTravel',
                    'description': 'Ứng dụng mobile hỗ trợ hành khách tra cứu chuyến bay, check-in trực tuyến và dịch vụ mặt đất tại sân bay.',
                    'tech': 'Flutter, DRF, SQLite, Firebase, Redis',
                    'category': 'MOBILE',
                    'status': ProjectStatus.IN_PROGRESS,
                    'leader': students[5],
                    'members': [students[6], students[7], students[8], students[1]],
                    'mentor': mentors[1],
                    'mentor_status': MentorStatus.ACCEPTED,
                    'progress': 25,
                    'start_days': -45,
                    'end_days': 45,
                    'milestones_names': [
                        "Mốc 1: Thiết kế UI/UX App Mobile & Khung Chức năng",
                        "Mốc 2: Tích hợp Cổng Thanh toán & Check-in QR",
                        "Mốc 3: Kiểm thử Đa thiết bị & Đóng gói App Stores"
                    ],
                    'tasks_blueprint': [
                        ("Thiết kế UI/UX luồng Đặt vé chuyến bay", "Vẽ prototype và thiết kế giao diện Flutter.", TaskStatus.DONE, TaskPriority.HIGH, students[5], -40, -30),
                        ("Xây dựng Service Check-in Trực tuyến", "Viết API xử lý chọn ghế và sinh thẻ lên máy bay QR.", TaskStatus.IN_PROGRESS, TaskPriority.CRITICAL, students[6], -20, -5),
                        ("Tích hợp Cổng Thanh toán VNPay", "Kết nối SDK thanh toán trực tuyến.", TaskStatus.IN_PROGRESS, TaskPriority.HIGH, students[7], -15, -2),
                        ("Xử lý Thông báo Đẩy lịch bay", "Tích hợp Firebase Cloud Messaging nhận cảnh báo chậm chuyến.", TaskStatus.IN_PROGRESS, TaskPriority.HIGH, students[8], -10, 5),
                        ("Thử nghiệm trên thiết bị Android/iOS", "Kiểm tra độ ổn định và hiệu năng bộ nhớ.", TaskStatus.TODO, TaskPriority.MEDIUM, students[1], 10, 25),
                    ]
                },
                {
                    'code': 'PRJ-2026-DRONE',
                    'name': 'Hệ thống Giám sát & Cảnh báo An ninh Sân bay bằng Drone',
                    'description': 'Giải pháp IoT và Thị giác máy tính phát hiện xâm nhập đường băng và sự cố vật thể lạ (FOD).',
                    'tech': 'FastAPI, OpenCV, Python, MQTT, PyTorch',
                    'category': 'IOT',
                    'status': ProjectStatus.REVIEW,
                    'leader': students[7],
                    'members': [students[8], students[9], students[10]],
                    'mentor': mentors[2],
                    'mentor_status': MentorStatus.ACCEPTED,
                    'progress': 85,
                    'start_days': -60,
                    'end_days': 15,
                    'milestones_names': [
                        "Mốc 1: Thu thập Dữ liệu Video & Thiết lập Firmware Drone",
                        "Mốc 2: Huấn luyện Mô hình YOLOv8 & Realtime Dashboard",
                        "Mốc 3: Thử nghiệm Thực địa Đường băng & Báo cáo Nghiệm thu"
                    ],
                    'tasks_blueprint': [
                        ("Lập trình Firmware Điều khiển Drone", "Viết mã nhúng thu thập luồng video RTSP.", TaskStatus.DONE, TaskPriority.CRITICAL, students[7], -50, -40),
                        ("Huấn luyện Model YOLOv8 Nhận diện FOD", "Gán nhãn dữ liệu và train mô hình phát hiện vật thể.", TaskStatus.DONE, TaskPriority.HIGH, students[8], -40, -20),
                        ("Xây dựng Dashboard Cảnh báo Realtime", "Giao diện bản đồ hiển thị vị trí sự cố trên đường băng.", TaskStatus.DONE, TaskPriority.HIGH, students[7], -30, -10),
                        ("Nộp Báo cáo Tiến độ nghiệm thu", "Tổng hợp báo cáo kỹ thuật nộp Mentor.", TaskStatus.REVIEW, TaskPriority.HIGH, students[7], -10, 5),
                    ]
                },
                {
                    'code': 'PRJ-2026-CARGO',
                    'name': 'Hệ thống Quản lý Kho Hàng hóa và Logistics Hàng không',
                    'description': 'Hệ thống quản lý chuỗi cung ứng hàng hóa hàng không, theo dõi vận đơn AWB và lưu kho lạnh.',
                    'tech': 'Spring Boot, Vue.js, MySQL, RabbitMQ',
                    'category': 'SYSTEM',
                    'status': ProjectStatus.PLANNING,
                    'leader': students[9],
                    'members': [students[10], students[11], students[12]],
                    'mentor': mentors[0],
                    'mentor_status': MentorStatus.ACCEPTED,
                    'progress': 10,
                    'start_days': -10,
                    'end_days': 80,
                    'milestones_names': [
                        "Mốc 1: Phân tích Quy trình Vận đơn AWB & Khảo sát Kho",
                        "Mốc 2: Thiết kế Hệ thống Quản lý Cung ứng Hàng hóa",
                        "Mốc 3: Triển khai Module Theo dõi Thời gian thực"
                    ],
                    'tasks_blueprint': [
                        ("Phân tích Yêu cầu Nghiệp vụ AWB", "Khảo sát quy trình quản lý vận đơn hàng hóa.", TaskStatus.TODO, TaskPriority.MEDIUM, None, 2, 10),
                        ("Khảo sát Hạ tầng Kho lạnh", "Đánh giá thiết bị tích hợp cảm biến nhiệt độ.", TaskStatus.TODO, TaskPriority.LOW, None, 5, 15),
                    ]
                },
                {
                    'code': 'PRJ-2026-RESERVE',
                    'name': 'Hệ thống Đặt chỗ Dịch vụ Mặt đất và Lounge Sân bay',
                    'description': 'Hệ thống quản lý và đặt trước phòng chờ thương gia, xe đưa đón và dịch vụ ưu tiên tại sân bay.',
                    'tech': 'Node.js, Express, React, MongoDB, Redis',
                    'category': 'WEB',
                    'status': ProjectStatus.COMPLETED,
                    'leader': students[11],
                    'members': [students[12], students[13], students[0], students[4]],
                    'mentor': mentors[1],
                    'mentor_status': MentorStatus.ACCEPTED,
                    'progress': 100,
                    'start_days': -90,
                    'end_days': -10,
                    'milestones_names': [
                        "Mốc 1: Khảo sát Sơ đồ Phòng chờ Thương gia & API Backend",
                        "Mốc 2: Tích hợp Check-in QR & Thanh toán Trực tuyến",
                        "Mốc 3: Nghiệm thu Đề tài & Báo cáo Hội đồng Xuất sắc"
                    ],
                    'tasks_blueprint': [
                        ("Xây dựng API Quản lý Sơ đồ Lounge", "Thiết lập sơ đồ chỗ ngồi và trạng thái phòng chờ.", TaskStatus.DONE, TaskPriority.HIGH, students[11], -80, -60),
                        ("Tích hợp Quét Mã QR Check-in", "Xây dựng tính năng quét vé thương gia.", TaskStatus.DONE, TaskPriority.HIGH, students[12], -60, -40),
                        ("Báo cáo Thống kê Doanh thu Dịch vụ", "Biểu đồ phân tích lưu lượng hành khách.", TaskStatus.DONE, TaskPriority.MEDIUM, students[13], -40, -20),
                        ("Báo vệ Nghiệm thu Xuất sắc", "Hoàn thành bài thuyết trình và nghiệm thu đề tài.", TaskStatus.DONE, TaskPriority.CRITICAL, students[11], -20, -10),
                    ]
                },
                {
                    'code': 'PRJ-2026-SAFETY',
                    'name': 'Hệ thống Phân tích & Dự báo An toàn Bay bằng Học máy',
                    'description': 'Ứng dụng AI phân tích dữ liệu nhật ký sự cố hàng không và dự báo các chỉ số an toàn bay.',
                    'tech': 'PyTorch, Streamlit, Pandas, Scikit-learn',
                    'category': 'AI_ML',
                    'status': ProjectStatus.PLANNING,
                    'leader': students[13],
                    'members': [students[2]],
                    'mentor': mentors[2],
                    'mentor_status': MentorStatus.PENDING,
                    'progress': 0,
                    'start_days': 0,
                    'end_days': 90,
                    'milestones_names': [
                        "Mốc 1: Thu thập & Tiền xử lý Dữ liệu Nhật ký Sự cố",
                        "Mốc 2: Xây dựng & Đánh giá Model Dự báo An toàn",
                        "Mốc 3: Triển khai Dashboard Streamlit & Nghiệm thu"
                    ],
                    'tasks_blueprint': []
                }
            ]

            from dashboard.models import TimeLog
            from milestones.models import Event, EventType, EventStatus

            for bp in blueprints:
                proj, _ = Project.objects.get_or_create(
                    code=bp['code'],
                    defaults={
                        'name': bp['name'],
                        'description': bp['description'],
                        'technology': bp['tech'],
                        'category': bp['category'],
                        'status': bp['status'],
                        'created_by': bp['leader'],
                        'mentor': bp['mentor'],
                        'mentor_status': bp['mentor_status'],
                        'start_date': today + timezone.timedelta(days=bp['start_days']),
                        'end_date': today + timezone.timedelta(days=bp['end_days'])
                    }
                )

                # Memberships
                ProjectMember.objects.get_or_create(
                    project=proj,
                    user=bp['leader'],
                    defaults={'role': MemberRole.LEADER, 'status': MemberStatus.ACCEPTED}
                )
                for m_user in bp['members']:
                    ProjectMember.objects.get_or_create(
                        project=proj,
                        user=m_user,
                        defaults={'role': MemberRole.MEMBER, 'status': MemberStatus.ACCEPTED}
                    )

                # Milestones with unique names
                ms_names = bp.get('milestones_names', ["Mốc 1", "Mốc 2", "Mốc 3"])
                m1, _ = Milestone.objects.get_or_create(
                    project=proj,
                    name=ms_names[0],
                    defaults={
                        'description': 'Hoàn thiện hồ sơ khảo sát và sơ đồ kiến trúc.',
                        'start_date': today + timezone.timedelta(days=bp['start_days']),
                        'due_date': today + timezone.timedelta(days=bp['start_days'] + 20),
                        'status': MilestoneStatus.COMPLETED if (bp['progress'] >= 40) else MilestoneStatus.IN_PROGRESS
                    }
                )
                m2, _ = Milestone.objects.get_or_create(
                    project=proj,
                    name=ms_names[1],
                    defaults={
                        'description': 'Xây dựng các module chức năng trọng tâm.',
                        'start_date': today + timezone.timedelta(days=bp['start_days'] + 21),
                        'due_date': today + timezone.timedelta(days=bp['start_days'] + 50),
                        'status': MilestoneStatus.COMPLETED if (bp['progress'] >= 80) else MilestoneStatus.PENDING
                    }
                )
                m3, _ = Milestone.objects.get_or_create(
                    project=proj,
                    name=ms_names[2],
                    defaults={
                        'description': 'Đóng gói sản phẩm và báo cáo hội đồng.',
                        'start_date': today + timezone.timedelta(days=bp['start_days'] + 51),
                        'due_date': today + timezone.timedelta(days=bp['end_days']),
                        'status': MilestoneStatus.COMPLETED if (bp['progress'] == 100) else MilestoneStatus.PENDING
                    }
                )

                # Sprints for IN_PROGRESS projects
                if bp['status'] == ProjectStatus.IN_PROGRESS:
                    Sprint.objects.get_or_create(
                        project=proj,
                        name=f"Sprint 1 - Khởi chạy [{proj.code}]",
                        defaults={
                            'goal': 'Xây dựng khung giao diện và API cơ bản.',
                            'start_date': today + timezone.timedelta(days=bp['start_days']),
                            'end_date': today + timezone.timedelta(days=bp['start_days'] + 14),
                            'is_active': False
                        }
                    )
                    Sprint.objects.get_or_create(
                        project=proj,
                        name=f"Sprint 2 - Tích hợp [{proj.code}]",
                        defaults={
                            'goal': 'Hoàn thiện luồng dữ liệu chính và kết nối AI.',
                            'start_date': today + timezone.timedelta(days=bp['start_days'] + 15),
                            'end_date': today + timezone.timedelta(days=bp['start_days'] + 30),
                            'is_active': True
                        }
                    )

                # Tasks
                for t_title, t_desc, t_status, t_prio, t_assignee, s_off, e_off in bp['tasks_blueprint']:
                    t_due = today + timezone.timedelta(days=e_off)
                    t_obj, t_created = Task.objects.get_or_create(
                        project=proj,
                        title=t_title,
                        defaults={
                            'description': t_desc,
                            'status': t_status,
                            'priority': t_prio,
                            'assignee': t_assignee,
                            'created_by': bp['leader'],
                            'milestone': m1 if e_off < 0 else m2,
                            'due_date': t_due,
                            'status_changed_at': timezone.now() - timezone.timedelta(days=abs(s_off)),
                            'completed_at': (timezone.now() - timezone.timedelta(days=abs(e_off))) if t_status == TaskStatus.DONE else None
                        }
                    )
                    if t_created:
                        TaskChecklistItem.objects.create(task=t_obj, title="Khảo sát tài liệu yêu cầu", is_completed=True)
                        TaskChecklistItem.objects.create(task=t_obj, title="Viết mã nguồn và kiểm thử", is_completed=(t_status == TaskStatus.DONE))

                        # TimeLog seed entry
                        if t_assignee:
                            TimeLog.objects.create(
                                user=t_assignee,
                                project=proj,
                                task=t_obj,
                                duration=3600 * 4,
                                note=f"Lập trình module cho task '{t_title}'"
                            )

                # Seed Calendar Event
                Event.objects.get_or_create(
                    project=proj,
                    title=f"Họp Mentor định kỳ - Đồ án {proj.code}",
                    defaults={
                        'event_type': EventType.MEETING,
                        'start': timezone.now() + timezone.timedelta(days=2),
                        'end': timezone.now() + timezone.timedelta(days=2, hours=1),
                        'status': EventStatus.ACCEPTED,
                        'created_by': bp['leader'],
                        'link': 'https://meet.google.com/vau-demo-project'
                    }
                )

                # Feedbacks
                if bp['code'] == 'PRJ-2026-DRONE':
                    Feedback.objects.get_or_create(
                        project=proj,
                        mentor=mentors[2],
                        defaults={
                            'content': 'Cần bổ sung thêm ma trận đánh giá độ chính xác Precision/Recall cho mô hình nhận diện FOD.',
                            'rating': 4,
                            'status': ReviewStatus.NEED_REVISION
                        }
                    )
                elif bp['code'] == 'PRJ-2026-RESERVE':
                    Feedback.objects.get_or_create(
                        project=proj,
                        mentor=mentors[1],
                        defaults={
                            'content': 'Đồ án hoàn thành xuất sắc, giao diện mượt mà và báo cáo đầy đủ chỉ tiêu.',
                            'rating': 5,
                            'status': ReviewStatus.APPROVED
                        }
                    )

                # Documents with real valid PDF files
                doc, doc_created = Document.objects.get_or_create(
                    project=proj,
                    title=f"Báo cáo Kiến trúc & Thiết kế [{proj.code}]",
                    defaults={
                        'uploaded_by': bp['leader'],
                        'file_type': 'pdf',
                        'file_size': '245 KB',
                        'current_version': 1
                    }
                )
                if doc_created:
                    doc.file.save(f"report_{proj.code}.pdf", ContentFile(MINIMAL_PDF_BYTES), save=True)
                    DocumentVersion.objects.create(
                        document=doc,
                        version_number=1,
                        file=doc.file,
                        uploaded_by=bp['leader'],
                        change_log="Phiên bản khởi tạo báo cáo đồ án."
                    )

                # Seed Appointment
                if proj.mentor:
                    Appointment.objects.get_or_create(
                        project=proj,
                        student=bp['leader'],
                        mentor=proj.mentor,
                        title=f"Họp duyệt tiến độ với Mentor [{proj.code}]",
                        defaults={
                            'notes': "Thảo luận về các khó khăn kỹ thuật và mốc kế tiếp.",
                            'start_time': timezone.now() + timezone.timedelta(days=1, hours=2),
                            'end_time': timezone.now() + timezone.timedelta(days=1, hours=3),
                            'status': AppointmentStatus.ACCEPTED,
                            'location': "Phòng A2-301 / Online Google Meet"
                        }
                    )

                # Activity Log
                ActivityLog.objects.get_or_create(
                    project=proj,
                    action=ActionType.CREATE_PROJECT,
                    defaults={
                        'user': bp['leader'],
                        'entity_type': 'Project',
                        'entity_id': proj.id,
                        'description': f"Khởi tạo đồ án {proj.code} - {proj.name}"
                    }
                )

        self.stdout.write(self.style.SUCCESS("Successfully seeded demo data (Phase E)!"))


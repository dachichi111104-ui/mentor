import os
import django
from datetime import date, timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'projecthub_config.settings')
django.setup()

from accounts.models import User, UserRole, UserStatus
from projects.models import Project, ProjectMember, ProjectStatus, ProjectCategory, MemberRole
from milestones.models import Milestone, MilestoneStatus
from tasks.models import Task, TaskComment, TaskPriority, TaskStatus
from documents.models import Document, DocumentVersion, FileCategory
from reviews.models import Feedback, ReviewStatus
from notifications.models import Notification, NotificationType
from audit_log.models import ActivityLog, ActionType

def run_seed():
    print(">>> Khoi tao du lieu mau theo phong cach Portal Hoc thuat ProjectHub AI...")

    # Clear existing data safely
    ActivityLog.objects.all().delete()
    Notification.objects.all().delete()
    Feedback.objects.all().delete()
    DocumentVersion.objects.all().delete()
    Document.objects.all().delete()
    TaskComment.objects.all().delete()
    Task.objects.all().delete()
    Milestone.objects.all().delete()
    ProjectMember.objects.all().delete()
    Project.objects.all().delete()
    User.objects.all().delete()

    print("Cleared existing database.")

    # 1. CREATE USERS
    admin = User.objects.create_superuser(
        username='admin',
        email='admin@projecthub.vn',
        password='admin123',
        first_name='Quản trị',
        last_name='Hệ thống',
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        phone='0987654321',
        department='Phòng CNTT & Đào tạo',
        bio='Quản trị viên hệ thống Cổng Quản lý Đồ án ProjectHub AI'
    )
    admin.set_password('admin123')
    admin.save()

    # Mentors
    mentor1 = User.objects.create_user(
        username='mentor1',
        email='mentor1@projecthub.vn',
        password='user123',
        first_name='Minh',
        last_name='PGS.TS Nguyễn Văn',
        role=UserRole.MENTOR,
        status=UserStatus.ACTIVE,
        student_id='GV001',
        phone='0912345678',
        department='Khoa Công nghệ Thông tin',
        specialization='Kỹ thuật Phần mềm, Kiến trúc Hệ thống SaaS, AI/ML',
        experience='15 năm giảng dạy và hướng dẫn hơn 120 đồ án tốt nghiệp.',
        bio='Giảng viên hướng dẫn chuyên môn Kỹ thuật phần mềm.'
    )
    mentor1.set_password('user123')
    mentor1.save()

    mentor2 = User.objects.create_user(
        username='mentor2',
        email='mentor2@projecthub.vn',
        password='user123',
        first_name='Hồng',
        last_name='TS. Trần Thị',
        role=UserRole.MENTOR,
        status=UserStatus.ACTIVE,
        student_id='GV002',
        phone='0923456789',
        department='Khoa Khoa học Dữ liệu',
        specialization='Trí tuệ nhân tạo, Học máy, Xử lý ngôn ngữ tự nhiên (NLP)',
        experience='10 năm kinh nghiệm nghiên cứu AI và cố vấn đồ án.',
        bio='Giảng viên hướng dẫn môn học Khoa học dữ liệu và AI.'
    )
    mentor2.set_password('user123')
    mentor2.save()

    mentor3 = User.objects.create_user(
        username='mentor3',
        email='mentor3@projecthub.vn',
        password='user123',
        first_name='Nam',
        last_name='ThS. Lê Hoàng',
        role=UserRole.MENTOR,
        status=UserStatus.ACTIVE,
        student_id='GV003',
        phone='0934567890',
        department='Khoa Mạng máy tính & Viễn thông',
        specialization='Phát triển Web Fullstack, Flutter Mobile, DevOps',
        experience='8 năm kiến trúc sư giải pháp phần mềm doanh nghiệp.',
        bio='Giảng viên tư vấn phát triển ứng dụng web và di động.'
    )
    mentor3.set_password('user123')
    mentor3.save()

    # Students
    students = []
    student_data = [
        ('student1', 'student1@projecthub.vn', 'Anh', 'Nguyễn Văn', '20120001', 'KTPM2021', 'Phát triển Backend Python/Django, Thiết kế CSDL'),
        ('student2', 'student2@projecthub.vn', 'Bình', 'Phạm Thị', '20120002', 'KTPM2021', 'Thiết kế Giao diện UI/UX, Tailwind CSS, JavaScript'),
        ('student3', 'student3@projecthub.vn', 'Cường', 'Lê Hoàng', '20120003', 'KTPM2021', 'Phát triển Ứng dụng Di động, Tích hợp RESTful API'),
        ('student4', 'student4@projecthub.vn', 'Dung', 'Đỗ Minh', '20120004', 'KHMT2021', 'Khoa học Dữ liệu, Python Pandas, Xử lý ngôn ngữ'),
        ('student5', 'student5@projecthub.vn', 'Giang', 'Vũ Quốc', '20120005', 'HTTT2021', 'Phân tích Yêu cầu Nghiệp vụ, Phân tích Hệ thống'),
        ('student6', 'student6@projecthub.vn', 'Hương', 'Ngô Thu', '20120006', 'KTPM2021', 'Kiểm thử Phần mềm, Đảm bảo Chất lượng QA'),
    ]

    for username, email, first_name, last_name, st_id, cls, skills in student_data:
        s = User.objects.create_user(
            username=username,
            email=email,
            password='user123',
            first_name=first_name,
            last_name=last_name,
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
            student_id=st_id,
            department='Khoa Công nghệ Thông tin',
            class_name=cls,
            skills=skills,
            bio='Sinh viên khóa 2021 - Đang thực hiện đồ án môn học.'
        )
        s.set_password('user123')
        s.save()
        students.append(s)

    print(f"Created Users: Admin, 3 Mentors, {len(students)} Students.")

    # 2. CREATE PROJECTS
    today = timezone.now().date()

    proj1 = Project.objects.create(
        name='ProjectHub AI - Nền tảng quản lý đồ án sinh viên & hỗ trợ Mentor',
        code='PROJ-2026-001',
        description='Hệ thống quản lý toàn bộ vòng đời đồ án sinh viên tích hợp trợ lý AI hỗ trợ lập kế hoạch công việc, tổng hợp báo cáo tiến độ và cảnh báo rủi ro.',
        category=ProjectCategory.WEB,
        technology='Python, Django, Tailwind CSS, HTML5, SQLite',
        start_date=today - timedelta(days=30),
        end_date=today + timedelta(days=45),
        status=ProjectStatus.IN_PROGRESS,
        created_by=students[0],
        mentor=mentor1,
        repo_url='https://github.com/projecthub/projecthub-ai',
        demo_url='https://projecthub-demo.vn'
    )
    ProjectMember.objects.create(project=proj1, user=students[0], role=MemberRole.LEADER)
    ProjectMember.objects.create(project=proj1, user=students[1], role=MemberRole.MEMBER)
    ProjectMember.objects.create(project=proj1, user=students[2], role=MemberRole.MEMBER)

    proj2 = Project.objects.create(
        name='EcoMart - Hệ thống Thương mại Điện tử Nông sản Hữu cơ',
        code='PROJ-2026-002',
        description='Ứng dụng web quản lý và phân phối nông sản sạch chuẩn VietGAP tích hợp tư vấn sản phẩm tự động.',
        category=ProjectCategory.WEB,
        technology='Node.js, ReactJS, MongoDB, Express',
        start_date=today - timedelta(days=50),
        end_date=today + timedelta(days=10),
        status=ProjectStatus.REVIEW,
        created_by=students[3],
        mentor=mentor3,
        repo_url='https://github.com/ecomart/ecomart-web',
        demo_url='https://ecomart.vn'
    )
    ProjectMember.objects.create(project=proj2, user=students[3], role=MemberRole.LEADER)
    ProjectMember.objects.create(project=proj2, user=students[4], role=MemberRole.MEMBER)

    proj3 = Project.objects.create(
        name='MediHealth - Ứng dụng Theo dõi Sức khỏe Cá nhân',
        code='PROJ-2026-003',
        description='Ứng dụng di động theo dõi chỉ số sinh hiệu cá nhân và nhắc nhở lịch khám bệnh định kỳ.',
        category=ProjectCategory.MOBILE,
        technology='Flutter, Dart, Firebase',
        start_date=today - timedelta(days=10),
        end_date=today + timedelta(days=80),
        status=ProjectStatus.PLANNING,
        created_by=students[4],
        mentor=mentor2,
        repo_url='https://github.com/medihealth/mobile-app'
    )
    ProjectMember.objects.create(project=proj3, user=students[4], role=MemberRole.LEADER)
    ProjectMember.objects.create(project=proj3, user=students[5], role=MemberRole.MEMBER)

    proj4 = Project.objects.create(
        name='SmartLibrary - Hệ thống Quản lý Thư viện Thông minh Mã QR',
        code='PROJ-2026-004',
        description='Giải pháp quản lý mượn trả sách tự động tại thư viện trường đại học bằng mã QR.',
        category=ProjectCategory.SYSTEM,
        technology='Python OpenCV, FastAPI, PostgreSQL',
        start_date=today - timedelta(days=90),
        end_date=today - timedelta(days=5),
        status=ProjectStatus.COMPLETED,
        created_by=students[1],
        mentor=mentor1,
        repo_url='https://github.com/smartlibrary/qr-system'
    )
    ProjectMember.objects.create(project=proj4, user=students[1], role=MemberRole.LEADER)
    ProjectMember.objects.create(project=proj4, user=students[2], role=MemberRole.MEMBER)

    print("Created 4 Projects with memberships.")

    # 3. CREATE MILESTONES FOR PROJ1
    ms1 = Milestone.objects.create(
        project=proj1,
        name='Milestone 1: Phân tích yêu cầu & Thiết kế Hệ thống',
        description='Xác định danh sách yêu cầu nghiệp vụ, sơ đồ Use-case, ERD Database và Wireframe giao diện.',
        start_date=today - timedelta(days=30),
        due_date=today - timedelta(days=15),
        status=MilestoneStatus.COMPLETED
    )
    ms2 = Milestone.objects.create(
        project=proj1,
        name='Milestone 2: Phát triển Core Backend & Authentication',
        description='Cấu hình Django project, Custom User Model, kiểm soát quyền truy cập RBAC và Middleware nhật ký.',
        start_date=today - timedelta(days=14),
        due_date=today + timedelta(days=5),
        status=MilestoneStatus.IN_PROGRESS
    )
    ms3 = Milestone.objects.create(
        project=proj1,
        name='Milestone 3: Bảng công việc Kanban & Quản lý Tài liệu',
        description='Xây dựng giao diện Kanban tương tác, quản lý danh mục tài liệu và nhận xét review từ Mentor.',
        start_date=today + timedelta(days=6),
        due_date=today + timedelta(days=25),
        status=MilestoneStatus.PENDING
    )

    # 4. CREATE TASKS FOR PROJ1
    t1 = Task.objects.create(
        project=proj1,
        milestone=ms1,
        title='Phân tích yêu cầu nghiệp vụ các nhóm người dùng',
        description='Xác định phạm vi chức năng chi tiết cho 3 role: Sinh viên, Mentor và Admin.',
        assignee=students[0],
        priority=TaskPriority.HIGH,
        status=TaskStatus.DONE,
        due_date=today - timedelta(days=20),
        labels='Requirement, SRS',
        order_index=1,
        created_by=students[0]
    )
    t2 = Task.objects.create(
        project=proj1,
        milestone=ms1,
        title='Thiết kế sơ đồ Cơ sở Dữ liệu Quan hệ ERD',
        description='Thiết kế cấu trúc bảng dữ liệu users, projects, tasks, milestones, documents, feedbacks, audit_logs.',
        assignee=students[0],
        priority=TaskPriority.CRITICAL,
        status=TaskStatus.DONE,
        due_date=today - timedelta(days=16),
        labels='Database, ERD',
        order_index=2,
        created_by=students[0]
    )
    t3 = Task.objects.create(
        project=proj1,
        milestone=ms2,
        title='Xây dựng Authentication & Role Control Middleware',
        description='Kiểm tra quyền truy cập theo role. Ngăn chặn tài khoản sinh viên truy cập trái phép trang Admin.',
        assignee=students[0],
        priority=TaskPriority.CRITICAL,
        status=TaskStatus.IN_PROGRESS,
        due_date=today + timedelta(days=1),
        labels='Auth, Security',
        order_index=1,
        created_by=students[0]
    )
    t4 = Task.objects.create(
        project=proj1,
        milestone=ms2,
        title='Thiết kế Giao diện Cổng Cổng thông tin Học thuật',
        description='Xây dựng Design System chuẩn Academic Navy và Warm Gray, phông chữ Inter dễ đọc.',
        assignee=students[1],
        priority=TaskPriority.HIGH,
        status=TaskStatus.IN_PROGRESS,
        due_date=today + timedelta(days=3),
        labels='UI/UX, Layout',
        order_index=2,
        created_by=students[0]
    )
    t5 = Task.objects.create(
        project=proj1,
        milestone=ms2,
        title='Phát triển Bảng công việc Kanban kéo thả',
        description='Hỗ trợ chuyển đổi trạng thái công việc (TODO -> IN_PROGRESS -> REVIEW -> DONE).',
        assignee=students[2],
        priority=TaskPriority.HIGH,
        status=TaskStatus.REVIEW,
        due_date=today + timedelta(days=2),
        labels='Kanban, JavaScript',
        order_index=1,
        created_by=students[0]
    )

    # 5. CREATE COMMENTS
    TaskComment.objects.create(
        task=t3,
        user=students[1],
        content='Đã cập nhật mã trạng thái 403 Forbidden chuẩn cho các route bảo mật.'
    )
    TaskComment.objects.create(
        task=t3,
        user=students[0],
        content='Đang kiểm tra thêm Middleware tự động ghi nhận nhật ký hệ thống ActivityLog.'
    )
    TaskComment.objects.create(
        task=t5,
        user=mentor1,
        content='Cần kiểm tra kỹ khả năng thao tác kéo thả trên màn hình thiết bị di động.'
    )

    # 6. CREATE DOCUMENTS
    d1 = Document.objects.create(
        project=proj1,
        uploaded_by=students[0],
        title='Tài liệu Báo cáo Phân tích Yêu cầu SRS',
        file='project_documents/srs_v1.pdf',
        file_type=FileCategory.PDF,
        file_size='2.4 MB',
        description='Tài liệu đặc tả yêu cầu phần mềm chi tiết.',
        current_version=1
    )

    d2 = Document.objects.create(
        project=proj1,
        uploaded_by=students[1],
        title='Sơ đồ Kiến trúc Hệ thống & Database ERD',
        file='project_documents/erd_diagram.png',
        file_type=FileCategory.IMAGE,
        file_size='1.1 MB',
        description='Sơ đồ liên kết thực thể dữ liệu trong hệ thống.',
        current_version=1
    )

    # 7. CREATE FEEDBACKS
    Feedback.objects.create(
        project=proj1,
        task=t2,
        mentor=mentor1,
        content='Sơ đồ CSDL được thiết kế đầy đủ ràng buộc khóa ngoại. Đánh giá hoàn thành tốt.',
        rating=5,
        status=ReviewStatus.APPROVED
    )
    Feedback.objects.create(
        project=proj1,
        task=t5,
        mentor=mentor1,
        content='Bổ sung chỉ báo trạng thái rõ ràng khi người dùng di chuyển các thẻ trên bảng Kanban.',
        rating=4,
        status=ReviewStatus.NEED_REVISION
    )

    # 8. CREATE NOTIFICATIONS
    Notification.objects.create(
        recipient=students[0],
        sender=mentor1,
        title='Phản hồi từ Mentor cho công việc Kanban Board',
        message='PGS.TS Nguyễn Văn Minh đã gửi nhận xét: "Bổ sung chỉ báo trạng thái rõ ràng khi người dùng di chuyển các thẻ trên bảng Kanban."',
        link=f'/projects/{proj1.id}/tasks/',
        notification_type=NotificationType.MENTOR_FEEDBACK
    )
    Notification.objects.create(
        recipient=students[1],
        sender=students[0],
        title='Phân công công việc mới',
        message='Nguyễn Văn Anh đã phân công task "Thiết kế Giao diện Cổng Cổng thông tin Học thuật" cho bạn.',
        link=f'/projects/{proj1.id}/tasks/',
        notification_type=NotificationType.TASK_ASSIGNED
    )
    Notification.objects.create(
        recipient=students[0],
        sender=None,
        title='Nhắc nhở hạn chót Milestone',
        message='Milestone 2 "Phát triển Core Backend & Authentication" có hạn hoàn thành trong 5 ngày tới.',
        link=f'/projects/{proj1.id}/milestones/',
        notification_type=NotificationType.MILESTONE_DUE
    )

    # 9. CREATE AUDIT LOGS
    ActivityLog.objects.create(
        user=admin,
        action=ActionType.LOGIN,
        entity_type='User',
        entity_id=str(admin.id),
        description='Quản trị viên đăng nhập hệ thống.',
        ip_address='127.0.0.1'
    )
    ActivityLog.objects.create(
        user=students[0],
        action=ActionType.CREATE_PROJECT,
        entity_type='Project',
        entity_id=str(proj1.id),
        description=f'Sinh viên {students[0].display_name} khởi tạo đồ án "{proj1.name}".',
        ip_address='127.0.0.1'
    )
    ActivityLog.objects.create(
        user=mentor1,
        action=ActionType.SUBMIT_REVIEW,
        entity_type='Feedback',
        entity_id='1',
        description=f'Mentor {mentor1.display_name} gửi nhận xét đánh giá cho đồ án "{proj1.name}".',
        ip_address='127.0.0.1'
    )

    print(">>> KHOI TAO DU LIEU MAU PORTAL HOC THUAT THANH CONG!")

if __name__ == '__main__':
    run_seed()

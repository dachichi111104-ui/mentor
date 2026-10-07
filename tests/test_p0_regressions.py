from django.test import TestCase
from django.utils import timezone
from accounts.models import User, UserRole, UserStatus
from projects.models import Project, ProjectStatus
from tasks.models import Task, TaskPriority, TaskStatus
from reviews.models import ReviewStatus

class P0RegressionTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(username='p0_student', email='p0@vau.edu.vn', role=UserRole.STUDENT, status=UserStatus.ACTIVE)
        self.mentor = User.objects.create_user(username='p0_mentor', email='p0m@vau.edu.vn', role=UserRole.MENTOR, status=UserStatus.ACTIVE)
        self.project = Project.objects.create(code='PRJ-P0-TEST', name='P0 Test Project', created_by=self.student, mentor=self.mentor,
            start_date=timezone.localdate() - timezone.timedelta(days=10),
            end_date=timezone.localdate() + timezone.timedelta(days=80),
        )

    def test_p0_p0_1(self):
        self.assertEqual(ReviewStatus.NEED_REVISION, 'NEED_REVISION')

    def test_p0_p0_2(self):
        self.assertEqual(self.project.created_by, self.student)

    def test_p0_p0_3(self):
        self.assertTrue(self.mentor.is_active_mentor)

    def test_p0_p0_4(self):
        task = Task.objects.create(project=self.project, title='P0-4 Task', created_by=self.student)
        self.assertEqual(task.status, TaskStatus.TODO)

    def test_p0_p0_5(self):
        self.assertEqual(self.project.status, ProjectStatus.PLANNING)

    def test_p0_p0_6(self):
        self.assertIsNotNone(self.project.created_at)

    def test_p0_p0_7(self):
        self.assertEqual(self.project.code, 'PRJ-P0-TEST')

    def test_p0_p0_8(self):
        self.assertEqual(self.project.progress, 0)

    def test_p0_p0_9(self):
        self.assertEqual(self.project.tasks.count(), 0)

    def test_p0_p0_10(self):
        self.assertEqual(self.project.milestones.count(), 0)

    def test_p0_p0_11(self):
        self.assertEqual(self.student.role, UserRole.STUDENT)

    def test_p0_p0_12(self):
        self.assertEqual(self.mentor.role, UserRole.MENTOR)

    def test_p0_p0_13(self):
        self.assertEqual(self.student.status, UserStatus.ACTIVE)

    def test_p0_p0_14(self):
        self.assertEqual(self.mentor.status, UserStatus.ACTIVE)

    def test_p0_p0_15(self):
        self.assertTrue(hasattr(self.project, 'technology'))

    def test_p0_p0_16(self):
        from projects.forms import ProjectForm
        form = ProjectForm(data={'code': 'PRJ-P0-NEW', 'name': 'New P0 Proj', 'category': 'WEB'})
        self.assertTrue(form.is_valid())

    def test_p0_p0_17(self):
        from tasks.forms import TaskForm
        form = TaskForm(data={'title': 'P0-17 Form Task', 'priority': TaskPriority.HIGH})
        self.assertTrue(form.is_valid())

    def test_p0_p0_18(self):
        from milestones.forms import MilestoneForm
        from django.utils import timezone
        form = MilestoneForm(data={'name': 'P0-18 Milestone', 'start_date': timezone.now().date(), 'due_date': timezone.now().date()})
        self.assertTrue(form.is_valid())

    def test_p0_p0_19(self):
        self.assertIsNotNone(self.project.id)

    def test_p0_p0_20(self):
        self.assertEqual(ProjectStatus.values, ['PLANNING', 'IN_PROGRESS', 'REVIEW', 'COMPLETED', 'ARCHIVED'])

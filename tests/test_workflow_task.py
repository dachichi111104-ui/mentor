from django.test import TestCase
from django.utils import timezone
from accounts.models import User, UserRole, UserStatus
from projects.models import Project, ProjectStatus
from tasks.models import Task, TaskStatus, TaskPriority

_today = None

def _get_today():
    global _today
    if _today is None:
        from django.utils import timezone as tz
        _today = tz.localdate()
    return _today

class TaskWorkflowTestCase(TestCase):
    def setUp(self):
        today = timezone.localdate()
        self.student = User.objects.create_user(username='std1', email='std1@vaa.edu.vn', role=UserRole.STUDENT, status=UserStatus.ACTIVE)
        self.project = Project.objects.create(
            code='PRJ-WF-1', name='Workflow Test Proj', created_by=self.student,
            start_date=today - timezone.timedelta(days=10),
            end_date=today + timezone.timedelta(days=80),
        )

    def test_p0_p0_17_task_creation(self):
        task = Task.objects.create(project=self.project, title='Test Task 1', priority=TaskPriority.HIGH, status=TaskStatus.TODO, created_by=self.student)
        self.assertEqual(task.status, TaskStatus.TODO)
        self.assertEqual(task.title, 'Test Task 1')

    def test_task_status_transition(self):
        task = Task.objects.create(project=self.project, title='Status Task', created_by=self.student)
        task.status = TaskStatus.IN_PROGRESS
        task.save()
        self.assertEqual(task.status, TaskStatus.IN_PROGRESS)

    def test_task_overdue_property(self):
        past = timezone.now().date() - timezone.timedelta(days=2)
        task = Task.objects.create(project=self.project, title='Overdue Task', due_date=past, created_by=self.student)
        self.assertTrue(task.is_overdue)

    def test_task_checklist_items(self):
        task = Task.objects.create(project=self.project, title='Checklist Task', created_by=self.student)
        item1 = task.checklist_items.create(title='Item 1', is_completed=True)
        item2 = task.checklist_items.create(title='Item 2', is_completed=False)
        self.assertEqual(task.checklist_total_count, 2)
        self.assertEqual(task.checklist_done_count, 1)
        self.assertEqual(task.checklist_progress, 50)

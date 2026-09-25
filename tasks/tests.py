from django.test import TestCase
from django.urls import reverse
from accounts.models import User, UserRole
from projects.models import Project, ProjectMember, MemberRole, MentorStatus, MemberStatus
from tasks.models import Task, TaskStatus

class TaskPermissionTests(TestCase):
    def setUp(self):
        self.student1 = User.objects.create_user(username='student1', password='password', role=UserRole.STUDENT)
        self.student2 = User.objects.create_user(username='student2', password='password', role=UserRole.STUDENT)
        self.mentor = User.objects.create_user(username='mentor', password='password', role=UserRole.MENTOR)
        
        self.project = Project.objects.create(
            name='Test Project',
            code='PRJ-TEST',
            description='Test Desc',
            technology='Python',
            start_date='2026-01-01',
            end_date='2026-12-31',
            created_by=self.student1,
            mentor=self.mentor,
            mentor_status=MentorStatus.ACCEPTED
        )
        ProjectMember.objects.create(project=self.project, user=self.student1, role=MemberRole.LEADER, status=MemberStatus.ACCEPTED)
        ProjectMember.objects.create(project=self.project, user=self.student2, role=MemberRole.MEMBER, status=MemberStatus.ACCEPTED)
        
        self.task = Task.objects.create(
            project=self.project,
            title='Sample Task',
            description='Task Description',
            assignee=self.student2,
            created_by=self.student1,
            status=TaskStatus.TODO
        )

    def test_assignee_can_move_task_to_review(self):
        self.client.login(username='student2', password='password')
        url = reverse('task_update_status', args=[self.task.id])
        response = self.client.post(url, {'status': TaskStatus.REVIEW})
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, TaskStatus.REVIEW)

    def test_regular_member_cannot_move_task_to_done(self):
        self.client.login(username='student2', password='password')
        url = reverse('task_update_status', args=[self.task.id])
        response = self.client.post(url, {'status': TaskStatus.DONE})
        self.assertEqual(response.status_code, 403)
        self.task.refresh_from_db()
        self.assertNotEqual(self.task.status, TaskStatus.DONE)

    def test_mentor_can_move_task_to_done(self):
        self.client.login(username='mentor', password='password')
        url = reverse('task_update_status', args=[self.task.id])
        response = self.client.post(url, {'status': TaskStatus.DONE})
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, TaskStatus.DONE)

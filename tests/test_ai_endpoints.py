from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from accounts.models import User, UserRole, UserStatus
from projects.models import Project, ProjectMember, MemberRole, MemberStatus

class AIEndpointsTestCase(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(username='aistd', email='aistd@vaa.edu.vn', role=UserRole.STUDENT, status=UserStatus.ACTIVE)
        self.project = Project.objects.create(code='PRJ-AI-END', name='AI Endpoints Proj', created_by=self.student,
            start_date=timezone.localdate() - timezone.timedelta(days=10),
            end_date=timezone.localdate() + timezone.timedelta(days=80),
        )
        ProjectMember.objects.create(project=self.project, user=self.student, role=MemberRole.LEADER, status=MemberStatus.ACCEPTED)
        self.client.force_login(self.student)

    def test_ai_task_breakdown_endpoint(self):
        url = reverse('ai_task_breakdown')
        res = self.client.post(url, {'project_id': self.project.id})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'success')

    def test_ai_breakdown_alias_endpoint(self):
        res = self.client.post('/ai/breakdown/', {'project_id': self.project.id})
        self.assertEqual(res.status_code, 200)

    def test_ai_weekly_alias_endpoint(self):
        res = self.client.post('/ai/weekly/', {'project_id': self.project.id})
        self.assertEqual(res.status_code, 200)

    def test_ai_risks_alias_endpoint(self):
        res = self.client.post('/ai/risks/', {'project_id': self.project.id})
        self.assertEqual(res.status_code, 200)

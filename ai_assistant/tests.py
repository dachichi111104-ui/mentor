from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, UserRole
from projects.models import Project, ProjectStatus, ProjectCategory, MemberStatus, MentorStatus
from datetime import date, timedelta

class AIAssistantTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='student_ai', password='password123', role=UserRole.STUDENT)
        self.project = Project.objects.create(
            name='AI Test Project',
            code='PROJ-AI-01',
            description='Test AI Description',
            category=ProjectCategory.WEB,
            technology='Python, Django',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status=ProjectStatus.IN_PROGRESS,
            created_by=self.user
        )

    def test_ai_risk_detection_endpoint_returns_success(self):
        self.client.login(username='student_ai', password='password123')
        url = reverse('ai_risk_detection')
        response = self.client.post(url, {'project_id': self.project.id})
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data.get('status'), 'success')
        self.assertIn('risk_html', json_data)

    def test_admin_cannot_access_ai_assistant(self):
        admin = User.objects.create_user(username='admin_ai', password='password123', role=UserRole.ADMIN)
        self.client.login(username='admin_ai', password='password123')
        
        # Test Page GET returns 403
        res_page = self.client.get(reverse('ai_assistant_page'))
        self.assertEqual(res_page.status_code, 403)
        
        # Test AJAX POST returns 403
        res_ajax = self.client.post(reverse('ai_risk_detection'), {'project_id': self.project.id})
        self.assertEqual(res_ajax.status_code, 403)

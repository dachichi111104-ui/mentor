from django.test import TestCase
from django.utils import timezone
from accounts.models import User, UserRole, UserStatus
from projects.models import Project

class AnalyticsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='analytics_user', email='ana@vau.edu.vn', role=UserRole.STUDENT, status=UserStatus.ACTIVE)
        self.project = Project.objects.create(code='PRJ-ANA-1', name='Analytics Proj', created_by=self.user,
            start_date=timezone.localdate() - timezone.timedelta(days=10),
            end_date=timezone.localdate() + timezone.timedelta(days=80),
        )
        self.client.force_login(self.user)

    def test_analytics_page_view(self):
        res = self.client.get('/analytics/')
        self.assertEqual(res.status_code, 200)

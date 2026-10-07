from django.test import TestCase
from django.utils import timezone
from accounts.models import User, UserRole, UserStatus
from projects.models import Project

class BreadcrumbsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='bc_user', email='bc@vau.edu.vn', role=UserRole.STUDENT, status=UserStatus.ACTIVE)
        self.project = Project.objects.create(code='PRJ-BC-1', name='Breadcrumbs Proj', created_by=self.user,
            start_date=timezone.localdate() - timezone.timedelta(days=10),
            end_date=timezone.localdate() + timezone.timedelta(days=80),
        )
        self.client.force_login(self.user)

    def test_breadcrumb_rendering(self):
        res = self.client.get(f'/projects/{self.project.id}/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('breadcrumbs', res.context)
        crumbs = res.context['breadcrumbs']
        self.assertTrue(len(crumbs) >= 2)

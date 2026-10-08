from django.test import TestCase
from django.utils import timezone
from accounts.models import User, UserRole, UserStatus
from projects.models import Project
from documents.models import Document

class SecurityTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='sec1', email='sec1@vaa.edu.vn', role=UserRole.STUDENT, status=UserStatus.ACTIVE)
        self.user2 = User.objects.create_user(username='sec2', email='sec2@vaa.edu.vn', role=UserRole.STUDENT, status=UserStatus.ACTIVE)
        self.project1 = Project.objects.create(code='PRJ-SEC-1', name='Security Proj 1', created_by=self.user1,
            start_date=timezone.localdate() - timezone.timedelta(days=10),
            end_date=timezone.localdate() + timezone.timedelta(days=80),
        )

    def test_unauthorized_document_access(self):
        doc = Document.objects.create(project=self.project1, title='Confidential Doc', uploaded_by=self.user1)
        self.client.force_login(self.user2)
        res = self.client.get(f'/documents/{doc.id}/view/')
        self.assertEqual(res.status_code, 403)

    def test_ratelimit_decorator_exists(self):
        from core.ratelimit import ratelimit
        self.assertTrue(callable(ratelimit))

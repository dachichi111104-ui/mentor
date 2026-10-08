from django.test import TestCase
from accounts.models import User, UserRole, UserStatus

class AccountsApprovalTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='admin_app', email='admin@vaa.edu.vn', password='pass')
        self.pending_mentor = User.objects.create_user(username='pending_m', email='pm@vaa.edu.vn', role=UserRole.MENTOR, status=UserStatus.PENDING_APPROVAL)

    def test_mentor_pending_status(self):
        self.assertEqual(self.pending_mentor.status, UserStatus.PENDING_APPROVAL)
        self.assertFalse(self.pending_mentor.is_active_mentor)

    def test_admin_approves_mentor(self):
        self.pending_mentor.status = UserStatus.ACTIVE
        self.pending_mentor.save()
        self.assertTrue(self.pending_mentor.is_active_mentor)

    def test_admin_rejects_mentor(self):
        self.pending_mentor.status = UserStatus.SUSPENDED
        self.pending_mentor.save()
        self.assertEqual(self.pending_mentor.status, UserStatus.SUSPENDED)
        self.assertFalse(self.pending_mentor.is_active_mentor)

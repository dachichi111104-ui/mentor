from django.test import TestCase
from accounts.models import UserRole
from notifications.models import Notification, NotificationType
from notifications.services import notify
from tests.factories import create_test_user, create_test_project

class RealtimeNotificationTestCase(TestCase):
    def setUp(self):
        self.user_a = create_test_user("user_rt_a", role=UserRole.STUDENT)
        self.user_b = create_test_user("user_rt_b", role=UserRole.STUDENT)
        self.project = create_test_project("PRJ-RT", created_by=self.user_a)

    def test_notify_service_creation_and_dedupe(self):
        """notify() creates Notification object and deduplicates correctly."""
        n1 = notify(
            recipient=self.user_b,
            sender=self.user_a,
            title="Notification 1",
            message="Test Message 1",
            notification_type=NotificationType.SYSTEM,
            project=self.project,
            dedupe_key="dedupe:12345"
        )
        self.assertIsNotNone(n1)
        self.assertEqual(Notification.objects.filter(recipient=self.user_b).count(), 1)

        # Duplicate call with same dedupe_key should be ignored
        n2 = notify(
            recipient=self.user_b,
            sender=self.user_a,
            title="Notification 1 Duplicate",
            message="Test Message 1 Duplicate",
            notification_type=NotificationType.SYSTEM,
            project=self.project,
            dedupe_key="dedupe:12345"
        )
        self.assertIsNone(n2)
        self.assertEqual(Notification.objects.filter(recipient=self.user_b).count(), 1)

    def test_unread_count_ajax_endpoint(self):
        """Unread count AJAX endpoint returns integer count."""
        notify(
            recipient=self.user_b,
            sender=self.user_a,
            title="Unread 1",
            message="Unread Message",
            notification_type=NotificationType.SYSTEM
        )
        self.client.force_login(self.user_b)
        response = self.client.get('/notifications/unread-count/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('unread_count', data)
        self.assertGreaterEqual(data['unread_count'], 1)

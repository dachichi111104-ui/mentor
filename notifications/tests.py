from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, UserRole
from notifications.models import Notification

class NotificationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='user_notif', password='password123', role=UserRole.STUDENT)
        Notification.objects.create(
            recipient=self.user,
            title='Test Notification',
            message='Test Content',
            is_read=False
        )

    def test_unread_count_ajax(self):
        self.client.login(username='user_notif', password='password123')
        url = reverse('notification_unread_count')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data.get('status'), 'success')
        self.assertEqual(json_data.get('unread_count'), 1)

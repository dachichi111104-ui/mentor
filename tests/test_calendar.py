from django.test import TestCase
from django.utils import timezone
from accounts.models import User, UserRole, UserStatus
from projects.models import Project
from milestones.models import Event, EventType, Milestone

class CalendarTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='caluser', email='cal@vau.edu.vn', role=UserRole.STUDENT, status=UserStatus.ACTIVE)
        self.project = Project.objects.create(code='PRJ-CAL-1', name='Calendar Proj', created_by=self.user,
            start_date=timezone.localdate() - timezone.timedelta(days=10),
            end_date=timezone.localdate() + timezone.timedelta(days=80),
        )
        self.client.force_login(self.user)

    def test_calendar_page_view(self):
        res = self.client.get('/calendar/')
        self.assertEqual(res.status_code, 200)

    def test_calendar_events_json_api(self):
        Event.objects.create(project=self.project, title='Test Meeting', event_type=EventType.MEETING, start=timezone.now(), created_by=self.user)
        res = self.client.get('/api/v1/calendar/events/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(len(data['events']) >= 1)

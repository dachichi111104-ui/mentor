from django.test import TestCase
from accounts.models import UserRole
from projects.models import MentorStatus
from tests.factories import create_test_user, create_test_project

class UICalendarTestCase(TestCase):
    def setUp(self):
        self.leader = create_test_user("leader_cal", role=UserRole.STUDENT)
        self.mentor = create_test_user("mentor_cal", role=UserRole.MENTOR)
        self.project = create_test_project("PRJ-CAL", created_by=self.leader, mentor=self.mentor, mentor_status=MentorStatus.ACCEPTED)

    def test_calendar_page_and_navigation(self):
        self.client.force_login(self.leader)
        response = self.client.get('/calendar/?month=2026-10')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tháng 10, 2026')
        self.assertContains(response, 'month=2026-09')
        self.assertContains(response, 'month=2026-11')

    def test_calendar_events_json(self):
        self.client.force_login(self.leader)
        response = self.client.get('/api/v1/calendar/events/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')

    def test_event_create_flow(self):
        self.client.force_login(self.leader)
        response = self.client.post('/calendar/events/create/', {
            'project_id': self.project.id,
            'title': 'Họp Review Sprint 1',
            'event_type': 'MEETING',
            'start': '2026-10-15T09:00'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.project.events.filter(title='Họp Review Sprint 1').exists())

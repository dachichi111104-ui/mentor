import os
from django.test import TestCase
from django.core.management import call_command
from accounts.models import User
from projects.models import Project
from milestones.models import Milestone, Event
from dashboard.models import TimeLog

class SeedDemoTestCase(TestCase):
    def test_seed_demo_command(self):
        """seed_demo populates demo users, projects, milestones, timelogs, and events."""
        os.environ['SEED_DEMO'] = '1'
        try:
            call_command('seed_demo')
            self.assertTrue(User.objects.filter(username='admin').exists())
            self.assertTrue(Project.objects.filter(code='PRJ-2026-AI').exists())
            self.assertGreaterEqual(User.objects.filter(role='STUDENT').count(), 12)
            self.assertGreaterEqual(Milestone.objects.count(), 5)
            self.assertGreaterEqual(Event.objects.count(), 1)
            self.assertGreaterEqual(TimeLog.objects.count(), 1)
        finally:
            os.environ.pop('SEED_DEMO', None)


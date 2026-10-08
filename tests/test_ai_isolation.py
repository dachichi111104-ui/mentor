from django.test import TestCase
from django.utils import timezone
from accounts.models import User, UserRole, UserStatus
from projects.models import Project
from ai_assistant.facts_builder import build_facts

class AIIsolationTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='u1', email='u1@vaa.edu.vn', role=UserRole.STUDENT)
        self.user2 = User.objects.create_user(username='u2', email='u2@vaa.edu.vn', role=UserRole.STUDENT)
        self.p1 = Project.objects.create(code='PRJ-ISO-1', name='Proj 1', created_by=self.user1,
            start_date=timezone.localdate() - timezone.timedelta(days=10),
            end_date=timezone.localdate() + timezone.timedelta(days=80),
        )
        self.p2 = Project.objects.create(code='PRJ-ISO-2', name='Proj 2', created_by=self.user2,
            start_date=timezone.localdate() - timezone.timedelta(days=10),
            end_date=timezone.localdate() + timezone.timedelta(days=80),
        )

        self.p1.tasks.create(title='P1 Secret Task', created_by=self.user1)
        self.p2.tasks.create(title='P2 Secret Task', created_by=self.user2)

    def test_facts_isolation(self):
        facts1 = build_facts(self.p1)
        facts2 = build_facts(self.p2)

        self.assertEqual(facts1['project']['code'], 'PRJ-ISO-1')
        self.assertEqual(facts2['project']['code'], 'PRJ-ISO-2')

        p1_task_titles = [t['title'] for t in facts1['tasks']['todo'] + facts1['tasks']['in_progress']]
        self.assertIn('P1 Secret Task', p1_task_titles)
        self.assertNotIn('P2 Secret Task', p1_task_titles)

from django.test import TestCase
from accounts.models import UserRole
from projects.models import MentorStatus
from ai_assistant.facts_builder import build_facts
from ai_assistant.engine.service import run_task
from ai_assistant.engine.rules import calculate_metrics
from tests.factories import create_test_user, create_test_project

class AIEngineTestCase(TestCase):
    def setUp(self):
        self.leader = create_test_user("leader_ai", role=UserRole.STUDENT)
        self.mentor = create_test_user("mentor_ai", role=UserRole.MENTOR)

        self.project_a = create_test_project("PRJ-AI-A", created_by=self.leader, mentor=self.mentor)
        self.project_b = create_test_project("PRJ-AI-B", created_by=self.leader, mentor=self.mentor)

        self.project_a.technology = "Flutter, Mobile, Dart"
        self.project_a.category = "MOBILE"
        self.project_a.save()

        self.project_b.technology = "Django, PostgreSQL, Python"
        self.project_b.category = "WEB"
        self.project_b.save()

    def test_ai_isolation(self):
        """Fact pack for Project A contains only Project A data."""
        facts_a = build_facts(self.project_a)
        facts_b = build_facts(self.project_b)

        self.assertEqual(facts_a['project']['code'], "PRJ-AI-A")
        self.assertEqual(facts_b['project']['code'], "PRJ-AI-B")

        res_a = run_task("breakdown", facts_a)
        res_b = run_task("breakdown", facts_b)

        self.assertEqual(res_a['status'], 'FALLBACK')
        self.assertEqual(res_b['status'], 'FALLBACK')

        tasks_a = [t['title'] for t in res_a['data']['tasks']]
        tasks_b = [t['title'] for t in res_b['data']['tasks']]

        # Titles for Mobile vs Web differ
        self.assertNotEqual(tasks_a, tasks_b)

    def test_metrics_calculation(self):
        """Metrics calculation produces valid scores and levels."""
        facts_a = build_facts(self.project_a)
        metrics = calculate_metrics(facts_a)

        self.assertIn('risk_score', metrics)
        self.assertIn('risk_level', metrics)
        self.assertGreaterEqual(metrics['risk_score'], 0)
        self.assertLessEqual(metrics['risk_score'], 100)

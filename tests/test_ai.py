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

        self.assertIn(res_a['status'], ['SUCCESS', 'FALLBACK'])
        self.assertIn(res_b['status'], ['SUCCESS', 'FALLBACK'])

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

    def test_ai_client_fallback(self):
        """AIClient falls back to in-process execution when service is not configured."""
        from ai_assistant.client import AIClient
        client = AIClient()
        facts_a = build_facts(self.project_a)
        res = client.run_task("breakdown", facts_a)
        self.assertIn('status', res)
        self.assertIn(res['source'], ['llm', 'rules'])

    def test_llm_circuit_breaker_and_cache(self):
        """LLMClient respects circuit breaker and cache keys."""
        from ai_assistant.engine.llm import LLMClient
        from django.core.cache import cache

        client = LLMClient()
        cache_key = "ai:test_task:12345"
        cache.set(cache_key, {'text': '{"test": true}', 't_in': 10, 't_out': 20}, timeout=600)

        text, t_in, t_out = client.complete("test prompt", cache_key=cache_key)
        self.assertEqual(text, '{"test": true}')
        self.assertEqual(t_in, 10)
        self.assertEqual(t_out, 20)

    def test_ai_propose_and_apply_flow(self):
        """Students propose tasks, and leader/admin applies or rejects them."""
        self.client.force_login(self.leader)
        response = self.client.post('/ai/propose/', {
            'project_id': self.project_a.id,
            'kind': 'task_breakdown',
            'payload': '{"tasks": [{"title": "Task AI 1", "priority": "HIGH"}]}'
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        proposal_id = data['proposal_id']

        # Apply proposal as leader
        response = self.client.post(f'/ai/proposals/{proposal_id}/apply/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertTrue(self.project_a.tasks.filter(title="Task AI 1").exists())

    def test_ai_history_and_overview_api(self):
        """Endpoints return JSON list for visible projects."""
        self.client.force_login(self.leader)
        res_h = self.client.get('/ai/history/')
        self.assertEqual(res_h.status_code, 200)
        self.assertEqual(res_h.json()['status'], 'success')

        res_o = self.client.get('/ai/overview/')
        self.assertEqual(res_o.status_code, 200)
        self.assertEqual(res_o.json()['status'], 'success')


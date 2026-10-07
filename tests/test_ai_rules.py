from django.test import TestCase
from django.utils import timezone
from ai_assistant.engine.rules import calculate_metrics, PHASES, QUESTION_BANK

class AIRulesTestCase(TestCase):
    def test_calculate_metrics_empty(self):
        facts = {'project': {'progress': 50, 'elapsed_pct': 50, 'category': 'WEB'}, 'tasks': {}, 'milestones': []}
        metrics = calculate_metrics(facts)
        self.assertIn('risk_score', metrics)
        self.assertIn('risks', metrics)

    def test_phases_categories(self):
        self.assertIn('WEB', PHASES)
        self.assertIn('MOBILE', PHASES)
        self.assertIn('AI_ML', PHASES)

    def test_question_bank(self):
        self.assertTrue(len(QUESTION_BANK) >= 5)

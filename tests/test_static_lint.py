from django.test import TestCase
import subprocess
import os

class StaticLintTestCase(TestCase):
    def test_lint_enums_script(self):
        res = subprocess.run(['python', 'scripts/lint_enums.py'], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

    def test_lint_views_script(self):
        res = subprocess.run(['python', 'scripts/lint_views.py'], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

    def test_lint_templates_script(self):
        res = subprocess.run(['python', 'scripts/lint_templates.py'], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

    def test_lint_ai_prompts_script(self):
        res = subprocess.run(['python', 'scripts/lint_ai_prompts.py'], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

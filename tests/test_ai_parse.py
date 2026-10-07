from django.test import TestCase
from django.utils import timezone
from ai_assistant.engine.parse import extract_json_block

class AIParseTestCase(TestCase):
    def test_extract_json_block_raw_json(self):
        raw = '{"tasks": [{"title": "Task 1"}]}'
        self.assertEqual(extract_json_block(raw), raw)

    def test_extract_json_block_markdown_wrapper(self):
        raw = '```json\n{"tasks": [{"title": "Task 1"}]}\n```'
        self.assertEqual(extract_json_block(raw), '{"tasks": [{"title": "Task 1"}]}')

    def test_extract_json_block_embedded_text(self):
        raw = 'Here is the result:\n{"status": "ok"}\nHope this helps!'
        self.assertEqual(extract_json_block(raw), '{"status": "ok"}')

    def test_extract_json_block_empty(self):
        self.assertEqual(extract_json_block(''), '')

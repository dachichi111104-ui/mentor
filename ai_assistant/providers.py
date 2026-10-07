import os
import json
import logging
from ai_assistant.engine.llm import LLMClient

logger = logging.getLogger(__name__)

class LLMProvider:
    @staticmethod
    def get_configured_provider():
        client = LLMClient()
        if client.is_configured():
            return client.provider, client.model, "configured"
        return 'rules', 'rules-engine', None

    @staticmethod
    def parse_json_safely(raw_text):
        if not raw_text:
            return None
        text = raw_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)
        except Exception:
            import re
            json_match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except Exception:
                    pass
        return None

    @classmethod
    def call(cls, prompt, system_prompt=""):
        client = LLMClient()
        if client.is_configured():
            try:
                full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                text, _, _ = client.complete(full_prompt)
                return text, f"{client.provider.capitalize()} ({client.model})"
            except Exception as exc:
                logger.warning(f"LLM call failed: {exc}")

        return None, "System Rules Engine"


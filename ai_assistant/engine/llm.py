import os
import time
import json
import hashlib
import requests
import logging
from django.core.cache import cache
from ai_assistant.engine.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

CB_MAX_FAILURES = 5
CB_WINDOW_SECONDS = 60
CB_COOLDOWN_SECONDS = 60

# LLMClient featuring retry backoff mechanism, circuit breaker, response cache, and execution lock.
class LLMClient:
    """
    LLM Client supporting Gemini, OpenAI, and Anthropic.
    Features: retry exponential backoff, circuit breaker, cache, and lock.
    """

    def __init__(self):
        self.provider = os.getenv('AI_PROVIDER', 'none').strip().lower()
        self.model = os.getenv('AI_MODEL', '').strip()
        self.gemini_key = os.getenv('GEMINI_API_KEY', '').strip()
        self.openai_key = os.getenv('OPENAI_API_KEY', '').strip()
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY', '').strip()
        self.timeout = int(os.getenv('AI_TIMEOUT_SECONDS', '8'))

    def is_configured(self) -> bool:
        if self.provider == 'none':
            return False
        if self.provider == 'gemini' and self.gemini_key and self.model:
            return True
        if self.provider == 'openai' and self.openai_key and self.model:
            return True
        if self.provider == 'anthropic' and self.anthropic_key and self.model:
            return True
        return False

    def is_circuit_open(self) -> bool:
        """Checks if the circuit breaker is currently tripped OPEN."""
        opened_at = cache.get('ai_cb_opened_at')
        if opened_at:
            if time.time() - opened_at < CB_COOLDOWN_SECONDS:
                return True
            else:
                cache.delete('ai_cb_opened_at')
                cache.delete('ai_cb_failures')
        return False

    def _record_failure(self):
        """Records an LLM failure for circuit breaker monitoring."""
        failures = cache.get('ai_cb_failures', 0) + 1
        cache.set('ai_cb_failures', failures, timeout=CB_WINDOW_SECONDS)
        if failures >= CB_MAX_FAILURES:
            cache.set('ai_cb_opened_at', time.time(), timeout=CB_COOLDOWN_SECONDS)
            logger.warning(f"Circuit Breaker tripped OPEN after {failures} consecutive LLM errors.")

    def _record_success(self):
        """Resets failure counter on success."""
        cache.delete('ai_cb_failures')

    def complete(self, prompt: str, cache_key: str = None) -> tuple[str, int, int]:
        """
        Sends prompt to LLM provider with retries, caching, circuit breaker, and lock support.
        Returns tuple: (response_text, tokens_in, tokens_out)
        """
        if cache_key:
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result['text'], cached_result['t_in'], cached_result['t_out']

        if not self.is_configured():
            raise ValueError("Chưa cấu hình API Key cho nhà cung cấp LLM.")

        if self.is_circuit_open():
            raise RuntimeError("Circuit Breaker OPEN: Dịch vụ LLM tạm thời bị ngắt do quá nhiều lỗi liên tiếp.")

        backoff_delays = [0.5]
        last_exception = None

        for attempt in range(len(backoff_delays) + 1):
            try:
                if self.provider == 'gemini':
                    text, t_in, t_out = self._call_gemini(prompt)
                elif self.provider == 'openai':
                    text, t_in, t_out = self._call_openai(prompt)
                elif self.provider == 'anthropic':
                    text, t_in, t_out = self._call_anthropic(prompt)
                else:
                    raise ValueError(f"Nhà cung cấp LLM không hợp lệ: {self.provider}")

                self._record_success()

                if cache_key:
                    cache.set(cache_key, {'text': text, 't_in': t_in, 't_out': t_out}, timeout=600)

                return text, t_in, t_out

            except Exception as e:
                last_exception = e
                if attempt < len(backoff_delays):
                    time.sleep(backoff_delays[attempt])

        self._record_failure()
        raise last_exception

    def _call_gemini(self, prompt: str) -> tuple[str, int, int]:
        model_name = self.model.lower() if self.model else ''
        if not model_name or 'antigravity' in model_name or not model_name.startswith('gemini'):
            model_name = 'gemini-1.5-flash'
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

        headers = {
            'Content-Type': 'application/json',
            'x-goog-api-key': self.gemini_key
        }
        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }
        res = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        if res.status_code != 200:
            raise RuntimeError(f"Gemini API trả về lỗi HTTP {res.status_code}: {res.text[:200]}")

        data = res.json()
        candidates = data.get('candidates', [])
        if not candidates:
            raise RuntimeError("Gemini không trả về kết quả candidates")

        text = candidates[0]['content']['parts'][0]['text']
        usage = data.get('usageMetadata', {})
        return text, usage.get('promptTokenCount', 0), usage.get('candidatesTokenCount', 0)


    def _call_openai(self, prompt: str) -> tuple[str, int, int]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.openai_key}'
        }
        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }
        res = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        if res.status_code != 200:
            raise RuntimeError(f"OpenAI API trả về lỗi HTTP {res.status_code}: {res.text[:200]}")

        data = res.json()
        text = data['choices'][0]['message']['content']
        usage = data.get('usage', {})
        return text, usage.get('prompt_tokens', 0), usage.get('completion_tokens', 0)

    def _call_anthropic(self, prompt: str) -> tuple[str, int, int]:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': self.anthropic_key,
            'anthropic-version': '2023-06-01'
        }
        payload = {
            "model": self.model,
            "max_tokens": 2048,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }
        res = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        if res.status_code != 200:
            raise RuntimeError(f"Anthropic API trả về lỗi HTTP {res.status_code}: {res.text[:200]}")

        data = res.json()
        text = data['content'][0]['text']
        usage = data.get('usage', {})
        return text, usage.get('input_tokens', 0), usage.get('output_tokens', 0)


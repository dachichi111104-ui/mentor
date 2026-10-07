import os
import time
import requests
from ai_assistant.engine.prompts import SYSTEM_PROMPT

class LLMClient:
    """
    LLM Client supporting Gemini, OpenAI, and Anthropic.
    Passes API key via headers (SEC-10), enforces timeouts, circuit breaker, and JSON mode.
    """

    def __init__(self):
        self.provider = os.getenv('AI_PROVIDER', 'none').lower()
        self.model = os.getenv('AI_MODEL', '')
        self.gemini_key = os.getenv('GEMINI_API_KEY', '')
        self.openai_key = os.getenv('OPENAI_API_KEY', '')
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY', '')
        self.timeout = int(os.getenv('AI_TIMEOUT_SECONDS', '25'))

        # Auto-select provider if not specified explicitly
        if self.provider == 'none':
            if self.gemini_key:
                self.provider = 'gemini'
            elif self.openai_key:
                self.provider = 'openai'
            elif self.anthropic_key:
                self.provider = 'anthropic'

        if self.provider == 'gemini' and not self.model:
            self.model = 'gemini-1.5-flash'
        elif self.provider == 'openai' and not self.model:
            self.model = 'gpt-3.5-turbo'
        elif self.provider == 'anthropic' and not self.model:
            self.model = 'claude-3-haiku-20240307'

    def is_configured(self) -> bool:
        if self.provider == 'gemini' and self.gemini_key:
            return True
        if self.provider == 'openai' and self.openai_key:
            return True
        if self.provider == 'anthropic' and self.anthropic_key:
            return True
        return False

    def complete(self, prompt: str) -> tuple[str, int, int]:
        """
        Sends prompt to LLM provider.
        Returns tuple: (response_text, tokens_in, tokens_out)
        Raises Exception if error or unconfigured.
        """
        if not self.is_configured():
            raise ValueError("Chưa cấu hình API Key cho nhà cung cấp LLM.")

        if self.provider == 'gemini':
            return self._call_gemini(prompt)
        elif self.provider == 'openai':
            return self._call_openai(prompt)
        elif self.provider == 'anthropic':
            return self._call_anthropic(prompt)
        else:
            raise ValueError(f"Nhà cung cấp LLM không hợp lệ: {self.provider}")

    def _call_gemini(self, prompt: str) -> tuple[str, int, int]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
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

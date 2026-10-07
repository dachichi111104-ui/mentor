import os
import json
import urllib.request
import urllib.error
from django.conf import settings

class LLMProvider:
    @staticmethod
    def get_configured_provider():
        provider = os.getenv('AI_PROVIDER', 'pollinations').lower()
        model = os.getenv('AI_MODEL', 'gemini-1.5-flash')
        gemini_key = os.getenv('GEMINI_API_KEY')
        openai_key = os.getenv('OPENAI_API_KEY')
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')

        if gemini_key:
            return 'gemini', model, gemini_key
        elif openai_key:
            return 'openai', model or 'gpt-3.5-turbo', openai_key
        elif anthropic_key:
            return 'anthropic', model or 'claude-3-haiku-20240307', anthropic_key
        return 'pollinations', 'pollinations-free', None

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
            # Try to extract first array or object if surrounded by prose
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
        provider, model, api_key = cls.get_configured_provider()
        
        # 1. Gemini API
        if provider == 'gemini' and api_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                payload = {
                    "contents": [{"parts": [{"text": f"{system_prompt}\n\n{prompt}"}]}]
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=20) as resp:
                    result = json.loads(resp.read().decode('utf-8'))
                    text = result['candidates'][0]['content']['parts'][0]['text']
                    return text, f"Gemini ({model})"
            except Exception as e:
                pass

        # 2. OpenAI API
        if provider == 'openai' and api_key:
            try:
                url = "https://api.openai.com/v1/chat/completions"
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
                )
                with urllib.request.urlopen(req, timeout=20) as resp:
                    result = json.loads(resp.read().decode('utf-8'))
                    text = result['choices'][0]['message']['content']
                    return text, f"OpenAI ({model})"
            except Exception as e:
                pass

        # 3. Pollinations Free API (Default Fallback Network Provider)
        try:
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            url = "https://text.pollinations.ai/"
            payload = {
                "messages": [
                    {"role": "system", "content": system_prompt or "You are an academic project AI assistant."},
                    {"role": "user", "content": prompt}
                ],
                "model": "openai"
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                text = resp.read().decode('utf-8')
                if text:
                    return text, "Pollinations Free LLM"
        except Exception:
            pass

        return None, "System Rules Engine"

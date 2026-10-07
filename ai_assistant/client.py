import os
import requests
import logging
from ai_assistant.engine.service import run_task as inprocess_run_task

logger = logging.getLogger(__name__)

class AIClient:
    """
    Client for interacting with the FastAPI AI microservice,
    with automatic fallback to in-process execution.
    """

    def __init__(self):
        self.base_url = os.getenv('AI_SERVICE_URL', '').rstrip('/')
        self.token = os.getenv('AI_SERVICE_TOKEN', '')

    def is_service_configured(self) -> bool:
        return bool(self.base_url and self.token)

    def run_task(self, prompt_type: str, facts: dict, user_message: str = "") -> dict:
        if self.is_service_configured():
            endpoint_map = {
                'breakdown': '/v1/breakdown',
                'risks': '/v1/risks',
                'weekly': '/v1/weekly',
                'questions': '/v1/questions',
                'chat': '/v1/chat',
            }
            path = endpoint_map.get(prompt_type)
            if path:
                try:
                    url = f"{self.base_url}{path}"
                    headers = {
                        'Authorization': f'Bearer {self.token}',
                        'Content-Type': 'application/json',
                    }
                    payload = {'facts': facts, 'user_message': user_message}
                    resp = requests.post(url, json=payload, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        return resp.json()
                    logger.warning(f"AI Microservice returned HTTP {resp.status_code}: {resp.text[:200]}")
                except Exception as exc:
                    logger.warning(f"Failed to call AI microservice at {self.base_url}: {exc}")

        # Fallback to in-process Python execution
        return inprocess_run_task(prompt_type, facts, user_message=user_message)

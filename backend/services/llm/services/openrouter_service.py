from typing import Any, Dict

import requests

from config import settings
from prompts import build_system_prompt
from utils.json_utils import extract_json_object


class OpenRouterParserService:
    def __init__(self) -> None:
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.api_key = settings.OPENROUTER_API_KEY
        self.site_url = getattr(settings, "OPENROUTER_SITE_URL", "")
        self.site_name = getattr(settings, "OPENROUTER_SITE_NAME", "")

    def parse_user_request(
        self, user_message: str, model: str | None = None
    ) -> Dict[str, Any]:
        selected_model = model or settings.OPENROUTER_DEFAULT_MODEL
        system_prompt = build_system_prompt()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if self.site_url:
            headers["HTTP-Referer"] = self.site_url

        if self.site_name:
            headers["X-OpenRouter-Title"] = self.site_name

        payload = {
            "model": selected_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"OpenRouter request failed: {exc}") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError("OpenRouter returned a non-JSON response") from exc

        if response.status_code != 200:
            raise RuntimeError(f"OpenRouter response error: {data}")

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Malformed OpenRouter response") from exc

        return extract_json_object(content)
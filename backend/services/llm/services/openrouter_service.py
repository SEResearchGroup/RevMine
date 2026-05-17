import logging
import time
from typing import Any, Dict

import requests

from config import settings
from prompts import build_system_prompt
from utils.json_utils import extract_json_object

logger = logging.getLogger(__name__)


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
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required for OpenRouter inference")
        system_prompt = build_system_prompt()
        _start = time.monotonic()

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

        logger.info(
            "OpenRouter inference started",
            extra={
                "model": selected_model,
                "prompt_length": len(user_message),
                "event": "llm_inference_started",
                "provider": "openrouter",
                "status": "started",
            },
        )

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60,
            )
        except requests.RequestException as exc:
            _duration = round(time.monotonic() - _start, 3)
            logger.error(
                "OpenRouter request failed",
                extra={
                    "model": selected_model,
                    "duration": _duration,
                    "error": str(exc),
                    "status": "failed",
                    "event": "llm_inference_failed",
                    "provider": "openrouter",
                },
            )
            raise RuntimeError(f"OpenRouter request failed: {exc}") from exc

        try:
            data = response.json()
        except ValueError as exc:
            _duration = round(time.monotonic() - _start, 3)
            logger.error(
                "OpenRouter returned non-JSON response",
                extra={
                    "model": selected_model,
                    "duration": _duration,
                    "status_code": response.status_code,
                    "status": "failed",
                    "event": "llm_inference_failed",
                    "provider": "openrouter",
                },
            )
            raise RuntimeError("OpenRouter returned a non-JSON response") from exc

        if response.status_code != 200:
            _duration = round(time.monotonic() - _start, 3)
            logger.error(
                "OpenRouter returned error status",
                extra={
                    "model": selected_model,
                    "duration": _duration,
                    "status_code": response.status_code,
                    "response_body": str(data)[:500],
                    "status": "failed",
                    "event": "llm_inference_failed",
                    "provider": "openrouter",
                },
            )
            raise RuntimeError(f"OpenRouter response error: {data}")

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Malformed OpenRouter response") from exc

        _duration = round(time.monotonic() - _start, 3)
        logger.info(
            "OpenRouter inference completed",
            extra={
                "model": selected_model,
                "duration": _duration,
                "response_length": len(content),
                "status": "success",
                "event": "llm_inference_completed",
                "provider": "openrouter",
                "tokens_used": data.get("usage", {}).get("total_tokens"),
                "prompt_tokens": data.get("usage", {}).get("prompt_tokens"),
                "completion_tokens": data.get("usage", {}).get("completion_tokens"),
            },
        )
        return extract_json_object(content)

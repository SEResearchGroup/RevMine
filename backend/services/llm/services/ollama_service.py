import logging
import time
from typing import Any, Dict

from ollama import Client
from ollama._types import ResponseError

from config import settings
from prompts import build_system_prompt
from utils.json_utils import extract_json_object

logger = logging.getLogger(__name__)


class OllamaParserService:
    def __init__(self) -> None:
        if not settings.OLLAMA_HOST:
            raise RuntimeError("OLLAMA_HOST is required for Ollama inference")
        self.client = Client(host=settings.OLLAMA_HOST)

    def parse_user_request(
        self, user_message: str, model: str | None = None
    ) -> Dict[str, Any]:
        selected_model = model or settings.DEFAULT_MODEL
        system_prompt = build_system_prompt()
        _start = time.monotonic()

        logger.info(
            "Ollama inference started",
            extra={
                "model": selected_model,
                "prompt_length": len(user_message),
                "event": "llm_inference_started",
                "provider": "ollama",
                "status": "started",
            },
        )

        try:
            response = self.client.chat(
                model=selected_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                format="json",
                options={"temperature": 0},
            )
        except ResponseError as exc:
            _duration = round(time.monotonic() - _start, 3)
            logger.error(
                "Ollama inference failed – ResponseError",
                extra={
                    "model": selected_model,
                    "duration": _duration,
                    "error": str(exc),
                    "status": "failed",
                    "event": "llm_inference_failed",
                    "provider": "ollama",
                },
            )
            raise
        except Exception as exc:
            _duration = round(time.monotonic() - _start, 3)
            logger.error(
                "Ollama inference failed – unexpected error",
                extra={
                    "model": selected_model,
                    "duration": _duration,
                    "error": str(exc),
                    "status": "failed",
                    "event": "llm_inference_failed",
                    "provider": "ollama",
                },
            )
            raise RuntimeError(f"Unexpected Ollama error: {exc}") from exc

        _duration = round(time.monotonic() - _start, 3)
        content = response["message"]["content"]
        logger.info(
            "Ollama inference completed",
            extra={
                "model": selected_model,
                "duration": _duration,
                "response_length": len(content),
                "status": "success",
                "event": "llm_inference_completed",
                "provider": "ollama",
            },
        )
        return extract_json_object(content)

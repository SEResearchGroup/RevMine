from typing import Any, Dict

from ollama import Client
from ollama._types import ResponseError

from config import settings
from prompts import build_system_prompt
from utils.json_utils import extract_json_object


class OllamaParserService:
    def __init__(self) -> None:
        self.client = Client()

    def parse_user_request(
        self, user_message: str, model: str | None = None
    ) -> Dict[str, Any]:
        selected_model = model or settings.DEFAULT_MODEL
        system_prompt = build_system_prompt()

        try:
            response = self.client.chat(
                model=selected_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                options={"temperature": 0},
            )
        except ResponseError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Unexpected Ollama error: {exc}") from exc

        content = response["message"]["content"]
        return extract_json_object(content)

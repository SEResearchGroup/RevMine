"""
Code Generation Agent
=====================
Generates a Python code snippet from a natural-language analysis request
when the DSL is insufficient.

Usage:
    agent = CodeGenerationAgent(backend="openrouter")
    code = agent.generate(
        user_message="Defect rate per author",
        available_columns=["Author", "#Comments", "#Commits", ...],
        model="openai/gpt-4o-mini",
    )
    # Returns: plain Python string or {"error": "...", "reason": "..."}
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from config import settings
from prompts_code import build_code_system_prompt

logger = logging.getLogger(__name__)


class CodeGenerationAgent:

    def __init__(self, backend: str = "openrouter"):
        if backend not in ("openrouter", "ollama"):
            raise ValueError(f"Unknown backend '{backend}'.")
        self._backend = backend

    def generate(
        self,
        user_message: str,
        available_columns: Optional[List[str]] = None,
        model: Optional[str] = None,
    ) -> str:
        """Return raw Python code string, or raise RuntimeError on failure."""
        system_prompt = build_code_system_prompt(available_columns or [])
        t0 = time.monotonic()

        if self._backend == "openrouter":
            code = self._call_openrouter(user_message, system_prompt, model)
        else:
            code = self._call_ollama(user_message, system_prompt, model)

        duration = round(time.monotonic() - t0, 3)
        logger.info("Python code generated", extra={
            "event": "code_generated",
            "backend": self._backend,
            "model": model,
            "duration": duration,
            "code_length": len(code),
        })
        return code

    def _call_openrouter(self, user_message: str, system_prompt: str, model: Optional[str]) -> str:
        import requests as req

        selected_model = model or settings.OPENROUTER_DEFAULT_MODEL
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        if getattr(settings, "OPENROUTER_SITE_URL", None):
            headers["HTTP-Referer"] = settings.OPENROUTER_SITE_URL
        if getattr(settings, "OPENROUTER_SITE_NAME", None):
            headers["X-OpenRouter-Title"] = settings.OPENROUTER_SITE_NAME

        payload = {
            "model": selected_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            "temperature": 0,
        }

        try:
            resp = req.post(url, json=payload, headers=headers, timeout=90)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return self._clean_code(content)
        except req.exceptions.RequestException as exc:
            raise RuntimeError(f"OpenRouter request failed: {exc}") from exc
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"Unexpected OpenRouter response: {exc}") from exc

    def _call_ollama(self, user_message: str, system_prompt: str, model: Optional[str]) -> str:
        try:
            import ollama as ollama_client
        except ImportError:
            raise RuntimeError("ollama package not installed.")

        selected_model = model or settings.DEFAULT_MODEL
        try:
            response = ollama_client.chat(
                model=selected_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_message},
                ],
                options={"temperature": 0},
            )
            content = response["message"]["content"]
            return self._clean_code(content)
        except Exception as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc

    @staticmethod
    def _clean_code(raw: str) -> str:
        """Strip markdown code fences if the LLM wraps the output."""
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.splitlines()
            # Remove first and last fence lines
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw = "\n".join(lines).strip()
        return raw

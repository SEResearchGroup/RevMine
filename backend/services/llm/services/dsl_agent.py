"""
DSL Generation Agent
====================
Translates a natural-language analysis request into an Analysis DSL JSON document.

Supports two backends:
  - OpenRouter (cloud LLMs via API key)
  - Ollama     (local LLMs)

Usage:
    agent = DSLGenerationAgent(backend="openrouter")
    result = agent.generate(
        user_message="Show lead time by author",
        available_columns=["Lead_Time", "Author", "State", ...],
        model="openai/gpt-4o-mini",
    )
    # result = {"version": "1", "source": {...}, ...}   or
    # result = {"error": "column_missing", ...}          or
    # result = {"error": "dsl_insufficient", ...}
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from config import settings
from prompts_dsl import build_dsl_system_prompt
from utils.json_utils import extract_json_object

logger = logging.getLogger(__name__)


class DSLGenerationAgent:
    """
    Agent responsible for NL → DSL translation.

    Wraps the LLM call (OpenRouter or Ollama) with a DSL-specific system prompt
    and returns a parsed JSON dict.
    """

    def __init__(self, backend: str = "openrouter"):
        if backend not in ("openrouter", "ollama"):
            raise ValueError(f"Unknown backend '{backend}'. Use 'openrouter' or 'ollama'.")
        self._backend = backend

    def generate(
        self,
        user_message: str,
        available_columns: Optional[List[str]] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate an Analysis DSL document from a natural-language request.

        Parameters
        ----------
        user_message : str
            The user's query in plain language.
        available_columns : list[str], optional
            Column names available in the dataset. Injected into the system prompt.
        model : str, optional
            Override the default model for this request.

        Returns
        -------
        dict
            A DSL document (valid JSON) or an error dict with an "error" key.
        """
        system_prompt = build_dsl_system_prompt(available_columns or [])
        t0 = time.monotonic()

        if self._backend == "openrouter":
            result = self._call_openrouter(user_message, system_prompt, model)
        else:
            result = self._call_ollama(user_message, system_prompt, model)

        duration = round(time.monotonic() - t0, 3)
        logger.info(
            "DSL generated",
            extra={
                "event": "dsl_generated",
                "backend": self._backend,
                "model": model,
                "duration": duration,
                "has_error": "error" in result,
                "columns_count": len(available_columns or []),
            },
        )
        return result

    # ------------------------------------------------------------------
    # OpenRouter backend
    # ------------------------------------------------------------------

    def _call_openrouter(
        self,
        user_message: str,
        system_prompt: str,
        model: Optional[str],
    ) -> Dict[str, Any]:
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
            "response_format": {"type": "json_object"},
        }

        try:
            resp = req.post(url, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return extract_json_object(content)
        except req.exceptions.RequestException as exc:
            raise RuntimeError(f"OpenRouter request failed: {exc}") from exc
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"Unexpected OpenRouter response structure: {exc}") from exc

    # ------------------------------------------------------------------
    # Ollama backend
    # ------------------------------------------------------------------

    def _call_ollama(
        self,
        user_message: str,
        system_prompt: str,
        model: Optional[str],
    ) -> Dict[str, Any]:
        try:
            import ollama as ollama_client
        except ImportError:
            raise RuntimeError("ollama package not installed. Run: pip install ollama")

        selected_model = model or settings.DEFAULT_MODEL
        try:
            response = ollama_client.chat(
                model=selected_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_message},
                ],
                format="json",
                options={"temperature": 0},
            )
            content = response["message"]["content"]
            return extract_json_object(content)
        except Exception as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc

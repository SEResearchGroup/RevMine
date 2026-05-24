from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field
from typing import List, Dict, Any


class OpenRouterRequest(BaseModel):
    model: str
    messages: List[Dict[str, Any]]


class ParseRequest(BaseModel):
    user_message: str = Field(
        ..., min_length=1, description="Natural language user request"
    )
    model: Optional[str] = Field(None, description="Optional Ollama model override")
    provider: Optional[str] = Field(None, description="Optional provider override")


class ParseResponse(BaseModel):
    model: str
    result: Dict[str, Any]



class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class ChatRequest(BaseModel):
    model: str = Field(..., description="OpenRouter model id, e.g. 'openai/gpt-5.2'")
    messages: list[ChatMessage]
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)
    stream: bool = False


class ChatResponse(BaseModel):
    model: str
    content: str
    raw: dict[str, Any]

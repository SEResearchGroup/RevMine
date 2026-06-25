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


# --- DSL-First schemas ---

class DSLGenerateRequest(BaseModel):
    """Request body for POST /dsl/generate"""
    user_message: str = Field(
        ..., min_length=1, description="Natural language analysis request"
    )
    available_columns: List[str] = Field(
        default_factory=list,
        description="Column names present in the target dataset",
    )
    model: Optional[str] = Field(None, description="LLM model override")
    backend: str = Field(
        default="openrouter",
        description="LLM backend: 'openrouter' or 'ollama'",
    )


class DSLGenerateResponse(BaseModel):
    """Response from POST /dsl/generate"""
    backend: str
    model: Optional[str]
    dsl: Dict[str, Any]
    has_error: bool


class CodeGenerateRequest(BaseModel):
    """Request body for POST /code/generate"""
    user_message: str = Field(..., min_length=1)
    available_columns: List[str] = Field(default_factory=list)
    model: Optional[str] = Field(None)
    backend: str = Field(default="openrouter")


class CodeGenerateResponse(BaseModel):
    """Response from POST /code/generate"""
    backend: str
    model: Optional[str]
    code: str

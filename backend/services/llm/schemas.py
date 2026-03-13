from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ParseRequest(BaseModel):
    user_message: str = Field(
        ..., min_length=1, description="Natural language user request"
    )
    model: Optional[str] = Field(None, description="Optional Ollama model override")


class ParseResponse(BaseModel):
    model: str
    result: Dict[str, Any]

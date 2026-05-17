import pytest

from ollama._types import ResponseError

from services import ollama_service
from services.ollama_service import OllamaParserService


class FakeClient:
    def __init__(self, content: str):
        self.content = content

    def chat(self, **kwargs):
        return {"message": {"content": self.content}}


def test_parse_user_request_returns_json(monkeypatch):
    monkeypatch.setattr(ollama_service.settings, "OLLAMA_HOST", "http://ollama.test")
    service = OllamaParserService()
    service.client = FakeClient('{"intent":"collect","metrics":["creation_date"]}')

    result = service.parse_user_request("Collect MRs", "deepseek-r1")

    assert result["intent"] == "collect"
    assert result["metrics"] == ["creation_date"]


def test_parse_user_request_handles_wrapped_json(monkeypatch):
    monkeypatch.setattr(ollama_service.settings, "OLLAMA_HOST", "http://ollama.test")
    service = OllamaParserService()
    service.client = FakeClient(
        'Result:\n{"intent":"analyze","metrics":["commits_distribution"]}'
    )

    result = service.parse_user_request("Analyze commits", "deepseek-r1")

    assert result["intent"] == "analyze"


def test_parse_user_request_raises_on_invalid_json(monkeypatch):
    monkeypatch.setattr(ollama_service.settings, "OLLAMA_HOST", "http://ollama.test")
    service = OllamaParserService()
    service.client = FakeClient("nonsense")

    with pytest.raises(ValueError):
        service.parse_user_request("bad", "deepseek-r1")


def test_init_requires_ollama_host(monkeypatch):
    monkeypatch.setattr(ollama_service.settings, "OLLAMA_HOST", None)

    with pytest.raises(RuntimeError, match="OLLAMA_HOST"):
        OllamaParserService()


def test_parse_user_request_wraps_unexpected_client_error(monkeypatch):
    monkeypatch.setattr(ollama_service.settings, "OLLAMA_HOST", "http://ollama.test")
    service = OllamaParserService()
    service.client = type(
        "BrokenClient",
        (),
        {"chat": lambda self, **kwargs: (_ for _ in ()).throw(ConnectionError("offline"))},
    )()

    with pytest.raises(RuntimeError, match="Unexpected Ollama error"):
        service.parse_user_request("Collect", "deepseek-r1")


def test_parse_user_request_propagates_response_error(monkeypatch):
    monkeypatch.setattr(ollama_service.settings, "OLLAMA_HOST", "http://ollama.test")
    service = OllamaParserService()
    service.client = type(
        "BrokenClient",
        (),
        {"chat": lambda self, **kwargs: (_ for _ in ()).throw(ResponseError("bad model", 404))},
    )()

    with pytest.raises(ResponseError):
        service.parse_user_request("Collect", "missing")

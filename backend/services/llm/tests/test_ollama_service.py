import pytest

from services.ollama_service import OllamaParserService


class FakeClient:
    def __init__(self, content: str):
        self.content = content

    def chat(self, **kwargs):
        return {"message": {"content": self.content}}


def test_parse_user_request_returns_json(monkeypatch):
    service = OllamaParserService()
    service.client = FakeClient('{"intent":"collect","metrics":["creation_date"]}')

    result = service.parse_user_request("Collect MRs", "deepseek-r1")

    assert result["intent"] == "collect"
    assert result["metrics"] == ["creation_date"]


def test_parse_user_request_handles_wrapped_json(monkeypatch):
    service = OllamaParserService()
    service.client = FakeClient(
        'Result:\n{"intent":"analyze","metrics":["commits_distribution"]}'
    )

    result = service.parse_user_request("Analyze commits", "deepseek-r1")

    assert result["intent"] == "analyze"


def test_parse_user_request_raises_on_invalid_json(monkeypatch):
    service = OllamaParserService()
    service.client = FakeClient("nonsense")

    with pytest.raises(ValueError):
        service.parse_user_request("bad", "deepseek-r1")

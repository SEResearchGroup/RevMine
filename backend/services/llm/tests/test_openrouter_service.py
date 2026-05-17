from unittest.mock import MagicMock

import pytest
import requests

from services import openrouter_service
from services.openrouter_service import OpenRouterParserService


class ResponseStub:
    def __init__(self, status_code=200, payload=None, json_error=None):
        self.status_code = status_code
        self._payload = payload
        self._json_error = json_error

    def json(self):
        if self._json_error:
            raise self._json_error
        return self._payload


@pytest.fixture(autouse=True)
def openrouter_settings(monkeypatch):
    monkeypatch.setattr(openrouter_service.settings, "OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setattr(openrouter_service.settings, "OPENROUTER_DEFAULT_MODEL", "openai/test")
    monkeypatch.setattr(openrouter_service.settings, "OPENROUTER_SITE_URL", "https://revmine.test")
    monkeypatch.setattr(openrouter_service.settings, "OPENROUTER_SITE_NAME", "RevMine", raising=False)


def test_parse_user_request_success_posts_expected_payload(monkeypatch):
    mock_post = MagicMock(
        return_value=ResponseStub(
            200,
            {
                "choices": [{"message": {"content": '{"intent":"collect"}'}}],
                "usage": {"total_tokens": 9, "prompt_tokens": 5, "completion_tokens": 4},
            },
        )
    )
    monkeypatch.setattr(openrouter_service.requests, "post", mock_post)

    result = OpenRouterParserService().parse_user_request("Collect MRs", model="custom/model")

    assert result == {"intent": "collect"}
    _, kwargs = mock_post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer sk-test"
    assert kwargs["headers"]["HTTP-Referer"] == "https://revmine.test"
    assert kwargs["headers"]["X-OpenRouter-Title"] == "RevMine"
    assert kwargs["json"]["model"] == "custom/model"
    assert kwargs["json"]["response_format"] == {"type": "json_object"}
    assert kwargs["timeout"] == 60


def test_parse_user_request_requires_api_key(monkeypatch):
    monkeypatch.setattr(openrouter_service.settings, "OPENROUTER_API_KEY", "")

    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        OpenRouterParserService().parse_user_request("Collect")


def test_parse_user_request_wraps_request_exception(monkeypatch):
    monkeypatch.setattr(
        openrouter_service.requests,
        "post",
        MagicMock(side_effect=requests.Timeout("slow")),
    )

    with pytest.raises(RuntimeError, match="OpenRouter request failed"):
        OpenRouterParserService().parse_user_request("Collect")


def test_parse_user_request_rejects_non_json_response(monkeypatch):
    monkeypatch.setattr(
        openrouter_service.requests,
        "post",
        MagicMock(return_value=ResponseStub(200, json_error=ValueError("not json"))),
    )

    with pytest.raises(RuntimeError, match="non-JSON"):
        OpenRouterParserService().parse_user_request("Collect")


def test_parse_user_request_rejects_error_status(monkeypatch):
    monkeypatch.setattr(
        openrouter_service.requests,
        "post",
        MagicMock(return_value=ResponseStub(401, {"error": "bad key"})),
    )

    with pytest.raises(RuntimeError, match="OpenRouter response error"):
        OpenRouterParserService().parse_user_request("Collect")


def test_parse_user_request_rejects_malformed_success_response(monkeypatch):
    monkeypatch.setattr(
        openrouter_service.requests,
        "post",
        MagicMock(return_value=ResponseStub(200, {"choices": []})),
    )

    with pytest.raises(RuntimeError, match="Malformed OpenRouter response"):
        OpenRouterParserService().parse_user_request("Collect")

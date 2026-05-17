from unittest.mock import MagicMock

import pytest

from analytics import workspace_tokens


@pytest.fixture(autouse=True)
def reset_request_reply_client():
    workspace_tokens._rr_client = None
    yield
    workspace_tokens._rr_client = None


def test_get_rr_client_is_lazy_singleton(monkeypatch):
    instances = []

    class FakeRequestReplyClient:
        def __init__(self):
            instances.append(self)

    monkeypatch.setattr(workspace_tokens, "RequestReplyClient", FakeRequestReplyClient)

    first = workspace_tokens._get_rr_client()
    second = workspace_tokens._get_rr_client()

    assert first is second
    assert len(instances) == 1


def test_resolve_workspace_token_returns_token_and_platform():
    client = MagicMock()
    client.call.return_value = {"status": "ok", "token": "tok", "platform": "github"}
    workspace_tokens._rr_client = client

    result = workspace_tokens.resolve_workspace_token(user_id=1, workspace_id=2)

    assert result == {"token": "tok", "platform": "github"}
    client.call.assert_called_once_with(
        request_topic=workspace_tokens.Topics.TOKENS_REQUEST,
        response_topic=workspace_tokens.Topics.TOKENS_RESPONSE,
        payload={"user_id": 1, "workspace_id": 2},
        timeout=10,
    )


@pytest.mark.parametrize("response", [None, {}, {"status": "error"}, {"status": "ok"}])
def test_resolve_workspace_token_rejects_bad_responses(response):
    client = MagicMock()
    client.call.return_value = response
    workspace_tokens._rr_client = client

    with pytest.raises(workspace_tokens.WorkspaceTokenError):
        workspace_tokens.resolve_workspace_token(user_id=1, workspace_id=2)

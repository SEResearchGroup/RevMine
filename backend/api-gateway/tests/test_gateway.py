import httpx
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AUTH_SERVICE_URL", "https://auth-service.example/api/v1/auth")
    monkeypatch.setenv("CONFIGURATION_SERVICE_URL", "https://configuration-service.example/api/v1/workspaces")
    monkeypatch.setenv("COLLECTION_SERVICE_URL", "https://collection-service.example/api/v1/collections")
    monkeypatch.setenv("ANALYZE_SERVICE_URL", "https://analyze-service.example/api/v1/analysis")
    monkeypatch.setenv("LLM_SERVICE_URL", "https://llm-service.example/api/v1/llm")
    monkeypatch.setenv("NOTIFICATION_SERVICE_URL", "https://notification-service.example/api/v1/notifications")
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "2")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    from gateway.app import create_app

    return TestClient(create_app())


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_unknown_route_returns_404(client):
    response = client.get("/api/v1/unknown")
    assert response.status_code == 404


def test_rate_limiting(client):
    assert client.get("/health").status_code == 200
    assert client.get("/health").status_code == 200
    assert client.get("/health").status_code == 429


def test_public_auth_route_is_proxied_without_introspection(client, monkeypatch):
    async def handler(request):
        assert request.url == "https://auth-service.example/api/v1/auth/login"
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(httpx.AsyncClient, "request", lambda self, **kwargs: handler(httpx.Request(kwargs["method"], kwargs["url"])))
    response = client.post("/api/v1/auth/login", json={"email": "u@example.com"})
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_legacy_unversioned_route_is_rewritten_to_v1(client, monkeypatch):
    async def handler(request):
        assert request.url == "https://auth-service.example/api/v1/auth/register"
        return httpx.Response(201, json={"created": True})

    monkeypatch.setattr(
        httpx.AsyncClient,
        "request",
        lambda self, **kwargs: handler(httpx.Request(kwargs["method"], kwargs["url"])),
    )

    response = client.post("/api/auth/register", json={"email": "u@example.com"})

    assert response.status_code == 201
    assert response.json() == {"created": True}


def test_protected_route_introspects_and_injects_user_id(client, monkeypatch):
    calls = []

    async def fake_post(self, url, headers):
        calls.append(("post", url, headers))
        return httpx.Response(200, json={"user_id": 42})

    async def fake_request(self, method, url, headers, content):
        calls.append(("request", method, url, headers, content))
        return httpx.Response(200, json={"proxied": True})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(httpx.AsyncClient, "request", fake_request)

    response = client.get(
        "/api/v1/workspaces/7/repositories?state=active",
        headers={"Authorization": "Bearer token"},
    )

    assert response.status_code == 200
    assert response.json() == {"proxied": True}
    assert calls[0][1] == "https://auth-service.example/api/v1/auth/introspect"
    assert calls[1][2] == "https://configuration-service.example/api/v1/workspaces/7/repositories?state=active"
    assert calls[1][3]["X-User-ID"] == "42"


def test_protected_route_rejects_missing_token(client):
    response = client.get("/api/v1/workspaces")
    assert response.status_code == 401


def test_upstream_timeout_returns_504(client, monkeypatch):
    async def fake_request(self, method, url, headers, content):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx.AsyncClient, "request", fake_request)
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 504

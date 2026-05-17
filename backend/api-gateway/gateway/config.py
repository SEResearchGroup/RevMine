import os
from dataclasses import dataclass


def get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value.rstrip("/")


@dataclass(frozen=True)
class Route:
    prefix: str
    target: str
    auth_required: bool = True

    def matches(self, path: str) -> bool:
        clean_prefix = self.prefix.rstrip("/")
        return path == clean_prefix or path.startswith(f"{clean_prefix}/")

    def target_url(self, path: str, query_string: bytes = b"") -> str:
        clean_prefix = self.prefix.rstrip("/")
        suffix = path[len(clean_prefix):] or "/"
        url = f"{self.target}{suffix}"
        if query_string:
            url = f"{url}?{query_string.decode()}"
        return url


@dataclass(frozen=True)
class GatewaySettings:
    auth_service_url: str
    routes: tuple[Route, ...]
    rate_limit_requests: int
    rate_limit_window_seconds: int
    request_timeout_seconds: float
    cors_origins: tuple[str, ...]


def load_settings() -> GatewaySettings:
    auth_service_url = get_env("AUTH_SERVICE_URL")
    routes = (
        Route("/api/auth", auth_service_url, auth_required=False),
        Route("/api/workspaces", get_env("CONFIGURATION_SERVICE_URL")),
        Route("/api/collections", get_env("COLLECTION_SERVICE_URL")),
        Route("/api/analysis", get_env("ANALYZE_SERVICE_URL")),
        Route("/api/llm", get_env("LLM_SERVICE_URL"), auth_required=False),
        Route("/api/notifications", get_env("NOTIFICATION_SERVICE_URL")),
    )
    cors_origins = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    )
    return GatewaySettings(
        auth_service_url=auth_service_url,
        routes=routes,
        rate_limit_requests=int(os.getenv("RATE_LIMIT_REQUESTS", "120")),
        rate_limit_window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
        request_timeout_seconds=float(os.getenv("GATEWAY_REQUEST_TIMEOUT", "300")),
        cors_origins=cors_origins,
    )

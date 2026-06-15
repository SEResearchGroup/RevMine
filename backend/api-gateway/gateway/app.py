from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import load_settings
from .proxy import GatewayProxy
from .rate_limit import SlidingWindowRateLimiter


def create_app() -> FastAPI:
    settings = load_settings()
    app = FastAPI(title="RevMine API Gateway", version="1.0.0")
    proxy = GatewayProxy(settings)
    limiter = SlidingWindowRateLimiter(
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.middleware("http")
    async def rate_limit(request: Request, call_next):
        client_host = request.client.host if request.client else "unknown"
        if not limiter.allow(client_host):
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)
        return await call_next(request)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.api_route(
        "/api/v1/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
    async def gateway_route(request: Request, path: str):
        return await proxy.proxy(request)

    @app.api_route(
        "/api/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
    async def gateway_legacy_route(request: Request, path: str):
        return await proxy.proxy(request, route_path=f"/api/v1/{path}")

    return app

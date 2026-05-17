import logging

import httpx
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from .config import GatewaySettings, Route

logger = logging.getLogger(__name__)

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


class GatewayProxy:
    def __init__(self, settings: GatewaySettings):
        self.settings = settings

    def match_route(self, path: str) -> Route | None:
        for route in self.settings.routes:
            if route.matches(path):
                return route
        return None

    async def proxy(self, request: Request) -> Response:
        route = self.match_route(request.url.path)
        if route is None:
            return JSONResponse({"error": "Route not found"}, status_code=404)

        headers = self._forward_headers(request)
        if route.auth_required:
            auth_response = await self._introspect(request)
            if auth_response.status_code != 200:
                return auth_response
            headers["X-User-ID"] = auth_response.headers["X-User-ID"]

        target_url = route.target_url(request.url.path, request.url.query.encode())
        body = await request.body()
        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                upstream = await client.request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    content=body,
                )
        except httpx.TimeoutException:
            return JSONResponse({"error": "Service timeout"}, status_code=504)
        except httpx.HTTPError as exc:
            logger.warning("Gateway upstream error for %s: %s", target_url, exc)
            return JSONResponse({"error": "Service unavailable"}, status_code=503)

        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=self._response_headers(upstream),
            media_type=upstream.headers.get("content-type"),
        )

    async def _introspect(self, request: Request) -> Response:
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return JSONResponse({"error": "Authentication required"}, status_code=401)

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.settings.auth_service_url}/introspect",
                    headers={"Authorization": auth_header},
                )
        except httpx.HTTPError:
            return JSONResponse({"error": "Authentication service unavailable"}, status_code=503)

        if response.status_code != 200:
            return JSONResponse({"error": "Invalid or expired token"}, status_code=401)

        payload = response.json()
        user_id = payload.get("user_id")
        if not user_id:
            return JSONResponse({"error": "Invalid auth service response"}, status_code=502)

        proxied = JSONResponse({"active": True}, status_code=200)
        proxied.headers["X-User-ID"] = str(user_id)
        return proxied

    def _forward_headers(self, request: Request) -> dict[str, str]:
        return {
            key: value
            for key, value in request.headers.items()
            if key.lower() not in HOP_BY_HOP_HEADERS
        }

    def _response_headers(self, upstream: httpx.Response) -> dict[str, str]:
        return {
            key: value
            for key, value in upstream.headers.items()
            if key.lower() not in HOP_BY_HOP_HEADERS
        }

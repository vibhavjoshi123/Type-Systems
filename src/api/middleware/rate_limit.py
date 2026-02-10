"""Simple in-memory rate limiting middleware.

Uses a sliding window counter per client IP. For production
deployments, replace with Redis-backed rate limiting.
"""

from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP rate limiting with sliding window.

    Args:
        app: The ASGI application.
        requests_per_minute: Maximum requests per IP per minute.
    """

    def __init__(self, app: object, requests_per_minute: int = 120) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.rpm = requests_per_minute
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window_start = now - 60.0

        # Clean old entries and add current request
        timestamps = self._requests[client_ip]
        self._requests[client_ip] = [t for t in timestamps if t > window_start]
        self._requests[client_ip].append(now)

        if len(self._requests[client_ip]) > self.rpm:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": "60"},
            )

        return await call_next(request)

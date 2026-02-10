"""API key authentication middleware.

Validates requests against a configured API key. If no API key is
configured (API_KEY env var), all requests are allowed through
(development mode).
"""

from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Paths that never require authentication
PUBLIC_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware that validates X-API-Key header.

    If the API_KEY environment variable is not set, all requests
    are allowed (development mode). When set, all non-public
    endpoints require a matching X-API-Key header.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        api_key = os.environ.get("API_KEY")

        # No key configured -> allow all (dev mode)
        if not api_key:
            return await call_next(request)

        # Public paths don't require auth
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # Validate header
        request_key = request.headers.get("X-API-Key")
        if request_key != api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
            )

        return await call_next(request)

"""Tests for API middleware (auth and rate limiting)."""

import os

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.middleware.auth import APIKeyMiddleware
from src.api.middleware.rate_limit import RateLimitMiddleware


def _make_app(
    api_key: str | None = None,
    rpm: int = 120,
) -> FastAPI:
    """Create a minimal FastAPI app with middleware for testing."""
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, requests_per_minute=rpm)
    app.add_middleware(APIKeyMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"ok": True}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    return app


class TestAPIKeyMiddleware:
    def test_no_key_configured_allows_all(self):
        os.environ.pop("API_KEY", None)
        client = TestClient(_make_app())
        response = client.get("/test")
        assert response.status_code == 200

    def test_with_key_rejects_missing(self):
        os.environ["API_KEY"] = "test-secret-key"
        try:
            client = TestClient(_make_app())
            response = client.get("/test")
            assert response.status_code == 401
        finally:
            os.environ.pop("API_KEY", None)

    def test_with_key_accepts_valid(self):
        os.environ["API_KEY"] = "test-secret-key"
        try:
            client = TestClient(_make_app())
            response = client.get(
                "/test", headers={"X-API-Key": "test-secret-key"}
            )
            assert response.status_code == 200
        finally:
            os.environ.pop("API_KEY", None)

    def test_with_key_rejects_invalid(self):
        os.environ["API_KEY"] = "test-secret-key"
        try:
            client = TestClient(_make_app())
            response = client.get(
                "/test", headers={"X-API-Key": "wrong-key"}
            )
            assert response.status_code == 401
        finally:
            os.environ.pop("API_KEY", None)

    def test_health_always_accessible(self):
        os.environ["API_KEY"] = "test-secret-key"
        try:
            client = TestClient(_make_app())
            response = client.get("/health")
            assert response.status_code == 200
        finally:
            os.environ.pop("API_KEY", None)


class TestRateLimitMiddleware:
    def test_under_limit(self):
        client = TestClient(_make_app(rpm=10))
        for _ in range(10):
            response = client.get("/test")
            assert response.status_code == 200

    def test_over_limit(self):
        client = TestClient(_make_app(rpm=5))
        for _ in range(5):
            client.get("/test")
        response = client.get("/test")
        assert response.status_code == 429
        assert "Rate limit" in response.json()["detail"]

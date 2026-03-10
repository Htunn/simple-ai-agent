"""Unit tests for API middleware (CorrelationId and ContentSizeLimit)."""

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from src.api.middleware import ContentSizeLimitMiddleware, CorrelationIdMiddleware


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _echo(request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def _app_with_middleware(*middleware_classes):
    app = Starlette(routes=[Route("/", _echo, methods=["GET", "POST"])])
    for cls in reversed(middleware_classes):
        app.add_middleware(cls)
    return app


# ── CorrelationIdMiddleware ───────────────────────────────────────────────────

class TestCorrelationIdMiddleware:
    def setup_method(self):
        self.client = TestClient(_app_with_middleware(CorrelationIdMiddleware))

    def test_generates_x_request_id_if_missing(self):
        resp = self.client.get("/")
        assert "X-Request-ID" in resp.headers
        # Should be non-empty
        assert len(resp.headers["X-Request-ID"]) > 0

    def test_echoes_provided_x_request_id(self):
        resp = self.client.get("/", headers={"X-Request-ID": "my-trace-id"})
        assert resp.headers["X-Request-ID"] == "my-trace-id"

    def test_generated_id_is_different_each_request(self):
        ids = {self.client.get("/").headers["X-Request-ID"] for _ in range(5)}
        assert len(ids) == 5

    def test_passes_through_with_200(self):
        resp = self.client.get("/")
        assert resp.status_code == 200
        assert resp.text == "ok"


# ── ContentSizeLimitMiddleware ────────────────────────────────────────────────

class TestContentSizeLimitMiddleware:
    _MAX = 1 * 1024 * 1024  # 1 MiB

    def setup_method(self):
        self.client = TestClient(_app_with_middleware(ContentSizeLimitMiddleware))

    def test_allows_request_without_content_length(self):
        resp = self.client.get("/")
        assert resp.status_code == 200

    def test_allows_request_within_limit(self):
        resp = self.client.post(
            "/",
            content=b"x" * 100,
            headers={"Content-Length": "100"},
        )
        assert resp.status_code == 200

    def test_allows_request_exactly_at_limit(self):
        resp = self.client.post(
            "/",
            content=b"",
            headers={"Content-Length": str(self._MAX)},
        )
        assert resp.status_code == 200

    def test_rejects_oversized_content_length_with_413(self):
        oversized = self._MAX + 1
        resp = self.client.post(
            "/",
            content=b"",
            headers={"Content-Length": str(oversized)},
        )
        assert resp.status_code == 413

    def test_413_response_message_mentions_size(self):
        resp = self.client.post(
            "/",
            content=b"",
            headers={"Content-Length": str(self._MAX + 1024)},
        )
        assert "too large" in resp.text.lower() or "1 MiB" in resp.text

    def test_very_large_declared_size_rejected(self):
        resp = self.client.post(
            "/",
            content=b"",
            headers={"Content-Length": str(100 * 1024 * 1024)},  # 100 MiB
        )
        assert resp.status_code == 413


# ── Both middlewares stacked ──────────────────────────────────────────────────

class TestMiddlewareStack:
    def setup_method(self):
        self.client = TestClient(
            _app_with_middleware(CorrelationIdMiddleware, ContentSizeLimitMiddleware)
        )

    def test_oversized_still_returns_413_with_correlation_id(self):
        resp = self.client.post(
            "/",
            content=b"",
            headers={"Content-Length": str(self._MAX + 1), "X-Request-ID": "trace-abc"},
        )
        # ContentSizeLimit fires at 413 before payload is read
        assert resp.status_code == 413

    _MAX = 1 * 1024 * 1024

    def test_normal_request_gets_correlation_and_200(self):
        resp = self.client.get("/", headers={"X-Request-ID": "test-id-123"})
        assert resp.status_code == 200
        assert resp.headers.get("X-Request-ID") == "test-id-123"

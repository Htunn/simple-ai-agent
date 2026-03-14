"""Rate limiting and request middleware."""

import uuid

import structlog
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.config import get_settings

settings = get_settings()
logger = structlog.get_logger()

_MAX_BODY_BYTES = 1 * 1024 * 1024  # 1 MiB

# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Attach a correlation/request-ID to every request for distributed tracing."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.unbind_contextvars("request_id")
        response.headers["X-Request-ID"] = request_id
        return response


class ContentSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject request bodies larger than 1 MiB with HTTP 413."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > _MAX_BODY_BYTES:
            logger.warning(
                "request_body_too_large",
                content_length=content_length,
                path=request.url.path,
            )
            return Response(
                content="Request body too large (max 1 MiB)",
                status_code=413,
            )
        return await call_next(request)

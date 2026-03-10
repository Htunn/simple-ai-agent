"""OpenTelemetry distributed tracing setup and helpers.

Usage
-----
Call :func:`setup_tracing` once at application startup (guarded by
``settings.otel_enabled``).  All other code calls :func:`get_tracer` to
obtain a named tracer and then uses the standard OTel context-manager API::

    from src.monitoring.tracing import get_tracer

    _tracer = get_tracer(__name__)

    async def my_op():
        with _tracer.start_as_current_span("my_op.do_work") as span:
            span.set_attribute("some.key", value)
            ...

When OTel has not been initialised (``otel_enabled=False``) *all* tracers are
no-ops and add zero overhead.
"""

from __future__ import annotations

import importlib
import logging
from typing import TYPE_CHECKING, Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

if TYPE_CHECKING:
    from src.config import Settings

_logger = logging.getLogger(__name__)

# Module-level reference so we can shut it down cleanly.
_tracer_provider: TracerProvider | None = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def setup_tracing(settings: Settings) -> None:
    """Configure and start the OpenTelemetry :class:`TracerProvider`.

    Must be called once at application startup.  Subsequent calls are
    idempotent (no-ops).  When ``settings.otel_enabled`` is *False* this
    function is never called and all spans remain no-ops.
    """
    global _tracer_provider
    if _tracer_provider is not None:
        return

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "deployment.environment": settings.environment,
        }
    )

    sampler = ParentBased(root=TraceIdRatioBased(settings.otel_sample_rate))
    provider = TracerProvider(resource=resource, sampler=sampler)

    if settings.otlp_endpoint:
        _add_otlp_exporter(provider, settings.otlp_endpoint)
    else:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        _logger.info("otel: console exporter configured (no OTLP endpoint set)")

    trace.set_tracer_provider(provider)
    _tracer_provider = provider

    _instrument_libraries()

    _logger.info(
        "otel: tracing initialised service=%s sample_rate=%s",
        settings.otel_service_name,
        settings.otel_sample_rate,
    )


def instrument_fastapi(app: Any) -> None:
    """Instrument a FastAPI *app* instance with the OTel middleware.

    Must be called **after** :func:`setup_tracing`.  Silently ignored when
    the instrumentation package is not installed.
    """
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        _logger.info("otel: FastAPI instrumented")
    except ImportError:
        _logger.debug("otel: opentelemetry-instrumentation-fastapi not installed; skipping")


def get_tracer(name: str) -> trace.Tracer:
    """Return a named :class:`~opentelemetry.trace.Tracer`.

    Safe to call before :func:`setup_tracing` — returns a no-op tracer
    when no provider has been configured.
    """
    return trace.get_tracer(name)


def shutdown_tracing() -> None:
    """Flush pending spans and shut down the :class:`TracerProvider` gracefully.

    Call once during application shutdown.
    """
    global _tracer_provider
    if _tracer_provider is not None:
        _tracer_provider.shutdown()
        _tracer_provider = None
        _logger.info("otel: tracing shut down")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _add_otlp_exporter(provider: TracerProvider, endpoint: str) -> None:
    """Attach an OTLP gRPC span exporter to *provider*."""
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        _logger.info("otel: OTLP gRPC exporter configured endpoint=%s", endpoint)
    except ImportError:
        _logger.warning(
            "otel: opentelemetry-exporter-otlp-proto-grpc not installed; "
            "falling back to console exporter"
        )
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))


def _instrument_libraries() -> None:
    """Apply automatic instrumentation to supported libraries.

    Each instrumentor is loaded lazily so missing packages are silently
    ignored rather than raising :class:`ImportError` at startup.
    """
    _try_instrument(
        "SQLAlchemy", "opentelemetry.instrumentation.sqlalchemy", "SQLAlchemyInstrumentor"
    )
    _try_instrument("Redis", "opentelemetry.instrumentation.redis", "RedisInstrumentor")
    _try_instrument("HTTPX", "opentelemetry.instrumentation.httpx", "HTTPXClientInstrumentor")


def _try_instrument(label: str, module_path: str, class_name: str) -> None:
    try:
        mod = importlib.import_module(module_path)
        getattr(mod, class_name)().instrument()
        _logger.debug("otel: %s instrumented", label)
    except ImportError:
        _logger.debug("otel: %s instrumentation package not installed; skipping", label)
    except Exception as exc:  # pragma: no cover
        _logger.warning("otel: %s instrumentation failed: %s", label, exc)

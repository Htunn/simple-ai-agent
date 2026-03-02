"""Logging configuration."""

import logging
import os
import sys

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structured logging.

    Uses JSON format when not attached to a TTY (containers, CI) or when
    LOG_FORMAT=json is explicitly set.  Falls back to the human-readable
    ConsoleRenderer for interactive development sessions.
    """
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Choose renderer based on environment
    use_json = (
        not sys.stdout.isatty()
        or os.getenv("LOG_FORMAT", "").lower() == "json"
    )

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    final_processor = (
        structlog.processors.JSONRenderer()
        if use_json
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    # Configure structlog
    structlog.configure(
        processors=shared_processors + [final_processor],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )

"""Structured logging setup.

We default to human-readable console output for local development and
JSON for anything running headless (CI, cron). Toggled by ``AIDLC_LOG_JSON=1``.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

import structlog

from aidlc.config import get_settings

_CONFIGURED = False


def configure_logging() -> None:
    """Idempotent logging setup — safe to call from multiple CLI entrypoints."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = get_settings().aidlc_log_level.value
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=level,
    )

    json_mode = os.environ.get("AIDLC_LOG_JSON") == "1"
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer() if json_mode else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )
    _CONFIGURED = True


def get_logger(name: str | None = None) -> Any:
    """Return a bound structlog logger.

    We type as ``Any`` rather than ``BoundLogger`` because structlog returns a
    proxy that duck-types to the bound logger interface, and pinning the
    precise class triggers unresolvable no-any-return complaints from mypy.
    """
    configure_logging()
    return structlog.get_logger(name)

"""Structured JSON logging for Aethos PS.

Usage
-----
    from app.core.logging import configure_logging, trace_id_var, tenant_id_var

Call ``configure_logging()`` once in the lifespan hook.  Every log record will
carry ``trace_id`` and ``tenant_id`` from the context variables so request logs
are automatically correlated.

Never log secrets, tokens, or raw PII here — callers are responsible for
masking before passing data to loggers.
"""

from __future__ import annotations

import logging
import logging.config
from contextvars import ContextVar

from pythonjsonlogger.json import JsonFormatter

from app.core.config import settings
from app.domain.pii import mask_pii

# ---------------------------------------------------------------------------
# Context variables — set per-request by TenantMiddleware
# ---------------------------------------------------------------------------
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="")

_QUIET_LOGGERS = (
    "uvicorn.access",
    "httpx",
    # httpcore/hpack DEBUG records include low-level request headers and HTTP/2
    # header-table contents. Never inherit application DEBUG for these loggers.
    "httpcore",
    "hpack",
    # stripe-python DEBUG logs full request/response bodies (including
    # SetupIntent client secrets); its urllib3 transport logs request paths.
    "stripe",
    "urllib3",
)


# ---------------------------------------------------------------------------
# Custom formatter — injects context vars into every record
# ---------------------------------------------------------------------------

class _AethosFormatter(JsonFormatter):
    """JSON log formatter that injects context-var fields into every record."""

    def add_fields(
        self,
        log_record: dict,
        record: logging.LogRecord,
        message_dict: dict,
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        # Pre-log PII boundary (#374): mask structured identifiers (bank
        # accounts, tax IDs, cards, NRIC, email) in the free-text message before
        # it reaches a log sink — defence in depth if a caller forgets to mask.
        message = log_record.get("message")
        if isinstance(message, str) and message:
            log_record["message"] = mask_pii(message)
        log_record["service"] = "aethos-ps"
        log_record["environment"] = settings.environment
        log_record["trace_id"] = trace_id_var.get("")
        log_record["tenant_id"] = tenant_id_var.get("")
        # Rename levelname → level for cleaner JSON
        if "levelname" in log_record:
            log_record["level"] = log_record.pop("levelname")
        # Rename asctime → timestamp
        if "asctime" in log_record:
            log_record["timestamp"] = log_record.pop("asctime")


# ---------------------------------------------------------------------------
# Public configuration entry point
# ---------------------------------------------------------------------------

def configure_logging() -> None:
    """Configure the root logger to emit structured JSON.

    Call once at application startup (lifespan hook).  Safe to call multiple
    times — subsequent calls are no-ops.
    """
    # Uvicorn installs handlers before the application lifespan starts. Apply
    # sensitive/noisy dependency levels even when root logging is already
    # configured and this function otherwise has nothing to install.
    for logger_name in _QUIET_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    root = logging.getLogger()
    if root.handlers:
        # Already configured (e.g., during testing when multiple app instances spin up)
        return

    handler = logging.StreamHandler()
    handler.setFormatter(
        _AethosFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )

    log_level = logging.DEBUG if settings.debug else logging.INFO
    root.setLevel(log_level)
    root.addHandler(handler)

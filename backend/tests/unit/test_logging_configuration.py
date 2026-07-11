"""Logging configuration security regressions."""

from __future__ import annotations

import logging

import pytest

from app.core.logging import configure_logging

pytestmark = pytest.mark.unit


def test_transport_loggers_stay_quiet_when_uvicorn_already_configured_root() -> None:
    """HTTP transport DEBUG must not expose header-table values."""
    root = logging.getLogger()
    sentinel = logging.NullHandler()
    root.addHandler(sentinel)
    logger_names = (
        "uvicorn.access",
        "httpx",
        "httpcore",
        "hpack",
        "stripe",
        "urllib3",
    )
    original_levels = {
        logger_name: logging.getLogger(logger_name).level
        for logger_name in logger_names
    }
    try:
        for logger_name in logger_names:
            logging.getLogger(logger_name).setLevel(logging.DEBUG)

        configure_logging()

        for logger_name in logger_names:
            assert logging.getLogger(logger_name).level == logging.WARNING
    finally:
        root.removeHandler(sentinel)
        for logger_name, level in original_levels.items():
            logging.getLogger(logger_name).setLevel(level)

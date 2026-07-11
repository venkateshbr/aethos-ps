"""Contracts for the Postgres-backed Procrastinate application."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.main import lifespan
from app.workers.procrastinate_app import create_queue_app

pytestmark = pytest.mark.unit


def test_queue_app_applies_explicit_connection_pool_settings() -> None:
    config = Settings(
        _env_file=None,
        database_url="postgresql://queue.example.test/aethos",
        queue_db_pool_min_size=2,
        queue_db_pool_max_size=3,
        queue_db_application_name="aethos-ps-test-worker",
    )

    queue_app = create_queue_app(config)

    assert queue_app.connector._pool_args == {
        "conninfo": "postgresql://queue.example.test/aethos",
        "min_size": 2,
        "max_size": 3,
        "kwargs": {"application_name": "aethos-ps-test-worker"},
    }


async def test_required_queue_connection_failure_aborts_api_startup() -> None:
    runtime_settings = MagicMock(
        database_url="postgresql://queue.example.test/aethos",
        queue_required=True,
        extraction_mode="sync",
    )
    queue_app = MagicMock()
    queue_app.open_async = AsyncMock(side_effect=RuntimeError("queue unavailable"))

    with (
        patch("app.main.settings", runtime_settings),
        patch("app.workers.procrastinate_app.app", queue_app),
        pytest.raises(RuntimeError, match="queue unavailable"),
    ):
        async with lifespan(MagicMock()):
            pass


async def test_optional_queue_connection_failure_keeps_local_api_available() -> None:
    runtime_settings = MagicMock(
        database_url="postgresql://queue.example.test/aethos",
        queue_required=False,
        extraction_mode="sync",
    )
    queue_app = MagicMock()
    queue_app.open_async = AsyncMock(side_effect=RuntimeError("queue unavailable"))

    with (
        patch("app.main.settings", runtime_settings),
        patch("app.workers.procrastinate_app.app", queue_app),
        patch("app.agents.base.flush_langfuse"),
    ):
        async with lifespan(MagicMock()):
            pass

    queue_app.open_async.assert_awaited_once()


async def test_queue_startup_log_does_not_expose_connection_error_detail(caplog) -> None:
    runtime_settings = MagicMock(
        database_url="postgresql://queue.example.test/aethos",
        queue_required=False,
        extraction_mode="sync",
    )
    queue_app = MagicMock()
    queue_app.open_async = AsyncMock(
        side_effect=RuntimeError("postgresql://user:do-not-log-me@queue.example.test/aethos")
    )

    with (
        patch("app.main.settings", runtime_settings),
        patch("app.workers.procrastinate_app.app", queue_app),
        patch("app.agents.base.flush_langfuse"),
    ):
        async with lifespan(MagicMock()):
            pass

    assert "do-not-log-me" not in caplog.text
    assert "RuntimeError" in caplog.text

"""Static contracts for the Hostinger production Compose topology."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOSTINGER_COMPOSE = _REPO_ROOT / "docker-compose.hostinger.yml"
_PRODUCTION_COMPOSE = _REPO_ROOT / "infra" / "docker-compose.prod.yml"
_BACKEND_DOCKERFILE = _REPO_ROOT / "backend" / "Dockerfile"


def _hostinger_services() -> dict:
    compose = yaml.safe_load(_HOSTINGER_COMPOSE.read_text(encoding="utf-8"))
    return compose["services"]


def _production_services() -> dict:
    compose = yaml.safe_load(_PRODUCTION_COMPOSE.read_text(encoding="utf-8"))
    return compose["services"]


def _environment_default_int(value: str) -> int:
    match = re.fullmatch(r"\$\{[A-Z0-9_]+:-(\d+)}", value)
    assert match is not None
    return int(match.group(1))


def test_hostinger_services_have_separate_bounded_queue_pool_budgets() -> None:
    services = _hostinger_services()

    api_environment = services["api"]["environment"]
    worker_environment = services["worker"]["environment"]

    assert api_environment["QUEUE_DB_POOL_MIN_SIZE"] == "${QUEUE_API_DB_POOL_MIN_SIZE:-1}"
    assert api_environment["QUEUE_DB_POOL_MAX_SIZE"] == "${QUEUE_API_DB_POOL_MAX_SIZE:-1}"
    assert api_environment["QUEUE_DB_APPLICATION_NAME"] == (
        "${QUEUE_API_DB_APPLICATION_NAME:-aethos-ps-api}"
    )
    assert worker_environment["QUEUE_DB_POOL_MIN_SIZE"] == (
        "${QUEUE_WORKER_DB_POOL_MIN_SIZE:-1}"
    )
    assert worker_environment["QUEUE_DB_POOL_MAX_SIZE"] == (
        "${QUEUE_WORKER_DB_POOL_MAX_SIZE:-2}"
    )
    assert worker_environment["QUEUE_DB_APPLICATION_NAME"] == (
        "${QUEUE_WORKER_DB_APPLICATION_NAME:-aethos-ps-worker}"
    )


def test_hostinger_default_session_budget_preserves_deploy_headroom() -> None:
    services = _hostinger_services()
    api_environment = services["api"]["environment"]
    worker_environment = services["worker"]["environment"]
    dockerfile = _BACKEND_DOCKERFILE.read_text(encoding="utf-8")
    api_worker_match = re.search(r"--workers\s+(\d+)", dockerfile)

    assert api_worker_match is not None
    api_workers = int(api_worker_match.group(1))
    api_pool_max = _environment_default_int(api_environment["QUEUE_DB_POOL_MAX_SIZE"])
    worker_pool_max = _environment_default_int(worker_environment["QUEUE_DB_POOL_MAX_SIZE"])

    # Procrastinate's LISTEN/NOTIFY connection is outside its worker pool.
    steady_sessions = (api_workers * api_pool_max) + worker_pool_max + 1

    assert steady_sessions == 5
    assert (steady_sessions * 2) + 3 <= 15


def test_hostinger_worker_consumes_every_production_queue() -> None:
    worker_command = _hostinger_services()["worker"]["command"]
    queue_argument = re.search(r"--queues=([^\s]+)", worker_command)

    assert queue_argument is not None
    assert set(queue_argument.group(1).split(",")) == {
        "default",
        "extraction",
        "cron",
        "billing",
        "fx",
    }


def test_secondary_production_worker_uses_the_same_queue_contract() -> None:
    worker_command = _production_services()["worker"]["command"]
    queue_argument = re.search(r"--queues=([^\s]+)", worker_command)

    assert queue_argument is not None
    assert set(queue_argument.group(1).split(",")) == {
        "default",
        "extraction",
        "cron",
        "billing",
        "fx",
    }


def test_hostinger_api_requires_the_queue_for_readiness() -> None:
    api_environment = _hostinger_services()["api"]["environment"]

    assert api_environment["QUEUE_REQUIRED"] == "true"


def test_hostinger_api_healthcheck_requires_ready_json_status() -> None:
    healthcheck_command = _hostinger_services()["api"]["healthcheck"]["test"][-1]

    assert "/health/ready" in healthcheck_command
    assert "json.load" in healthcheck_command
    assert "data.get('status') == 'ready'" in healthcheck_command

"""Unit tests for enterprise ops hardening."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.rate_limit import InMemoryRateLimiter, RateLimitMiddleware, RateLimitRule
from app.core.tenant import get_tenant_id
from app.main import app as main_app
from app.services.operational_telemetry import (
    OperationalTelemetry,
    TenantHealthService,
    sanitise_path,
)
from app.services.operational_telemetry import (
    telemetry as global_telemetry,
)

pytestmark = pytest.mark.unit


def test_in_memory_rate_limiter_blocks_after_threshold() -> None:
    now = 1000.0

    def _now() -> float:
        return now

    limiter = InMemoryRateLimiter(now=_now)
    rule = RateLimitRule(
        name="signup",
        method="POST",
        path_prefix="/api/v1/auth/signup",
        max_requests=2,
        window_seconds=60,
    )

    assert limiter.check(rule=rule, subject="127.0.0.1").allowed is True
    assert limiter.check(rule=rule, subject="127.0.0.1").allowed is True
    blocked = limiter.check(rule=rule, subject="127.0.0.1")

    assert blocked.allowed is False
    assert blocked.retry_after_seconds == 60


def test_rate_limit_middleware_returns_safe_429_shape() -> None:
    app = FastAPI()

    @app.post("/api/v1/auth/signup")
    async def _signup() -> dict[str, bool]:
        return {"ok": True}

    app.add_middleware(
        RateLimitMiddleware,
        rules=[
            RateLimitRule(
                name="signup",
                method="POST",
                path_prefix="/api/v1/auth/signup",
                max_requests=1,
                window_seconds=60,
            )
        ],
    )
    client = TestClient(app)

    first = client.post("/api/v1/auth/signup")
    second = client.post("/api/v1/auth/signup")

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"]["code"] == "rate_limit_exceeded"
    assert "Retry-After" in second.headers
    assert second.headers["X-RateLimit-Remaining"] == "0"


def test_operational_telemetry_sanitises_paths_and_counts_failures() -> None:
    telemetry = OperationalTelemetry()

    telemetry.record_request_failure(
        method="GET",
        path="/api/v1/public/invoices/token_1234567890abcdef",
        status_code=404,
    )
    telemetry.record_request_failure(
        method="GET",
        path="/api/v1/public/invoices/token_1234567890abcdef",
        status_code=200,
    )
    telemetry.record_background_failure("close_scheduler_worker")

    snapshot = telemetry.snapshot()

    assert sanitise_path("/api/v1/public/invoices/token_1234567890abcdef").endswith(
        "/{token}"
    )
    assert snapshot["request_failures"][0]["status_code"] == 404
    assert snapshot["request_failures"][0]["count"] == 1
    assert snapshot["background_failures"][0] == {
        "worker_name": "close_scheduler_worker",
        "count": 1,
    }


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _Db, table: str) -> None:
        self.db = db
        self.table = table
        self.filters: list[tuple[str, Any]] = []

    def select(self, _columns: str) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self.filters.append((key, value))
        return self

    def gte(self, _key: str, _value: Any) -> _Query:
        return self

    def limit(self, _count: int) -> _Query:
        return self

    def execute(self) -> _Result:
        rows = self.db.tables[self.table]
        for key, value in self.filters:
            rows = [row for row in rows if row.get(key) == value]
        return _Result(rows)


class _Db:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "tenants": [{"id": "tenant-1"}],
            "tenant_users": [{"id": "tu-1", "tenant_id": "tenant-1"}],
            "agent_runs": [{"id": "run-1", "tenant_id": "tenant-1", "status": "failed"}],
            "agent_tool_invocations": [
                {
                    "id": "tool-1",
                    "tenant_id": "tenant-1",
                    "status": "failed",
                    "tool_name": "send_email",
                }
            ],
            "agent_workflow_runs": [],
            "accounting_close_tasks": [],
            "accounting_close_overrides": [],
            "financial_events": [],
        }

    def table(self, name: str) -> _Query:
        if name not in self.tables:
            raise AssertionError(f"unexpected table {name}")
        return _Query(self, name)


def test_tenant_health_summary_exposes_safe_operational_signals() -> None:
    summary = TenantHealthService(_Db(), "tenant-1").summary()  # type: ignore[arg-type]

    assert summary["status"] == "degraded"
    assert summary["tenant_id"] == "tenant-1"
    assert summary["runtime"]["queue_configured"] in {True, False}
    assert all(check["status"] == "ok" for check in summary["checks"]["tables"])
    assert summary["telemetry"]["failed_agent_runs_24h"] == 1
    assert summary["telemetry"]["failed_tool_invocations_24h"] == 1
    assert summary["telemetry"]["failed_tools_by_name_24h"] == [
        {"tool_name": "send_email", "count": 1}
    ]


def test_tenant_health_endpoint_returns_admin_scoped_safe_summary() -> None:
    fake_db = _Db()
    global_telemetry.reset()
    global_telemetry.record_request_failure(
        method="GET",
        path="/api/v1/public/invoices/token_1234567890abcdef",
        status_code=404,
    )
    main_app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="admin@example.com",
        role="admin",
    )
    main_app.dependency_overrides[get_tenant_id] = lambda: "tenant-1"
    main_app.dependency_overrides[get_service_role_client] = lambda: fake_db

    try:
        with TestClient(main_app) as client:
            response = client.get("/api/v1/tenants/health")
    finally:
        main_app.dependency_overrides.clear()
        global_telemetry.reset()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["tenant_id"] == "tenant-1"
    assert body["checks"]["tables"][0] == {"name": "tenants", "status": "ok"}
    assert body["telemetry"]["request_failures"][0]["path"].endswith("/{token}")
    assert "token_1234567890abcdef" not in response.text

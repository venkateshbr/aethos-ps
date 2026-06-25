"""Unit tests for enterprise ops hardening."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.config import settings
from app.core.db import get_service_role_client
from app.core.rate_limit import (
    InMemoryRateLimiter,
    RateLimitMiddleware,
    RateLimitRule,
    SupabaseRateLimiter,
)
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
    assert second.headers["X-RateLimit-Backend"] == "memory"
    assert second.headers["X-RateLimit-Fallback"] == "0"


class _RpcResult:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _RpcQuery:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data

    def execute(self) -> _RpcResult:
        return _RpcResult(self.data)


class _RpcDb:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def rpc(self, name: str, params: dict[str, Any]) -> _RpcQuery:
        self.calls.append((name, params))
        return _RpcQuery([{"allowed": True, "request_count": 1, "retry_after_seconds": 0}])


class _BrokenRpcDb:
    def rpc(self, _name: str, _params: dict[str, Any]) -> _RpcQuery:
        raise RuntimeError("distributed store unavailable")


class _SharedRpcStore:
    def __init__(self) -> None:
        self.counts: dict[tuple[str, str], int] = {}
        self.calls: list[tuple[str, dict[str, Any]]] = []


class _SharedRpcDb:
    def __init__(self, store: _SharedRpcStore) -> None:
        self.store = store

    def rpc(self, name: str, params: dict[str, Any]) -> _RpcQuery:
        self.store.calls.append((name, params))
        key = (str(params["p_rule_name"]), str(params["p_subject_hash"]))
        max_requests = int(params["p_max_requests"])
        current_count = self.store.counts.get(key, 0)
        if current_count >= max_requests:
            return _RpcQuery(
                [
                    {
                        "allowed": False,
                        "request_count": current_count,
                        "retry_after_seconds": 60,
                    }
                ]
            )
        next_count = current_count + 1
        self.store.counts[key] = next_count
        return _RpcQuery(
            [
                {
                    "allowed": True,
                    "request_count": next_count,
                    "retry_after_seconds": 0,
                }
            ]
        )


def test_supabase_rate_limiter_uses_rpc_with_hashed_subject() -> None:
    db = _RpcDb()
    limiter = SupabaseRateLimiter(db_factory=lambda: db, subject_salt="unit")
    rule = RateLimitRule(
        name="public_invoice",
        method="GET",
        path_prefix="/api/v1/public/invoices/",
        max_requests=2,
        window_seconds=60,
    )

    decision = limiter.check(rule=rule, subject="203.0.113.12")

    assert decision.allowed is True
    assert decision.backend == "supabase"
    assert decision.remaining == 1
    assert db.calls[0][0] == "check_rate_limit"
    params = db.calls[0][1]
    assert params["p_rule_name"] == "public_invoice"
    assert params["p_subject_hash"] != "203.0.113.12"
    assert len(params["p_subject_hash"]) == 64


def test_supabase_rate_limiter_shares_state_across_simulated_app_instances() -> None:
    store = _SharedRpcStore()
    rule = RateLimitRule(
        name="public_invoice",
        method="GET",
        path_prefix="/api/v1/public/invoices/",
        max_requests=2,
        window_seconds=60,
    )
    app_instance_a = SupabaseRateLimiter(
        db_factory=lambda: _SharedRpcDb(store),
        subject_salt="shared-test",
    )
    app_instance_b = SupabaseRateLimiter(
        db_factory=lambda: _SharedRpcDb(store),
        subject_salt="shared-test",
    )

    first = app_instance_a.check(rule=rule, subject="198.51.100.10")
    second = app_instance_b.check(rule=rule, subject="198.51.100.10")
    blocked = app_instance_a.check(rule=rule, subject="198.51.100.10")

    assert first.allowed is True
    assert first.backend == "supabase"
    assert second.allowed is True
    assert second.remaining == 0
    assert blocked.allowed is False
    assert blocked.backend == "supabase"
    assert blocked.retry_after_seconds == 60
    subject_hashes = {params["p_subject_hash"] for _, params in store.calls}
    assert len(subject_hashes) == 1
    assert "198.51.100.10" not in str(store.calls)


def test_supabase_rate_limiter_falls_back_to_memory_when_rpc_fails() -> None:
    global_telemetry.reset()
    limiter = SupabaseRateLimiter(
        db_factory=lambda: _BrokenRpcDb(),
        fallback_limiter=InMemoryRateLimiter(),
    )
    rule = RateLimitRule(
        name="signup",
        method="POST",
        path_prefix="/api/v1/auth/signup",
        max_requests=1,
        window_seconds=60,
    )

    first = limiter.check(rule=rule, subject="127.0.0.1")
    second = limiter.check(rule=rule, subject="127.0.0.1")
    snapshot = global_telemetry.snapshot()
    global_telemetry.reset()

    assert first.allowed is True
    assert first.backend == "memory"
    assert first.fallback_used is True
    assert second.allowed is False
    assert second.retry_after_seconds > 0
    assert snapshot["background_failures"][0] == {
        "worker_name": "rate_limit_distributed_backend",
        "count": 2,
    }


def test_supabase_rate_limiter_denies_safely_when_rpc_fails_without_fallback() -> None:
    global_telemetry.reset()
    limiter = SupabaseRateLimiter(
        db_factory=lambda: _BrokenRpcDb(),
        fallback_enabled=False,
    )
    rule = RateLimitRule(
        name="signup",
        method="POST",
        path_prefix="/api/v1/auth/signup",
        max_requests=10,
        window_seconds=60,
    )

    try:
        decision = limiter.check(rule=rule, subject="127.0.0.1")
        snapshot = global_telemetry.snapshot()
    finally:
        global_telemetry.reset()

    assert decision.allowed is False
    assert decision.backend == "supabase"
    assert decision.fallback_used is False
    assert decision.retry_after_seconds == 1
    assert snapshot["background_failures"] == [
        {"worker_name": "rate_limit_distributed_backend", "count": 1}
    ]


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
    assert summary["rate_limit"]["backend"] in {"memory", "supabase"}
    assert all(check["status"] == "ok" for check in summary["checks"]["tables"])
    assert summary["telemetry"]["failed_agent_runs_24h"] == 1
    assert summary["telemetry"]["failed_tool_invocations_24h"] == 1
    assert summary["telemetry"]["failed_tools_by_name_24h"] == [
        {"tool_name": "send_email", "count": 1}
    ]
    assert {item["code"] for item in summary["alerts"]["items"]} >= {
        "tenant_health_degraded",
        "agent_failure_spike",
    }


def test_tenant_health_alerts_route_without_raw_sensitive_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ops_alert_rate_limit_threshold", 1)
    monkeypatch.setattr(settings, "ops_alert_background_failure_threshold", 1)
    monkeypatch.setattr(settings, "ops_alert_webhook_url", "")
    raw_token = "token_1234567890abcdef"
    global_telemetry.reset()
    global_telemetry.record_request_failure(
        method="GET",
        path=f"/api/v1/public/invoices/{raw_token}",
        status_code=429,
    )
    global_telemetry.record_background_failure("close_scheduler_worker")

    try:
        summary = TenantHealthService(_Db(), "tenant-1").summary()  # type: ignore[arg-type]
    finally:
        global_telemetry.reset()

    codes = {item["code"] for item in summary["alerts"]["items"]}
    assert summary["alerts"]["route"]["route_type"] == "runbook_queue"
    assert {"public_endpoint_abuse", "background_failure_spike"} <= codes
    assert raw_token not in str(summary)
    assert "jwt" not in str(summary).lower()


def test_tenant_health_alert_route_hides_configured_webhook_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    webhook_url = "https://hooks.example.test/secret-token"
    monkeypatch.setattr(settings, "ops_alert_channel", "secops")
    monkeypatch.setattr(settings, "ops_alert_webhook_url", webhook_url)

    summary = TenantHealthService(_Db(), "tenant-1").summary()  # type: ignore[arg-type]

    assert summary["alerts"]["route"] == {
        "route_type": "webhook",
        "channel": "secops",
        "configured": True,
    }
    assert webhook_url not in str(summary)
    assert "secret-token" not in str(summary)


def test_tenant_health_routes_all_ops_alert_classes_without_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    webhook_url = "https://hooks.example.test/ops-secret-token"
    raw_invoice_token = "token_1234567890abcdef"
    monkeypatch.setattr(settings, "ops_alert_channel", "secops")
    monkeypatch.setattr(settings, "ops_alert_webhook_url", webhook_url)
    monkeypatch.setattr(settings, "ops_alert_rate_limit_threshold", 1)
    monkeypatch.setattr(settings, "ops_alert_background_failure_threshold", 1)
    monkeypatch.setattr(settings, "ops_alert_agent_failure_threshold", 1)
    fake_db = _Db()
    fake_db.tables["agent_workflow_runs"] = [
        {"id": "workflow-1", "tenant_id": "tenant-1", "status": "failed"}
    ]
    global_telemetry.reset()
    global_telemetry.record_request_failure(
        method="GET",
        path=f"/api/v1/public/invoices/{raw_invoice_token}",
        status_code=429,
    )
    global_telemetry.record_background_failure("rate_limit_distributed_backend")

    try:
        summary = TenantHealthService(fake_db, "tenant-1").summary()  # type: ignore[arg-type]
    finally:
        global_telemetry.reset()

    codes = {item["code"] for item in summary["alerts"]["items"]}
    assert {
        "tenant_health_degraded",
        "public_endpoint_abuse",
        "background_failure_spike",
        "agent_failure_spike",
    } <= codes
    assert summary["alerts"]["route"] == {
        "route_type": "webhook",
        "channel": "secops",
        "configured": True,
    }
    assert summary["telemetry"]["failed_workflow_runs_24h"] == 1
    assert raw_invoice_token not in str(summary)
    assert "ops-secret-token" not in str(summary)
    assert "jwt" not in str(summary).lower()
    assert "sk_live" not in str(summary).lower()


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
    assert body["alerts"]["route"]["channel"] == "runbook"
    assert "token_1234567890abcdef" not in response.text


def test_finance_persona_catalog_is_viewer_readable() -> None:
    main_app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="viewer-1",
        email="viewer@example.com",
        role="viewer",
    )
    main_app.dependency_overrides[get_service_role_client] = lambda: _Db()

    try:
        with TestClient(main_app) as client:
            response = client.get("/api/v1/tenants/finance-personas")
    finally:
        main_app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert {item["id"] for item in items} >= {"ap_lead", "ar_lead", "controller"}
    auditor = next(item for item in items if item["id"] == "auditor")
    assert auditor["mapped_roles"] == ["viewer"]
    assert auditor["read_only"] is True

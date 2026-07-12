"""Reports API contract tests for RLS-backed read dependency wiring."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.tenant import get_tenant_id
from app.main import app

pytestmark = pytest.mark.unit

TENANT_ID = "11111111-1111-1111-1111-111111111111"
OTHER_TENANT_ID = "22222222-2222-2222-2222-222222222222"


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _FakeDb, table: str) -> None:
        self.db = db
        self.table = table
        self._eq_filters: list[tuple[str, Any]] = []
        self._in_filters: list[tuple[str, list[Any]]] = []
        self._null_filters: list[str] = []

    def select(self, _columns: str = "*", **_kwargs: Any) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._eq_filters.append((key, value))
        return self

    def in_(self, key: str, values: list[Any]) -> _Query:
        self._in_filters.append((key, values))
        return self

    def is_(self, key: str, value: Any) -> _Query:
        if value == "null":
            self._null_filters.append(key)
        return self

    def execute(self) -> _Result:
        rows = [row for row in self.db.tables[self.table] if self._matches(row)]
        return _Result(deepcopy(rows))

    def _matches(self, row: dict[str, Any]) -> bool:
        for key, value in self._eq_filters:
            if row.get(key) != value:
                return False
        for key, values in self._in_filters:
            if row.get(key) not in values:
                return False
        for key in self._null_filters:
            if row.get(key) is not None:
                return False
        return True


class _FakeDb:
    def __init__(self) -> None:
        due_date = (date.today() - timedelta(days=10)).isoformat()
        self.tables: dict[str, list[dict[str, Any]]] = {
            "journal_lines": [
                {
                    "tenant_id": TENANT_ID,
                    "direction": "DR",
                    "base_amount": "250.00",
                    "journal_entries": {
                        "period": date.today().strftime("%Y-%m"),
                        "entry_date": date.today().isoformat(),
                        "posted_at": f"{date.today().isoformat()}T01:00:00+00:00",
                        "reference_type": "invoice",
                        "reference_id": "invoice-1",
                    },
                    "accounts": {"code": "1200"},
                },
                {
                    "tenant_id": OTHER_TENANT_ID,
                    "direction": "DR",
                    "base_amount": "999.00",
                    "journal_entries": {
                        "period": date.today().strftime("%Y-%m"),
                        "entry_date": date.today().isoformat(),
                        "posted_at": f"{date.today().isoformat()}T01:00:00+00:00",
                        "reference_type": "invoice",
                        "reference_id": "invoice-foreign",
                    },
                    "accounts": {"code": "1200"},
                },
            ],
            "invoices": [
                {
                    "id": "invoice-1",
                    "tenant_id": TENANT_ID,
                    "total": "250.00",
                    "currency": "USD",
                    "due_date": due_date,
                    "status": "approved",
                    "deleted_at": None,
                },
                {
                    "id": "invoice-foreign",
                    "tenant_id": OTHER_TENANT_ID,
                    "total": "999.00",
                    "currency": "USD",
                    "due_date": due_date,
                    "status": "approved",
                    "deleted_at": None,
                },
            ],
            "tenants": [
                {
                    "id": TENANT_ID,
                    "country": "GB",
                    "base_currency": "GBP",
                    "timezone": "Europe/London",
                    "locale": "en-GB",
                }
            ],
        }

    def table(self, name: str) -> _Query:
        assert name in self.tables
        return _Query(self, name)


class _ForbiddenDb:
    def table(self, name: str) -> None:
        raise AssertionError(f"wrong dependency attempted to access {name}")


def test_reports_router_uses_rls_client() -> None:
    fake_db = _FakeDb()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="viewer@example.com",
        role="viewer",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/reports/ar-aging")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json()["total"] == "250.00"


def test_action_queue_route_uses_rls_client(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_db = _FakeDb()

    class _FakeReportsService:
        def __init__(self, db: object, tenant_id: str) -> None:
            assert db is fake_db
            assert tenant_id == TENANT_ID

        def action_queue(
            self,
            *,
            role: str,
            period_start: str | None,
            period_end: str | None,
            limit: int,
            assignee_user_id: str | None,
            include_unassigned: bool,
        ) -> list[dict[str, Any]]:
            assert role == "partner"
            assert period_start is None
            assert period_end is None
            assert limit == 5
            assert assignee_user_id == "user-1"
            assert include_unassigned is False
            return [
                {
                    "id": "partner:practice_dashboard:practice:advisory",
                    "role": "partner",
                    "source_type": "practice_dashboard",
                    "priority": "critical",
                    "entity_type": "practice",
                    "entity_id": "advisory",
                    "entity_name": "Advisory",
                    "summary": "Advisory needs partner review.",
                    "recommended_action": "Run partner recovery review.",
                    "evidence": ["Critical projects: 1."],
                    "metrics": {"critical_project_count": 1},
                    "route_hint": "/app/reports",
                }
            ]

    monkeypatch.setattr(
        "app.api.v1.endpoints.reports.ReportsService",
        _FakeReportsService,
    )
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="viewer@example.com",
        role="viewer",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/reports/action-queue?role=partner&limit=5&assignee=me"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json()[0]["role"] == "partner"


def test_balance_sheet_route_uses_rls_client(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_db = _FakeDb()

    class _FakeReportsService:
        def __init__(self, db: object, tenant_id: str) -> None:
            assert db is fake_db
            assert tenant_id == TENANT_ID

        def balance_sheet(self, *, as_of_period: str | None) -> dict[str, Any]:
            assert as_of_period == "2026-06"
            return {
                "as_of_period": "2026-06",
                "asset_lines": [],
                "liability_lines": [],
                "equity_lines": [],
                "total_assets": "0.00",
                "total_liabilities": "0.00",
                "total_equity": "0.00",
                "liabilities_and_equity": "0.00",
                "is_balanced": True,
                "generated_at": "2026-06-23T00:00:00+00:00",
            }

    monkeypatch.setattr(
        "app.api.v1.endpoints.reports.ReportsService",
        _FakeReportsService,
    )
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="viewer@example.com",
        role="viewer",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/reports/balance-sheet?as_of_period=2026-06")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json()["is_balanced"] is True


def test_retained_earnings_route_uses_rls_client(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_db = _FakeDb()

    class _FakeReportsService:
        def __init__(self, db: object, tenant_id: str) -> None:
            assert db is fake_db
            assert tenant_id == TENANT_ID

        def retained_earnings_roll_forward(self, *, period: str) -> dict[str, Any]:
            assert period == "2026-06"
            return {
                "period": "2026-06",
                "previous_period": "2026-05",
                "beginning_retained_earnings": "1000.00",
                "current_period_net_income": "600.00",
                "retained_earnings_activity": "-100.00",
                "ending_retained_earnings": "1500.00",
                "generated_at": "2026-06-23T00:00:00+00:00",
            }

    monkeypatch.setattr(
        "app.api.v1.endpoints.reports.ReportsService",
        _FakeReportsService,
    )
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="viewer@example.com",
        role="viewer",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/reports/retained-earnings-roll-forward?period=2026-06")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json()["ending_retained_earnings"] == "1500.00"


def test_statutory_pack_route_uses_rls_client_and_tenant_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_rls_db = _FakeDb()
    fake_tenant_db = _FakeDb()

    class _FakeReportsService:
        def __init__(self, db: object, tenant_id: str) -> None:
            assert db is fake_rls_db
            assert tenant_id == TENANT_ID

        def statutory_reporting_pack(
            self,
            *,
            period_start: str,
            period_end: str,
            tenant_metadata: dict[str, Any],
        ) -> dict[str, Any]:
            assert period_start == "2026-06"
            assert period_end == "2026-06"
            assert tenant_metadata["country"] == "GB"
            assert tenant_metadata["base_currency"] == "GBP"
            generated_at = "2026-06-23T00:00:00+00:00"
            return {
                "period_start": "2026-06",
                "period_end": "2026-06",
                "as_of_period": "2026-06",
                "country": "GB",
                "market": "UK",
                "base_currency": "GBP",
                "locale": "en-GB",
                "timezone": "Europe/London",
                "tax_label": "VAT",
                "tax_authority_label": "HMRC",
                "tax_collection_model": "vat",
                "reporting_periods": ["monthly", "quarterly", "annual"],
                "trial_balance": {
                    "as_of_period": "2026-06",
                    "lines": [],
                    "grand_total_dr": "0.00",
                    "grand_total_cr": "0.00",
                    "is_balanced": True,
                    "generated_at": generated_at,
                },
                "balance_sheet": {
                    "as_of_period": "2026-06",
                    "asset_lines": [],
                    "liability_lines": [],
                    "equity_lines": [],
                    "total_assets": "0.00",
                    "total_liabilities": "0.00",
                    "total_equity": "0.00",
                    "liabilities_and_equity": "0.00",
                    "is_balanced": True,
                    "generated_at": generated_at,
                },
                "income_statement": {
                    "period_start": "2026-06",
                    "period_end": "2026-06",
                    "revenue_lines": [],
                    "expense_lines": [],
                    "total_revenue": "0.00",
                    "total_expenses": "0.00",
                    "net_income": "0.00",
                    "generated_at": generated_at,
                },
                "cash_flow": {
                    "period_start": "2026-06",
                    "period_end": "2026-06",
                    "operating_lines": [],
                    "investing_lines": [],
                    "financing_lines": [],
                    "net_cash_from_operating": "0.00",
                    "net_cash_from_investing": "0.00",
                    "net_cash_from_financing": "0.00",
                    "net_change_in_cash": "0.00",
                    "beginning_cash": "0.00",
                    "ending_cash": "0.00",
                    "generated_at": generated_at,
                },
                "retained_earnings_roll_forward": {
                    "period": "2026-06",
                    "previous_period": "2026-05",
                    "beginning_retained_earnings": "0.00",
                    "current_period_net_income": "0.00",
                    "retained_earnings_activity": "0.00",
                    "ending_retained_earnings": "0.00",
                    "generated_at": generated_at,
                },
                "tax_summary": {
                    "tax_label": "VAT",
                    "tax_authority_label": "HMRC",
                    "base_currency": "GBP",
                    "transaction_currency_buckets": [],
                    "ledger_output_tax_payable_balance": "0.00",
                    "ledger_input_tax_recoverable_balance": "0.00",
                    "ledger_net_tax_payable": "0.00",
                },
                "generated_at": generated_at,
            }

    monkeypatch.setattr(
        "app.api.v1.endpoints.reports.ReportsService",
        _FakeReportsService,
    )
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="viewer@example.com",
        role="viewer",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: fake_rls_db
    app.dependency_overrides[get_service_role_client] = lambda: fake_tenant_db

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/reports/statutory-pack?period_start=2026-06")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json()["market"] == "UK"
    assert response.json()["tax_label"] == "VAT"


def test_backlog_forecast_route_uses_rls_client(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_db = _FakeDb()

    class _FakeReportsService:
        def __init__(self, db: object, tenant_id: str) -> None:
            assert db is fake_db
            assert tenant_id == TENANT_ID

        def backlog_forecast(self) -> list[dict[str, Any]]:
            return [
                {
                    "engagement_id": "eng-risk",
                    "engagement_name": "Risky Transformation",
                    "client_name": "Acme Corp",
                    "contracted_value": "10000.00",
                    "recognized_backlog": "4000.00",
                    "risk_level": "critical",
                }
            ]

    monkeypatch.setattr(
        "app.api.v1.endpoints.reports.ReportsService",
        _FakeReportsService,
    )
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="viewer@example.com",
        role="viewer",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/reports/backlog-forecast")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json()[0]["risk_level"] == "critical"

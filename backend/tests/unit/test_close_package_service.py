"""Unit tests for composed financial close packages."""

from __future__ import annotations

from typing import Any

import pytest

from app.services.close_package_service import (
    ClosePackageService,
    period_bounds,
    previous_period_for,
)

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-close-package-001"


class _Result:
    def __init__(self, data: list[dict]) -> None:
        self.data = data


class _Query:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows
        self._filters: list[tuple[str, Any]] = []

    def select(self, _columns: str) -> _Query:
        return self

    def eq(self, field: str, value: Any) -> _Query:
        self._filters.append((field, value))
        return self

    def execute(self) -> _Result:
        rows = self._rows
        for field, value in self._filters:
            rows = [row for row in rows if row.get(field) == value]
        return _Result(rows)


class _Db:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def table(self, name: str) -> _Query:
        assert name == "journal_lines"
        return _Query(self.rows)


class _TrialBalance:
    def model_dump(self, *, mode: str = "python") -> dict[str, object]:
        assert mode == "json"
        return {
            "as_of_period": "2026-06",
            "grand_total_dr": "1600.00",
            "grand_total_cr": "1600.00",
            "is_balanced": True,
            "lines": [],
            "generated_at": "2026-06-30T23:59:00+00:00",
        }


class _Reports:
    def trial_balance(self, *, as_of_period: str | None = None) -> _TrialBalance:
        assert as_of_period == "2026-06"
        return _TrialBalance()

    def ar_aging(self) -> dict[str, str]:
        return {"0_30": "250.00", "31_60": "0.00", "61_90": "0.00", "over_90": "0.00", "total": "250.00"}

    def ap_aging(self) -> dict[str, str]:
        return {"0_30": "100.00", "31_60": "0.00", "61_90": "0.00", "over_90": "0.00", "total": "100.00"}

    def wip(self) -> list[dict]:
        return [
            {"project_id": "project-1", "project_name": "Advisory", "wip_value": "350.00"}
        ]

    def margin_by_service_line(self, period: str | None = None) -> list[dict]:
        assert period == "2026-06"
        return [
            {
                "service_line": "advisory",
                "label": "Advisory",
                "revenue": "1000.00",
                "cost": "600.00",
                "gross_margin": "400.00",
                "margin_pct": 40.0,
            }
        ]


class _Status:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def as_dict(self) -> dict[str, object]:
        return self.payload


class _CloseStatus:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def get_status(self, period: str) -> _Status:
        assert period == "2026-06"
        return _Status(self.payload)


def _line(
    *,
    direction: str,
    amount: str,
    period: str,
    account_type: str,
    code: str,
    posted: bool = True,
) -> dict:
    return {
        "tenant_id": TENANT_ID,
        "direction": direction,
        "base_amount": amount,
        "journal_entries": {
            "period": period,
            "posted_at": f"{period}-15T00:00:00+00:00" if posted else None,
        },
        "accounts": {
            "code": code,
            "account_type": account_type,
        },
    }


def _service(status_payload: dict[str, object]) -> ClosePackageService:
    rows = [
        _line(direction="CR", amount="1000.00", period="2026-06", account_type="revenue", code="4000"),
        _line(direction="DR", amount="600.00", period="2026-06", account_type="expense", code="5000"),
        _line(direction="CR", amount="800.00", period="2026-05", account_type="revenue", code="4000"),
        _line(direction="DR", amount="500.00", period="2026-05", account_type="expense", code="5000"),
        _line(direction="CR", amount="999.00", period="2026-06", account_type="revenue", code="4000", posted=False),
        _line(direction="DR", amount="50.00", period="2026-06", account_type="asset", code="1200"),
    ]
    return ClosePackageService(
        _Db(rows),  # type: ignore[arg-type]
        TENANT_ID,
        reports_service=_Reports(),  # type: ignore[arg-type]
        close_status_service=_CloseStatus(status_payload),  # type: ignore[arg-type]
    )


def test_period_helpers_handle_year_boundary() -> None:
    bounds = period_bounds("2026-02")

    assert bounds.start == "2026-02-01"
    assert bounds.end == "2026-02-28"
    assert previous_period_for("2026-01") == "2025-12"


def test_close_package_composes_reports_and_variance_commentary() -> None:
    package = _service(
        {"status": "ready", "ready_to_lock": True, "lock_blockers": []}
    ).build_package("2026-06")

    assert package["period_start"] == "2026-06-01"
    assert package["period_end"] == "2026-06-30"
    assert package["previous_period"] == "2026-05"
    assert package["gl_summary"]["revenue"] == "1000.00"
    assert package["gl_summary"]["expenses"] == "600.00"
    assert package["gl_summary"]["net_income"] == "400.00"
    assert package["previous_gl_summary"]["net_income"] == "300.00"
    assert package["working_capital"] == {
        "ar_open_total": "250.00",
        "ap_open_total": "100.00",
        "wip_total": "350.00",
    }
    evidence = package["readiness_evidence"]
    assert evidence["ar"]["open_total"] == "250.00"
    assert evidence["ap"]["open_total"] == "100.00"
    assert evidence["wip"]["project_count"] == 1
    assert evidence["gl"]["trial_balance_balanced"] is True
    assert evidence["approvals"]["pending_review_count"] == 0
    assert package["close_overrides"] == []

    commentary = {row["code"]: row for row in package["variance_commentary"]}
    assert commentary["revenue_variance"]["delta_pct"] == 25.0
    assert commentary["revenue_variance"]["evidence"]["source"] == "period_gl_summary"
    assert commentary["net_income_variance"]["delta"] == "100.00"
    assert commentary["working_capital"]["net_exposure"] == "500.00"
    assert commentary["working_capital"]["evidence"]["ar_open_total"] == "250.00"
    assert commentary["service_line_mix"]["service_line"] == "advisory"
    assert "close_blockers" not in commentary


def test_close_package_surfaces_close_blockers_first() -> None:
    package = _service(
        {
            "status": "blocked",
            "ready_to_lock": False,
            "lock_blockers": ["trial_balance", "close_reviews"],
        }
    ).build_package("2026-06")

    first = package["variance_commentary"][0]
    assert first["code"] == "close_blockers"
    assert first["severity"] == "blocker"
    assert first["metric"] == "trial_balance, close_reviews"


def test_close_package_surfaces_recorded_overrides() -> None:
    package = _service(
        {
            "status": "ready",
            "ready_to_lock": True,
            "lock_blockers": [],
            "overrides": [
                {
                    "id": "override-001",
                    "period": "2026-06",
                    "blocker_code": "unposted_journals",
                    "reason": "Controller approved excluding a draft reversal.",
                    "created_by": "controller-1",
                    "created_at": "2026-06-30T23:00:00+00:00",
                    "blocker_ref": {"journal_entry_id": "journal-draft-001"},
                }
            ],
        }
    ).build_package("2026-06")

    assert package["close_overrides"][0]["blocker_code"] == "unposted_journals"
    assert package["readiness_evidence"]["overrides"]["count"] == 1
    first = package["variance_commentary"][0]
    assert first["code"] == "close_overrides"
    assert first["severity"] == "watch"
    assert first["evidence"]["overrides"][0]["created_by"] == "controller-1"

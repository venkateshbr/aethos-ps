"""Unit tests for year-end close retained-earnings posting."""

from __future__ import annotations

from typing import Any

import pytest

from app.services.year_end_close_service import YearEndCloseError, YearEndCloseService

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-year-end-close-001"
USER_ID = "controller-001"


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.eq_filters: list[tuple[str, Any]] = []
        self.gte_filters: list[tuple[str, Any]] = []
        self.lte_filters: list[tuple[str, Any]] = []
        self.null_filters: list[str] = []

    def select(self, _columns: str) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self.eq_filters.append((key, value))
        return self

    def gte(self, key: str, value: Any) -> _Query:
        self.gte_filters.append((key, value))
        return self

    def lte(self, key: str, value: Any) -> _Query:
        self.lte_filters.append((key, value))
        return self

    def is_(self, key: str, value: Any) -> _Query:
        if value == "null":
            self.null_filters.append(key)
        return self

    def execute(self) -> _Result:
        rows = [
            row
            for row in self.rows
            if all(row.get(key) == value for key, value in self.eq_filters)
            and all(str(row.get(key) or "") >= str(value) for key, value in self.gte_filters)
            and all(str(row.get(key) or "") <= str(value) for key, value in self.lte_filters)
            and all(row.get(key) is None for key in self.null_filters)
        ]
        return _Result(rows)


class _Db:
    def __init__(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        self.tables = tables

    def table(self, name: str) -> _Query:
        return _Query(self.tables.get(name, []))


def _line(
    *,
    direction: str,
    amount: str,
    code: str,
    name: str,
    account_type: str,
    period: str = "2026-06",
    posted: bool = True,
) -> dict[str, Any]:
    return {
        "tenant_id": TENANT_ID,
        "direction": direction,
        "base_amount": amount,
        "journal_entries": {
            "period": period,
            "posted_at": f"{period}-28T00:00:00+00:00" if posted else None,
        },
        "accounts": {
            "id": f"acct-{code}",
            "code": code,
            "name": name,
            "account_type": account_type,
        },
    }


def _db(*, lines: list[dict[str, Any]], accounts: list[dict[str, Any]] | None = None) -> _Db:
    return _Db(
        {
            "period_locks": [],
            "journal_entries": [],
            "journal_lines": lines,
            "accounts": accounts
            if accounts is not None
            else [
                {
                    "id": "acct-3000",
                    "tenant_id": TENANT_ID,
                    "code": "3000",
                    "name": "Retained Earnings",
                    "account_type": "equity",
                    "deleted_at": None,
                }
            ],
        }
    )


def test_posts_balanced_year_end_close_for_net_income(monkeypatch: pytest.MonkeyPatch) -> None:
    posted: dict[str, Any] = {}

    def _post_journal(**kwargs: Any) -> dict[str, Any]:
        posted.update(kwargs)
        return {
            "id": "journal-year-end-2026",
            "entry_number": "YE-2026",
            "posted_at": "2026-12-31T23:59:00+00:00",
        }

    monkeypatch.setattr("app.services.year_end_close_service.post_journal", _post_journal)
    svc = YearEndCloseService(
        _db(
            lines=[
                _line(direction="CR", amount="1200.00", code="4000", name="Revenue", account_type="revenue"),
                _line(direction="DR", amount="300.00", code="5000", name="Expenses", account_type="expense"),
                _line(direction="CR", amount="999.00", code="4000", name="Revenue", account_type="revenue", posted=False),
            ],
        ),  # type: ignore[arg-type]
        TENANT_ID,
        USER_ID,
    )

    result = svc.post_year_end_close(2026)

    assert result["net_income"] == "900.00"
    assert result["retained_earnings_direction"] == "CR"
    assert result["retained_earnings_amount"] == "900.00"
    assert result["revenue_closed"] == "1200.00"
    assert result["expenses_closed"] == "300.00"
    assert posted["tenant_id"] == TENANT_ID
    assert posted["created_by"] == USER_ID
    assert posted["entry_date"] == "2026-12-31"
    assert posted["reference_type"] == "year_end_close"
    lines = posted["lines"]
    assert [(line.account_code, line.direction, str(line.amount)) for line in lines] == [
        ("4000", "DR", "1200.00"),
        ("5000", "CR", "300.00"),
        ("3000", "CR", "900.00"),
    ]


def test_previews_year_end_close_without_posting(monkeypatch: pytest.MonkeyPatch) -> None:
    def _post_journal(**_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("preview must not post a journal")

    monkeypatch.setattr("app.services.year_end_close_service.post_journal", _post_journal)
    svc = YearEndCloseService(
        _db(
            lines=[
                _line(direction="CR", amount="1200.00", code="4000", name="Revenue", account_type="revenue"),
                _line(direction="DR", amount="300.00", code="5000", name="Expenses", account_type="expense"),
            ],
        ),  # type: ignore[arg-type]
        TENANT_ID,
        USER_ID,
    )

    preview = svc.preview_year_end_close(2026)

    assert preview["ready_to_post"] is True
    assert preview["workflow"] == "year_end_close"
    assert preview["period"] == "2026-12"
    assert preview["net_income"] == "900.00"
    assert preview["retained_earnings_direction"] == "CR"
    assert preview["retained_earnings_amount"] == "900.00"
    assert preview["retained_earnings_account"]["code"] == "3000"
    assert preview["line_count"] == 3
    assert [account["code"] for account in preview["closing_accounts"]] == ["4000", "5000"]


def test_posts_retained_earnings_debit_for_net_loss(monkeypatch: pytest.MonkeyPatch) -> None:
    posted: dict[str, Any] = {}

    def _post_journal(**kwargs: Any) -> dict[str, Any]:
        posted.update(kwargs)
        return {
            "id": "journal-year-end-loss",
            "entry_number": "YE-2026",
            "posted_at": "2026-12-31T23:59:00+00:00",
        }

    monkeypatch.setattr("app.services.year_end_close_service.post_journal", _post_journal)
    svc = YearEndCloseService(
        _db(
            lines=[
                _line(direction="CR", amount="200.00", code="4000", name="Revenue", account_type="revenue"),
                _line(direction="DR", amount="700.00", code="5000", name="Expenses", account_type="expense"),
            ],
        ),  # type: ignore[arg-type]
        TENANT_ID,
        USER_ID,
    )

    result = svc.post_year_end_close(2026)

    assert result["net_income"] == "-500.00"
    assert result["retained_earnings_direction"] == "DR"
    assert [(line.account_code, line.direction, str(line.amount)) for line in posted["lines"]] == [
        ("4000", "DR", "200.00"),
        ("5000", "CR", "700.00"),
        ("3000", "DR", "500.00"),
    ]


def test_rejects_duplicate_year_end_close() -> None:
    db = _db(lines=[])
    db.tables["journal_entries"] = [
        {
            "id": "journal-existing",
            "tenant_id": TENANT_ID,
            "period": "2026-12",
            "reference_type": "year_end_close",
            "entry_number": "YE-2026",
            "posted_at": "2026-12-31T23:59:00+00:00",
        }
    ]
    svc = YearEndCloseService(db, TENANT_ID, USER_ID)  # type: ignore[arg-type]

    with pytest.raises(YearEndCloseError) as exc:
        svc.post_year_end_close(2026)

    assert exc.value.code == "year_end_close_already_posted"
    assert exc.value.status_code == 409
    assert exc.value.detail["journal_entry_id"] == "journal-existing"


def test_rejects_when_fiscal_year_period_is_locked() -> None:
    db = _db(lines=[])
    db.tables["period_locks"] = [
        {"tenant_id": TENANT_ID, "period": "2026-05"},
        {"tenant_id": "other", "period": "2026-06"},
    ]
    svc = YearEndCloseService(db, TENANT_ID, USER_ID)  # type: ignore[arg-type]

    with pytest.raises(YearEndCloseError) as exc:
        svc.post_year_end_close(2026)

    assert exc.value.code == "year_end_close_period_locked"
    assert exc.value.status_code == 409
    assert exc.value.detail["locked_periods"] == ["2026-05"]


def test_rejects_when_retained_earnings_account_is_missing() -> None:
    svc = YearEndCloseService(
        _db(
            accounts=[],
            lines=[
                _line(direction="CR", amount="200.00", code="4000", name="Revenue", account_type="revenue"),
            ],
        ),  # type: ignore[arg-type]
        TENANT_ID,
        USER_ID,
    )

    with pytest.raises(YearEndCloseError) as exc:
        svc.post_year_end_close(2026)

    assert exc.value.code == "retained_earnings_account_missing"


def test_rejects_when_there_is_no_posted_pnl_activity() -> None:
    svc = YearEndCloseService(
        _db(
            lines=[
                _line(direction="DR", amount="200.00", code="1100", name="Bank", account_type="asset"),
            ],
        ),  # type: ignore[arg-type]
        TENANT_ID,
        USER_ID,
    )

    with pytest.raises(YearEndCloseError) as exc:
        svc.post_year_end_close(2026)

    assert exc.value.code == "year_end_close_no_activity"


def test_preview_surfaces_blockers_without_raising() -> None:
    db = _db(accounts=[], lines=[])
    db.tables["period_locks"] = [{"tenant_id": TENANT_ID, "period": "2026-05"}]
    db.tables["journal_entries"] = [
        {
            "id": "journal-existing",
            "tenant_id": TENANT_ID,
            "period": "2026-12",
            "reference_type": "year_end_close",
            "entry_number": "YE-2026",
            "posted_at": "2026-12-31T23:59:00+00:00",
        }
    ]
    svc = YearEndCloseService(db, TENANT_ID, USER_ID)  # type: ignore[arg-type]

    preview = svc.preview_year_end_close(2026)

    assert preview["ready_to_post"] is False
    assert preview["blocker_count"] == 4
    assert [blocker["code"] for blocker in preview["blockers"]] == [
        "year_end_close_period_locked",
        "year_end_close_already_posted",
        "retained_earnings_account_missing",
        "year_end_close_no_activity",
    ]
    assert preview["duplicate_journal"]["journal_entry_id"] == "journal-existing"

"""Unit tests for fx_remeasurement_agent — period-end unrealized FX (#376)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from app.agents.base import AgentDeps
from app.agents.fx_remeasurement_agent import (
    FxRemeasurementProposalError,
    build_fx_remeasurement_proposals,
)

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-fx-001"


class _Result:
    def __init__(self, data: list[dict]) -> None:
        self.data = data


class _Query:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = list(rows)
        self._filters: list[tuple[str, str, Any]] = []
        self._order: tuple[str, bool] | None = None
        self._limit: int | None = None

    def select(self, _columns: str) -> _Query:
        return self

    def eq(self, field: str, value: Any) -> _Query:
        self._filters.append(("eq", field, value))
        return self

    def neq(self, field: str, value: Any) -> _Query:
        self._filters.append(("neq", field, value))
        return self

    def in_(self, field: str, values: list[Any]) -> _Query:
        self._filters.append(("in", field, values))
        return self

    def is_(self, field: str, value: str) -> _Query:
        self._filters.append(("is", field, value))
        return self

    def lte(self, field: str, value: Any) -> _Query:
        self._filters.append(("lte", field, value))
        return self

    def order(self, field: str, desc: bool = False) -> _Query:
        self._order = (field, desc)
        return self

    def limit(self, n: int) -> _Query:
        self._limit = n
        return self

    def _matches(self, row: dict) -> bool:
        for op, field, value in self._filters:
            current = row.get(field)
            if op == "eq" and current != value:
                return False
            if op == "neq" and current == value:
                return False
            if op == "in" and str(current) not in {str(v) for v in value}:
                return False
            if op == "is" and value == "null" and current is not None:
                return False
            if op == "lte" and str(current or "") > str(value):
                return False
        return True

    def execute(self) -> _Result:
        rows = [r for r in self._rows if self._matches(r)]
        if self._order is not None:
            field, desc = self._order
            rows.sort(key=lambda r: str(r.get(field) or ""), reverse=desc)
        if self._limit is not None:
            rows = rows[: self._limit]
        return _Result(rows)


class _Db:
    def __init__(self, tables: dict[str, list[dict]]) -> None:
        self.tables = tables

    def table(self, name: str) -> _Query:
        return _Query(self.tables.get(name, []))


def _deps(tables: dict[str, list[dict]]) -> AgentDeps:
    return AgentDeps(tenant_id=TENANT_ID, user_id="user-001", db=_Db(tables))  # type: ignore[arg-type]


def _accounts() -> list[dict]:
    return [
        {"tenant_id": TENANT_ID, "id": "ar", "code": "1200", "deleted_at": None},
        {"tenant_id": TENANT_ID, "id": "ap", "code": "2000", "deleted_at": None},
        {"tenant_id": TENANT_ID, "id": "ufx", "code": "7910", "deleted_at": None},
    ]


def _fx(rate: str, to_ccy: str = "USD", from_ccy: str = "GBP") -> list[dict]:
    return [{
        "id": "fx-1", "from_currency": from_ccy, "to_currency": to_ccy,
        "rate": rate, "rate_date": "2026-06-30", "source": "test",
    }]


def _base_tables(rate: str = "1.30") -> dict[str, list[dict]]:
    return {
        "tenants": [{"id": TENANT_ID, "base_currency": "USD"}],
        "accounts": _accounts(),
        "fx_rates": _fx(rate),
        "payments": [],
        "bill_payment_items": [],
        "invoices": [],
        "bills": [],
    }


def _invoice(**over: Any) -> dict:
    return {
        "tenant_id": TENANT_ID, "id": "inv-1", "currency": "GBP",
        "total": "1000.00", "base_total": "1250.00", "status": "sent",
        "issue_date": "2026-06-10", "paid_at": None, "deleted_at": None, **over,
    }


def _bill(**over: Any) -> dict:
    return {
        "tenant_id": TENANT_ID, "id": "bill-1", "currency": "GBP",
        "total": "1000.00", "base_total": "1250.00", "status": "approved",
        "issue_date": "2026-06-10", "paid_at": None, "deleted_at": None, **over,
    }


async def _build(tables: dict[str, list[dict]]):
    return await build_fx_remeasurement_proposals(_deps(tables), "2026-06")


@pytest.mark.asyncio
async def test_ar_unrealized_gain_debits_ar_credits_unrealized() -> None:
    tables = _base_tables(rate="1.30")  # booked 1.25, now 1.30 → GBP AR worth more
    tables["invoices"] = [_invoice()]
    props = await _build(tables)

    assert len(props) == 1
    p = props[0]
    assert p.balance_type == "AR"
    assert p.remeasured_base_amount == "1300.00"
    assert p.unrealized_gain_loss == "50.00"
    assert p.reverses_on == "2026-07-01"
    lines = p.journal_entry["lines"]
    dr = next(ln for ln in lines if ln["direction"] == "DR")
    cr = next(ln for ln in lines if ln["direction"] == "CR")
    assert dr["account_id"] == "ar" and dr["amount"] == "50.00"
    assert cr["account_id"] == "ufx" and cr["amount"] == "50.00"


@pytest.mark.asyncio
async def test_ar_unrealized_loss_debits_unrealized_credits_ar() -> None:
    tables = _base_tables(rate="1.20")  # 1.25 → 1.20, AR worth less
    tables["invoices"] = [_invoice()]
    props = await _build(tables)

    p = props[0]
    assert p.unrealized_gain_loss == "-50.00"
    dr = next(ln for ln in p.journal_entry["lines"] if ln["direction"] == "DR")
    cr = next(ln for ln in p.journal_entry["lines"] if ln["direction"] == "CR")
    assert dr["account_id"] == "ufx" and cr["account_id"] == "ar"


@pytest.mark.asyncio
async def test_ap_unrealized_loss_debits_unrealized_credits_ap() -> None:
    tables = _base_tables(rate="1.30")  # owe more base → loss on AP
    tables["bills"] = [_bill()]
    props = await _build(tables)

    p = next(pr for pr in props if pr.balance_type == "AP")
    assert p.unrealized_gain_loss == "50.00"
    dr = next(ln for ln in p.journal_entry["lines"] if ln["direction"] == "DR")
    cr = next(ln for ln in p.journal_entry["lines"] if ln["direction"] == "CR")
    assert dr["account_id"] == "ufx" and cr["account_id"] == "ap"


@pytest.mark.asyncio
async def test_journal_is_balanced() -> None:
    tables = _base_tables(rate="1.30")
    tables["invoices"] = [_invoice()]
    tables["bills"] = [_bill()]
    for p in await _build(tables):
        dr = sum(Decimal(ln["amount"]) for ln in p.journal_entry["lines"] if ln["direction"] == "DR")
        cr = sum(Decimal(ln["amount"]) for ln in p.journal_entry["lines"] if ln["direction"] == "CR")
        assert dr == cr


@pytest.mark.asyncio
async def test_immaterial_delta_skipped() -> None:
    tables = _base_tables(rate="1.2505")  # 1000*1.2505=1250.50 → delta 0.50 < 1.00
    tables["invoices"] = [_invoice()]
    assert await _build(tables) == []


@pytest.mark.asyncio
async def test_same_currency_balance_skipped() -> None:
    tables = _base_tables()
    tables["invoices"] = [_invoice(currency="USD", base_total="1000.00", total="1000.00")]
    assert await _build(tables) == []


@pytest.mark.asyncio
async def test_paid_invoice_skipped() -> None:
    tables = _base_tables(rate="1.30")
    tables["invoices"] = [_invoice()]
    tables["payments"] = [{"tenant_id": TENANT_ID, "invoice_id": "inv-1", "amount": "500.00"}]
    assert await _build(tables) == []  # has a payment → out of v1 scope


@pytest.mark.asyncio
async def test_draft_invoice_skipped() -> None:
    tables = _base_tables(rate="1.30")
    tables["invoices"] = [_invoice(status="draft")]
    assert await _build(tables) == []  # draft is not a posted AR balance


@pytest.mark.asyncio
async def test_missing_unrealized_account_raises() -> None:
    tables = _base_tables(rate="1.30")
    tables["accounts"] = [a for a in _accounts() if a["code"] != "7910"]
    tables["invoices"] = [_invoice()]
    with pytest.raises(FxRemeasurementProposalError, match="7910"):
        await _build(tables)

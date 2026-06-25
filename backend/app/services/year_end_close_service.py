"""Year-end close service for rolling P&L into retained earnings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from app.domain.journal_helper import JournalLineSpec, post_journal
from app.domain.money import serialise_money
from supabase import Client


class YearEndCloseError(ValueError):
    """Business-rule failure while preparing or posting year-end close."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 422,
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.detail = {
            "code": code,
            "message": message,
            **(detail or {}),
        }


@dataclass(frozen=True)
class ClosingAccount:
    id: str
    code: str
    name: str
    account_type: str
    balance: Decimal


@dataclass(frozen=True)
class YearEndCloseContext:
    year: int
    start_period: str
    end_period: str
    entry_date: str
    locked_periods: list[str]
    duplicate: dict[str, Any] | None
    retained_earnings: dict[str, Any] | None
    closing_accounts: list[ClosingAccount]

    @property
    def net_income(self) -> Decimal:
        return _net_income(self.closing_accounts)

    @property
    def revenue_closed(self) -> Decimal:
        return sum(
            row.balance for row in self.closing_accounts if row.account_type == "revenue"
        )

    @property
    def expenses_closed(self) -> Decimal:
        return sum(
            row.balance for row in self.closing_accounts if row.account_type == "expense"
        )

    @property
    def retained_direction(self) -> str | None:
        if self.net_income > Decimal("0"):
            return "CR"
        if self.net_income < Decimal("0"):
            return "DR"
        return None

    @property
    def retained_amount(self) -> Decimal:
        return abs(self.net_income)


class YearEndCloseService:
    """Prepare and post the annual closing journal for a tenant."""

    def __init__(self, db: Client, tenant_id: str, user_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    def preview_year_end_close(self, year: int) -> dict[str, Any]:
        """Return review evidence for year-end close without posting a journal."""
        context = self._context(year)
        return self._preview_payload(context)

    def post_year_end_close(self, year: int) -> dict[str, Any]:
        """Post the year-end close journal for ``year``.

        The journal zeros posted revenue and expense balances for January
        through December and offsets the net result to Retained Earnings.
        """
        context = self._context(year)
        self._raise_for_blocker(context)

        retained_earnings = context.retained_earnings
        if retained_earnings is None:
            raise AssertionError("retained earnings account unexpectedly missing")
        lines = self._closing_lines(context.closing_accounts)
        if context.retained_direction is not None:
            lines.append(
                JournalLineSpec(
                    direction=context.retained_direction,
                    account_code=str(retained_earnings["code"]),
                    account_id=str(retained_earnings["id"]),
                    amount=context.retained_amount,
                    base_amount=context.retained_amount,
                    description=f"Roll {context.year} net income to retained earnings",
                )
            )

        journal = post_journal(
            db=self.db,
            tenant_id=self.tenant_id,
            created_by=self.user_id,
            description=f"Year-end close {context.year}: roll P&L to retained earnings",
            entry_date=context.entry_date,
            reference_type="year_end_close",
            reference_id=None,  # type: ignore[arg-type]
            entry_number=f"YE-{context.year}",
            lines=lines,
        )

        return {
            "year": context.year,
            "period": context.end_period,
            "entry_date": context.entry_date,
            "journal_entry_id": str(journal["id"]),
            "entry_number": str(journal.get("entry_number") or f"YE-{context.year}"),
            "posted_at": str(journal.get("posted_at") or ""),
            "net_income": serialise_money(context.net_income),
            "retained_earnings_direction": context.retained_direction,
            "retained_earnings_amount": serialise_money(context.retained_amount),
            "retained_earnings_account": {
                "id": str(retained_earnings["id"]),
                "code": str(retained_earnings["code"]),
                "name": str(retained_earnings["name"]),
            },
            "revenue_closed": serialise_money(context.revenue_closed),
            "expenses_closed": serialise_money(context.expenses_closed),
            "line_count": len(lines),
        }

    def _context(self, year: int) -> YearEndCloseContext:
        start_period = f"{year}-01"
        end_period = f"{year}-12"
        return YearEndCloseContext(
            year=year,
            start_period=start_period,
            end_period=end_period,
            entry_date=date(year, 12, 31).isoformat(),
            locked_periods=self._locked_periods(start_period, end_period),
            duplicate=self._existing_close(end_period),
            retained_earnings=self._retained_earnings_account(),
            closing_accounts=self._pnl_balances(start_period, end_period),
        )

    def _preview_payload(self, context: YearEndCloseContext) -> dict[str, Any]:
        blockers = self._blockers(context)
        retained_earnings = context.retained_earnings
        closing_line_count = len(context.closing_accounts)
        retained_line_count = 1 if context.retained_direction is not None else 0

        return {
            "year": context.year,
            "period": context.end_period,
            "entry_date": context.entry_date,
            "workflow": "year_end_close",
            "ready_to_post": not blockers,
            "blocker_count": len(blockers),
            "blockers": blockers,
            "locked_periods": context.locked_periods,
            "duplicate_journal": _duplicate_preview(context.duplicate),
            "pnl_account_count": len(context.closing_accounts),
            "closing_accounts": [
                {
                    "id": account.id,
                    "code": account.code,
                    "name": account.name,
                    "account_type": account.account_type,
                    "balance": serialise_money(account.balance),
                }
                for account in context.closing_accounts
            ],
            "net_income": serialise_money(context.net_income),
            "revenue_closed": serialise_money(context.revenue_closed),
            "expenses_closed": serialise_money(context.expenses_closed),
            "retained_earnings_direction": context.retained_direction,
            "retained_earnings_amount": serialise_money(context.retained_amount),
            "retained_earnings_account": (
                {
                    "id": str(retained_earnings["id"]),
                    "code": str(retained_earnings["code"]),
                    "name": str(retained_earnings["name"]),
                }
                if retained_earnings is not None
                else None
            ),
            "line_count": closing_line_count + retained_line_count,
        }

    @staticmethod
    def _blockers(context: YearEndCloseContext) -> list[dict[str, Any]]:
        blockers: list[dict[str, Any]] = []
        if context.locked_periods:
            blockers.append(
                {
                    "code": "year_end_close_period_locked",
                    "message": (
                        "Unlock the fiscal-year periods before posting year-end close."
                    ),
                    "status_code": 409,
                    "locked_periods": context.locked_periods,
                }
            )
        if context.duplicate is not None:
            duplicate = _duplicate_preview(context.duplicate)
            blockers.append(
                {
                    "code": "year_end_close_already_posted",
                    "message": f"Year-end close for {context.year} is already posted.",
                    "status_code": 409,
                    "journal_entry_id": duplicate.get("journal_entry_id"),
                    "entry_number": duplicate.get("entry_number"),
                }
            )
        if context.retained_earnings is None:
            blockers.append(
                {
                    "code": "retained_earnings_account_missing",
                    "message": (
                        "Retained Earnings account is not configured for this tenant."
                    ),
                    "status_code": 422,
                    "expected_code": "3000",
                }
            )
        if not context.closing_accounts:
            blockers.append(
                {
                    "code": "year_end_close_no_activity",
                    "message": (
                        "No posted revenue or expense activity exists for this fiscal year."
                    ),
                    "status_code": 422,
                }
            )
        return blockers

    def _raise_for_blocker(self, context: YearEndCloseContext) -> None:
        for blocker in self._blockers(context):
            code = str(blocker["code"])
            message = str(blocker["message"])
            status_code = int(blocker.get("status_code") or 422)
            detail = {"year": context.year}
            if code == "year_end_close_period_locked":
                detail["locked_periods"] = context.locked_periods
            elif code == "year_end_close_already_posted":
                detail["journal_entry_id"] = str(blocker.get("journal_entry_id") or "")
                detail["entry_number"] = str(blocker.get("entry_number") or "")
            elif code == "retained_earnings_account_missing":
                detail["expected_code"] = "3000"
            raise YearEndCloseError(
                code,
                message,
                status_code=status_code,
                detail=detail,
            )

    def _locked_periods(self, start_period: str, end_period: str) -> list[str]:
        rows = (
            self.db.table("period_locks")
            .select("period")
            .eq("tenant_id", self.tenant_id)
            .gte("period", start_period)
            .lte("period", end_period)
            .execute()
            .data
            or []
        )
        return sorted(str(row.get("period")) for row in rows if row.get("period"))

    def _existing_close(self, period: str) -> dict[str, Any] | None:
        rows = (
            self.db.table("journal_entries")
            .select("id, entry_number, posted_at")
            .eq("tenant_id", self.tenant_id)
            .eq("period", period)
            .eq("reference_type", "year_end_close")
            .execute()
            .data
            or []
        )
        for row in rows:
            if row.get("posted_at"):
                return row
        return None

    def _retained_earnings_account(self) -> dict[str, Any] | None:
        rows = (
            self.db.table("accounts")
            .select("id, code, name, account_type")
            .eq("tenant_id", self.tenant_id)
            .eq("account_type", "equity")
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        for row in rows:
            if str(row.get("code") or "") == "3000":
                return row
        for row in rows:
            if "retained earnings" in str(row.get("name") or "").lower():
                return row
        return None

    def _pnl_balances(self, start_period: str, end_period: str) -> list[ClosingAccount]:
        rows = (
            self.db.table("journal_lines")
            .select(
                "direction, base_amount, "
                "journal_entries!journal_entry_id(period, posted_at), "
                "accounts!account_id(id, code, name, account_type)"
            )
            .eq("tenant_id", self.tenant_id)
            .execute()
            .data
            or []
        )

        balances: dict[str, ClosingAccount] = {}
        for row in rows:
            entry = _single_join(row.get("journal_entries"))
            period = str(entry.get("period") or "")
            if period < start_period or period > end_period or not entry.get("posted_at"):
                continue

            account = _single_join(row.get("accounts"))
            account_type = str(account.get("account_type") or "")
            if account_type not in {"revenue", "expense"}:
                continue

            amount = Decimal(str(row.get("base_amount") or "0"))
            direction = str(row.get("direction") or "")
            signed = _natural_balance(account_type, direction, amount)
            account_id = str(account.get("id") or "")
            if not account_id:
                continue
            current = balances.get(account_id)
            if current is None:
                balances[account_id] = ClosingAccount(
                    id=account_id,
                    code=str(account.get("code") or ""),
                    name=str(account.get("name") or ""),
                    account_type=account_type,
                    balance=signed,
                )
            else:
                balances[account_id] = ClosingAccount(
                    id=current.id,
                    code=current.code,
                    name=current.name,
                    account_type=current.account_type,
                    balance=current.balance + signed,
                )

        return [
            account
            for account in sorted(balances.values(), key=lambda item: item.code)
            if account.balance != Decimal("0")
        ]

    @staticmethod
    def _closing_lines(accounts: list[ClosingAccount]) -> list[JournalLineSpec]:
        lines: list[JournalLineSpec] = []
        for account in accounts:
            direction = _closing_direction(account.account_type, account.balance)
            amount = abs(account.balance)
            lines.append(
                JournalLineSpec(
                    direction=direction,
                    account_code=account.code,
                    account_id=account.id,
                    amount=amount,
                    base_amount=amount,
                    description=f"Close {account.code} {account.name}",
                )
            )
        return lines


def _single_join(value: Any) -> dict[str, Any]:
    if isinstance(value, list):
        return value[0] if value else {}
    return value if isinstance(value, dict) else {}


def _duplicate_preview(row: dict[str, Any] | None) -> dict[str, str] | None:
    if row is None:
        return None
    return {
        "journal_entry_id": str(row.get("id") or ""),
        "entry_number": str(row.get("entry_number") or ""),
        "posted_at": str(row.get("posted_at") or ""),
    }


def _natural_balance(account_type: str, direction: str, amount: Decimal) -> Decimal:
    if account_type == "revenue":
        return amount if direction == "CR" else -amount
    if account_type == "expense":
        return amount if direction == "DR" else -amount
    return Decimal("0")


def _closing_direction(account_type: str, balance: Decimal) -> str:
    if account_type == "revenue":
        return "DR" if balance > Decimal("0") else "CR"
    return "CR" if balance > Decimal("0") else "DR"


def _net_income(accounts: list[ClosingAccount]) -> Decimal:
    revenue = sum(row.balance for row in accounts if row.account_type == "revenue")
    expenses = sum(row.balance for row in accounts if row.account_type == "expense")
    return revenue - expenses

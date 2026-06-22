"""Financial close reconciliation checks used before period lock."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from typing import ClassVar

from app.services.reports_service import ReportsService
from supabase import Client


@dataclass(frozen=True)
class ReconciliationFinding:
    """A blocking close finding for one sub-ledger source row."""

    code: str
    source_table: str
    source_id: str
    source_number: str | None
    reason: str
    expected_reference_type: str

    def as_dict(self) -> dict[str, str | None]:
        return {
            "code": self.code,
            "source_table": self.source_table,
            "source_id": self.source_id,
            "source_number": self.source_number,
            "reason": self.reason,
            "expected_reference_type": self.expected_reference_type,
        }


@dataclass(frozen=True)
class CloseReconciliationResult:
    """Result of the pre-lock close reconciliation."""

    period: str
    ready: bool
    findings: list[ReconciliationFinding]
    trial_balance_balanced: bool

    def as_error_detail(self) -> dict[str, object]:
        return {
            "code": "close_reconciliation_failed",
            "period": self.period,
            "findings": [finding.as_dict() for finding in self.findings],
            "trial_balance_balanced": self.trial_balance_balanced,
        }


class CloseReconciliationService:
    """Checks whether a tenant period is safe to lock."""

    _AR_FINAL_STATUSES: ClassVar[tuple[str, ...]] = ("approved", "sent", "paid", "overdue")
    _AP_FINAL_STATUSES: ClassVar[tuple[str, ...]] = ("approved", "partially_paid", "paid")

    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def check_period(self, period: str) -> CloseReconciliationResult:
        """Return close blockers for the requested ``YYYY-MM`` period."""
        start, end = _period_bounds(period)

        findings: list[ReconciliationFinding] = []
        findings.extend(self._check_ar_invoice_journals(start, end))
        findings.extend(self._check_ar_payment_journals(start, end))
        findings.extend(self._check_ap_bill_journals(start, end))
        findings.extend(self._check_ap_payment_journals(start, end))

        trial_balance = ReportsService(self.db, self.tenant_id).trial_balance(period)
        trial_balance_balanced = trial_balance.is_balanced
        if not trial_balance_balanced:
            findings.append(
                ReconciliationFinding(
                    code="trial_balance_unbalanced",
                    source_table="journal_entries",
                    source_id=period,
                    source_number=period,
                    reason="Trial balance debits and credits do not match through this period.",
                    expected_reference_type="journal",
                )
            )

        return CloseReconciliationResult(
            period=period,
            ready=not findings,
            findings=findings,
            trial_balance_balanced=trial_balance_balanced,
        )

    def _check_ar_invoice_journals(
        self, start: date, end: date
    ) -> list[ReconciliationFinding]:
        invoices = (
            self.db.table("invoices")
            .select("id, invoice_number, status, issue_date")
            .eq("tenant_id", self.tenant_id)
            .in_("status", list(self._AR_FINAL_STATUSES))
            .gte("issue_date", start.isoformat())
            .lte("issue_date", end.isoformat())
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        posted_ids = self._posted_reference_ids("invoice", [row["id"] for row in invoices])
        return [
            ReconciliationFinding(
                code="missing_invoice_journal",
                source_table="invoices",
                source_id=str(row["id"]),
                source_number=row.get("invoice_number"),
                reason=f"Invoice status is {row.get('status')!r} but no posted AR journal exists.",
                expected_reference_type="invoice",
            )
            for row in invoices
            if str(row["id"]) not in posted_ids
        ]

    def _check_ar_payment_journals(
        self, start: date, end: date
    ) -> list[ReconciliationFinding]:
        paid_invoices = (
            self.db.table("invoices")
            .select("id, invoice_number, paid_at")
            .eq("tenant_id", self.tenant_id)
            .eq("status", "paid")
            .gte("paid_at", start.isoformat())
            .lte("paid_at", f"{end.isoformat()}T23:59:59")
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        posted_ids = self._posted_reference_ids(
            "payment", [row["id"] for row in paid_invoices]
        )
        return [
            ReconciliationFinding(
                code="missing_ar_payment_journal",
                source_table="invoices",
                source_id=str(row["id"]),
                source_number=row.get("invoice_number"),
                reason="Invoice is paid in the period but no posted payment journal exists.",
                expected_reference_type="payment",
            )
            for row in paid_invoices
            if str(row["id"]) not in posted_ids
        ]

    def _check_ap_bill_journals(
        self, start: date, end: date
    ) -> list[ReconciliationFinding]:
        bills = (
            self.db.table("bills")
            .select("id, bill_number, status, issue_date")
            .eq("tenant_id", self.tenant_id)
            .in_("status", list(self._AP_FINAL_STATUSES))
            .gte("issue_date", start.isoformat())
            .lte("issue_date", end.isoformat())
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        posted_ids = self._posted_reference_ids("bill", [row["id"] for row in bills])
        return [
            ReconciliationFinding(
                code="missing_bill_journal",
                source_table="bills",
                source_id=str(row["id"]),
                source_number=row.get("bill_number"),
                reason=f"Bill status is {row.get('status')!r} but no posted AP journal exists.",
                expected_reference_type="bill",
            )
            for row in bills
            if str(row["id"]) not in posted_ids
        ]

    def _check_ap_payment_journals(
        self, start: date, end: date
    ) -> list[ReconciliationFinding]:
        paid_bills = (
            self.db.table("bills")
            .select("id, bill_number, paid_at")
            .eq("tenant_id", self.tenant_id)
            .eq("status", "paid")
            .gte("paid_at", start.isoformat())
            .lte("paid_at", f"{end.isoformat()}T23:59:59")
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        posted_ids = self._posted_reference_ids(
            "bill_payment", [row["id"] for row in paid_bills]
        )
        return [
            ReconciliationFinding(
                code="missing_ap_payment_journal",
                source_table="bills",
                source_id=str(row["id"]),
                source_number=row.get("bill_number"),
                reason="Bill is paid in the period but no posted payment journal exists.",
                expected_reference_type="bill_payment",
            )
            for row in paid_bills
            if str(row["id"]) not in posted_ids
        ]

    def _posted_reference_ids(self, reference_type: str, source_ids: list[str]) -> set[str]:
        if not source_ids:
            return set()
        rows = (
            self.db.table("journal_entries")
            .select("reference_id")
            .eq("tenant_id", self.tenant_id)
            .eq("reference_type", reference_type)
            .in_("reference_id", source_ids)
            .not_.is_("posted_at", "null")
            .execute()
            .data
            or []
        )
        return {str(row["reference_id"]) for row in rows if row.get("reference_id")}


def _period_bounds(period: str) -> tuple[date, date]:
    year_str, month_str = period.split("-", 1)
    year = int(year_str)
    month = int(month_str)
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)

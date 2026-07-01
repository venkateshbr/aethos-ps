"""Read-only P2P vendor bill and payment-risk drilldown service."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from supabase import Client


class P2PReadService:
    """Tenant-scoped read model for vendor bills and bill-payment risk."""

    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def payment_risk_read_pack(
        self,
        *,
        bill_id: str | None = None,
        bill_number: str | None = None,
        vendor_id: str | None = None,
        vendor_name: str | None = None,
        status: str | None = None,
        due_within_days: int = 10,
        limit: int = 25,
    ) -> dict[str, Any]:
        capped_limit = max(1, min(limit, 100))
        due_window = max(0, min(due_within_days, 365))
        vendor_ids = self._vendor_ids_for_name(vendor_name) if vendor_name else None
        bill_rows = self._fetch_bill_rows(
            bill_id=bill_id,
            bill_number=bill_number,
            vendor_id=vendor_id,
            vendor_ids=vendor_ids,
            status=status,
            limit=capped_limit,
        )
        bill_ids = [str(row["id"]) for row in bill_rows]
        lines_by_bill = self._lines_by_bill(bill_ids)
        batch_items_by_bill = self._payment_batches_by_bill(bill_ids)
        duplicate_keys = self._duplicate_keys(bill_rows)

        bills = [
            self._bill_summary(
                row,
                lines=lines_by_bill.get(str(row["id"]), []),
                payment_batches=batch_items_by_bill.get(str(row["id"]), []),
                duplicate_keys=duplicate_keys,
                due_within_days=due_window,
            )
            for row in bill_rows
        ]
        vendors = self._vendor_summaries(bills, due_within_days=due_window)
        return {
            "tenant_id": self.tenant_id,
            "generated_at": datetime.now().astimezone().isoformat(),
            "query": {
                "bill_id": bill_id,
                "bill_number": bill_number,
                "vendor_id": vendor_id,
                "vendor_name": vendor_name,
                "status": status,
                "due_within_days": due_window,
                "limit": capped_limit,
            },
            "totals": self._totals(bills, vendors, due_within_days=due_window),
            "vendors": vendors,
            "bills": bills,
            "response_contract": [
                "Payment answers must use the literal label Vendor and include bill number, amount, due date, status, duplicate guard, PO/service-order evidence, coding/account evidence, blockers, and next action.",
                "If extraction is blocked by security review, still summarize available project, duplicate, PO/service-order, coding, and Inbox review evidence.",
            ],
        }

    def _vendor_ids_for_name(self, vendor_name: str | None) -> list[str]:
        raw = (vendor_name or "").strip().lower()
        if not raw:
            return []
        rows = (
            self.db.table("clients")
            .select("id,name,kind")
            .eq("tenant_id", self.tenant_id)
            .is_("deleted_at", "null")
            .limit(100)
            .execute()
            .data
            or []
        )
        return [
            str(row["id"])
            for row in rows
            if raw in str(row.get("name") or "").lower()
            and str(row.get("kind") or "vendor") in {"vendor", "both"}
        ]

    def _fetch_bill_rows(
        self,
        *,
        bill_id: str | None,
        bill_number: str | None,
        vendor_id: str | None,
        vendor_ids: list[str] | None,
        status: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        if vendor_ids is not None and not vendor_ids:
            return []
        query = (
            self.db.table("bills")
            .select(
                "id,tenant_id,client_id,purchase_order_id,bill_number,currency,subtotal,"
                "tax_total,total,status,issue_date,due_date,paid_at,vendor_invoice_number,"
                "po_match_status,po_match_summary,vendor_invoice_review,source_document_id,"
                "notes,created_at,updated_at,clients(name,billing_email)"
            )
            .eq("tenant_id", self.tenant_id)
            .is_("deleted_at", "null")
            .order("due_date", desc=False)
            .limit(limit)
        )
        if bill_id:
            query = query.eq("id", bill_id)
        if bill_number:
            query = query.eq("bill_number", bill_number)
        if vendor_id:
            query = query.eq("client_id", vendor_id)
        if vendor_ids is not None:
            query = query.in_("client_id", vendor_ids)
        if status:
            query = query.eq("status", status)
        return query.execute().data or []

    def _lines_by_bill(self, bill_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        if not bill_ids:
            return {}
        rows = (
            self.db.table("bill_lines")
            .select(
                "id,bill_id,description,quantity,unit_price,amount,tax_amount,account_id,"
                "is_prepaid,service_start_date,service_end_date,created_at"
            )
            .eq("tenant_id", self.tenant_id)
            .in_("bill_id", bill_ids)
            .execute()
            .data
            or []
        )
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[str(row.get("bill_id") or "")].append(row)
        return dict(grouped)

    def _payment_batches_by_bill(
        self,
        bill_ids: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        if not bill_ids:
            return {}
        items = (
            self.db.table("bill_payment_items")
            .select("id,batch_id,bill_id,amount,currency,status,created_at")
            .eq("tenant_id", self.tenant_id)
            .in_("bill_id", bill_ids)
            .execute()
            .data
            or []
        )
        batch_ids = sorted(
            {str(item.get("batch_id") or "") for item in items if item.get("batch_id")}
        )
        batches = self._payment_batches(batch_ids)
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in items:
            batch = batches.get(str(item.get("batch_id") or ""), {})
            grouped[str(item.get("bill_id") or "")].append(_payment_batch_summary(item, batch))
        return dict(grouped)

    def _payment_batches(self, batch_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not batch_ids:
            return {}
        rows = (
            self.db.table("bill_payment_batches")
            .select(
                "id,status,total,currency,pay_date,file_format,exported_at,"
                "export_file_sha256,sent_at,settled_at,risk_review_required"
            )
            .eq("tenant_id", self.tenant_id)
            .in_("id", batch_ids)
            .execute()
            .data
            or []
        )
        return {str(row.get("id") or ""): row for row in rows}

    def _duplicate_keys(self, bill_rows: list[dict[str, Any]]) -> set[tuple[str, str]]:
        counts: Counter[tuple[str, str]] = Counter()
        for row in bill_rows:
            vendor_invoice_number = str(row.get("vendor_invoice_number") or "").strip()
            if not vendor_invoice_number:
                continue
            status = str(row.get("status") or "")
            if status in {"void", "voided", "paid"}:
                continue
            counts[(str(row.get("client_id") or ""), vendor_invoice_number)] += 1
        return {key for key, count in counts.items() if count > 1}

    def _bill_summary(
        self,
        row: dict[str, Any],
        *,
        lines: list[dict[str, Any]],
        payment_batches: list[dict[str, Any]],
        duplicate_keys: set[tuple[str, str]],
        due_within_days: int,
    ) -> dict[str, Any]:
        today = date.today()
        due_date = _parse_date(row.get("due_date"))
        days_until_due = (due_date - today).days if due_date else None
        days_overdue = max(0, -days_until_due) if days_until_due is not None else 0
        coding_summary = _coding_summary(lines)
        duplicate_risk = _duplicate_risk(row, duplicate_keys)
        duplicate_review_required = duplicate_risk and not _duplicate_review_approved(row)
        payment_blockers = _payment_blockers(
            row=row,
            coding_summary=coding_summary,
            duplicate_review_required=duplicate_review_required,
            payment_batches=payment_batches,
        )
        bill_state = _bill_state(row, payment_batches, payment_blockers)
        payment_readiness = _payment_readiness(row, payment_blockers)
        return {
            "id": str(row.get("id") or ""),
            "bill_number": str(row.get("bill_number") or ""),
            "vendor_id": str(row.get("client_id") or ""),
            "vendor_name": _vendor_name(row),
            "vendor_invoice_number": (
                str(row.get("vendor_invoice_number")) if row.get("vendor_invoice_number") else None
            ),
            "status": str(row.get("status") or ""),
            "bill_state": bill_state,
            "currency": str(row.get("currency") or "USD"),
            "total": str(_decimal(row.get("total"))),
            "issue_date": _date_text(row.get("issue_date")),
            "due_date": _date_text(row.get("due_date")),
            "paid_at": _date_text(row.get("paid_at")),
            "days_until_due": days_until_due,
            "days_overdue": days_overdue,
            "aging_bucket": _ap_aging_bucket(due_date, today, str(row.get("status") or "")),
            "source_document_id": (
                str(row.get("source_document_id")) if row.get("source_document_id") else None
            ),
            "source_document_available": bool(row.get("source_document_id")),
            "po_match_status": str(row.get("po_match_status") or "not_linked"),
            "coding_summary": coding_summary,
            "duplicate_risk": duplicate_risk,
            "duplicate_review_required": duplicate_review_required,
            "approval_state": _approval_state(row),
            "payment_readiness": payment_readiness,
            "payment_blockers": payment_blockers,
            "payment_batches": payment_batches,
            "recommended_next_action": _recommended_next_action(
                row=row,
                days_until_due=days_until_due,
                due_within_days=due_within_days,
                payment_batches=payment_batches,
                payment_blockers=payment_blockers,
            ),
        }

    def _vendor_summaries(
        self,
        bills: list[dict[str, Any]],
        *,
        due_within_days: int,
    ) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for bill in bills:
            grouped[str(bill["vendor_id"])].append(bill)

        summaries: list[dict[str, Any]] = []
        for vendor_id, vendor_bills in grouped.items():
            balances: dict[str, Decimal] = defaultdict(Decimal)
            due_soon: dict[str, Decimal] = defaultdict(Decimal)
            for bill in vendor_bills:
                if bill["status"] in {"paid", "void", "voided"}:
                    continue
                currency = str(bill["currency"])
                amount = _decimal(bill["total"])
                balances[currency] += amount
                if _is_due_soon(bill, due_within_days=due_within_days):
                    due_soon[currency] += amount
            blocked = [bill for bill in vendor_bills if bill["payment_blockers"]]
            due_soon_bills = [
                bill for bill in vendor_bills if _is_due_soon(bill, due_within_days=due_within_days)
            ]
            summaries.append(
                {
                    "vendor_id": vendor_id,
                    "vendor_name": vendor_bills[0].get("vendor_name"),
                    "bill_count": len(vendor_bills),
                    "open_bill_count": sum(
                        1
                        for bill in vendor_bills
                        if bill["status"] not in {"paid", "void", "voided"}
                    ),
                    "due_soon_bill_count": len(due_soon_bills),
                    "blocked_bill_count": len(blocked),
                    "balances_by_currency": {
                        currency: str(amount) for currency, amount in balances.items()
                    },
                    "due_soon_by_currency": {
                        currency: str(amount) for currency, amount in due_soon.items()
                    },
                    "recommended_next_action": _vendor_next_action(
                        due_soon_bills,
                        blocked,
                    ),
                    "bills": vendor_bills,
                }
            )
        return summaries

    def _totals(
        self,
        bills: list[dict[str, Any]],
        vendors: list[dict[str, Any]],
        *,
        due_within_days: int,
    ) -> dict[str, object]:
        balances: dict[str, Decimal] = defaultdict(Decimal)
        due_soon: dict[str, Decimal] = defaultdict(Decimal)
        for bill in bills:
            if bill["status"] in {"paid", "void", "voided"}:
                continue
            currency = str(bill["currency"])
            amount = _decimal(bill["total"])
            balances[currency] += amount
            if _is_due_soon(bill, due_within_days=due_within_days):
                due_soon[currency] += amount
        return {
            "bill_count": len(bills),
            "vendor_count": len(vendors),
            "open_bill_count": sum(
                1 for bill in bills if bill["status"] not in {"paid", "void", "voided"}
            ),
            "due_soon_bill_count": sum(
                1 for bill in bills if _is_due_soon(bill, due_within_days=due_within_days)
            ),
            "blocked_bill_count": sum(1 for bill in bills if bill["payment_blockers"]),
            "balances_by_currency": {
                currency: str(amount) for currency, amount in balances.items()
            },
            "due_soon_by_currency": {
                currency: str(amount) for currency, amount in due_soon.items()
            },
            "status_counts": dict(Counter(str(bill["status"]) for bill in bills)),
            "state_counts": dict(Counter(str(bill["bill_state"]) for bill in bills)),
        }


def _payment_batch_summary(item: dict[str, Any], batch: dict[str, Any]) -> dict[str, Any]:
    return {
        "batch_id": str(item.get("batch_id") or ""),
        "batch_status": str(batch.get("status") or "unknown"),
        "item_status": str(item.get("status") or "pending"),
        "amount": str(_decimal(item.get("amount"))),
        "currency": str(item.get("currency") or batch.get("currency") or "USD"),
        "pay_date": _date_text(batch.get("pay_date")),
        "file_format": batch.get("file_format"),
        "exported_at": _date_text(batch.get("exported_at")),
        "export_file_hash_present": bool(batch.get("export_file_sha256")),
        "sent_at": _date_text(batch.get("sent_at")),
        "settled_at": _date_text(batch.get("settled_at")),
        "risk_review_required": bool(batch.get("risk_review_required")),
    }


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _parse_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _date_text(value: object) -> str | None:
    return str(value) if value else None


def _vendor_name(row: dict[str, Any]) -> str | None:
    client = row.get("clients")
    if isinstance(client, list):
        client = client[0] if client else {}
    if isinstance(client, dict):
        return str(client.get("name")) if client.get("name") else None
    return None


def _coding_summary(lines: list[dict[str, Any]]) -> dict[str, object]:
    line_count = len(lines)
    coded_count = sum(1 for line in lines if line.get("account_id"))
    prepaid_count = sum(1 for line in lines if line.get("is_prepaid"))
    service_period_missing = sum(
        1
        for line in lines
        if line.get("is_prepaid")
        and (not line.get("service_start_date") or not line.get("service_end_date"))
    )
    if line_count == 0:
        status = "no_lines"
    elif coded_count == line_count and service_period_missing == 0:
        status = "fully_coded"
    elif coded_count == 0:
        status = "uncoded"
    else:
        status = "partially_coded"
    return {
        "status": status,
        "line_count": line_count,
        "coded_line_count": coded_count,
        "uncoded_line_count": max(line_count - coded_count, 0),
        "prepaid_line_count": prepaid_count,
        "service_period_exception_count": service_period_missing,
    }


def _duplicate_risk(
    row: dict[str, Any],
    duplicate_keys: set[tuple[str, str]],
) -> bool:
    review = row.get("vendor_invoice_review") or {}
    if not isinstance(review, dict):
        review = {}
    if review.get("possible_duplicate") is True:
        return True
    exceptions = review.get("review_exceptions") or review.get("exceptions") or []
    if isinstance(exceptions, list):
        for exception in exceptions:
            if isinstance(exception, dict) and "duplicate" in str(exception.get("code") or ""):
                return True
    vendor_invoice_number = str(row.get("vendor_invoice_number") or "").strip()
    return (
        bool(vendor_invoice_number)
        and (
            str(row.get("client_id") or ""),
            vendor_invoice_number,
        )
        in duplicate_keys
    )


def _duplicate_review_approved(row: dict[str, Any]) -> bool:
    review = row.get("vendor_invoice_review") or {}
    if not isinstance(review, dict):
        return False
    duplicate_review = review.get("duplicate_review")
    if not isinstance(duplicate_review, dict):
        return False
    return bool(duplicate_review.get("approved_duplicate") and duplicate_review.get("reason"))


def _payment_blockers(
    *,
    row: dict[str, Any],
    coding_summary: dict[str, object],
    duplicate_review_required: bool,
    payment_batches: list[dict[str, Any]],
) -> list[str]:
    status = str(row.get("status") or "")
    blockers: list[str] = []
    if status in {"paid"}:
        blockers.append("bill_paid")
    if status in {"void", "voided"}:
        blockers.append("bill_voided")
    if status != "approved":
        blockers.append("bill_not_approved")
    if duplicate_review_required:
        blockers.append("duplicate_review_required")
    if str(row.get("po_match_status") or "not_linked") in {
        "over_tolerance",
        "vendor_mismatch",
        "currency_mismatch",
        "order_not_approved",
        "order_not_found",
    }:
        blockers.append("po_match_exception")
    if coding_summary.get("status") in {"no_lines", "uncoded", "partially_coded"}:
        blockers.append("coding_incomplete")
    if not row.get("source_document_id"):
        blockers.append("source_document_missing")
    unsettled_batches = [
        batch for batch in payment_batches if batch.get("batch_status") != "settled"
    ]
    if unsettled_batches:
        blockers.append("already_in_payment_batch")
    return list(dict.fromkeys(blockers))


def _bill_state(
    row: dict[str, Any],
    payment_batches: list[dict[str, Any]],
    payment_blockers: list[str],
) -> str:
    status = str(row.get("status") or "")
    if status in {"paid", "void", "voided", "draft"}:
        return "void" if status in {"void", "voided"} else status
    if "duplicate_review_required" in payment_blockers:
        return "duplicate_risk"
    if "po_match_exception" in payment_blockers or "source_document_missing" in payment_blockers:
        return "missing_evidence"
    if any(batch.get("batch_status") != "settled" for batch in payment_batches):
        return "scheduled"
    return status or "unknown"


def _payment_readiness(row: dict[str, Any], blockers: list[str]) -> str:
    status = str(row.get("status") or "")
    if status == "paid":
        return "paid"
    if status in {"void", "voided"}:
        return "not_payable"
    if "already_in_payment_batch" in blockers:
        return "scheduled"
    if blockers:
        return "blocked"
    return "ready_for_payment_packet"


def _approval_state(row: dict[str, Any]) -> str:
    status = str(row.get("status") or "")
    if status == "draft":
        return "bill_approval_required"
    if status == "approved":
        return "approved_for_payment_review"
    if status == "paid":
        return "paid"
    if status in {"void", "voided"}:
        return "voided"
    return status or "unknown"


def _ap_aging_bucket(due_date: date | None, today: date, status: str) -> str:
    if status == "paid":
        return "paid"
    if status in {"void", "voided", "draft"}:
        return "not_payable"
    if due_date is None:
        return "no_due_date"
    days = (today - due_date).days
    if days <= 0:
        return "current"
    if days <= 30:
        return "1_30"
    if days <= 60:
        return "31_60"
    if days <= 90:
        return "61_90"
    return "over_90"


def _recommended_next_action(
    *,
    row: dict[str, Any],
    days_until_due: int | None,
    due_within_days: int,
    payment_batches: list[dict[str, Any]],
    payment_blockers: list[str],
) -> str:
    status = str(row.get("status") or "")
    if status == "paid":
        return "No payment action; the bill is paid."
    if status in {"void", "voided"}:
        return "No payment action; the bill is voided."
    if "already_in_payment_batch" in payment_blockers:
        batch = next(
            (item for item in payment_batches if item.get("batch_status") != "settled"), {}
        )
        return _batch_next_action(batch)
    if "duplicate_review_required" in payment_blockers:
        return "Resolve duplicate vendor-invoice risk and capture reviewer reason before payment."
    if "po_match_exception" in payment_blockers:
        return "Resolve PO/service-order match exceptions before payment approval."
    if "coding_incomplete" in payment_blockers:
        return "Complete bill coding and line evidence before payment approval."
    if "source_document_missing" in payment_blockers:
        return "Attach or verify source document evidence before payment approval."
    if status != "approved":
        return "Approve the bill through Inbox or Bills before preparing payment."
    if days_until_due is None:
        return "Verify due date, then prepare a payment packet if payable."
    if days_until_due <= due_within_days:
        return "Prepare a payment approval packet for this approved bill."
    return "Approved but not due soon; schedule closer to due date."


def _batch_next_action(batch: dict[str, Any]) -> str:
    status = str(batch.get("batch_status") or "")
    if status == "draft":
        return "Bill is already in a draft payment batch awaiting approval."
    if status == "approved" and not batch.get("export_file_hash_present"):
        return "Payment batch is approved; export the bank file before sending."
    if status == "approved":
        return "Payment batch is approved and exported; mark sent after bank upload."
    if status == "sent_to_bank":
        return "Payment batch is sent to bank; settle after bank confirmation."
    if status == "settled":
        return "Payment batch is settled."
    return "Review the existing payment batch status before further payment action."


def _is_due_soon(bill: dict[str, Any], *, due_within_days: int) -> bool:
    if bill["status"] in {"paid", "void", "voided"}:
        return False
    days_until_due = bill.get("days_until_due")
    return isinstance(days_until_due, int) and days_until_due <= due_within_days


def _vendor_next_action(
    due_soon_bills: list[dict[str, Any]],
    blocked_bills: list[dict[str, Any]],
) -> str:
    if blocked_bills:
        return blocked_bills[0]["recommended_next_action"]
    if due_soon_bills:
        return due_soon_bills[0]["recommended_next_action"]
    return "No vendor payment action due soon."

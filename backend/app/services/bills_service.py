"""Business logic for the Bills (AP) resource.

Flow:
  create_bill  → validate vendor → insert bill → insert lines → recompute totals
  approve_bill → validate draft  → post GL journal (DR Expenses / CR AP) → mark approved
  list_bills   → paginated list with optional filters
  ap_aging     → bucket outstanding bills by due date
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status

from app.domain.journal_helper import JournalLineSpec, post_journal
from app.domain.money import serialise_money
from app.models.bills import (
    AgingBucket,
    ApAgingResponse,
    BillApproveResponse,
    BillCreate,
    BillLineResponse,
    BillListResponse,
    BillResponse,
)
from app.repositories.bills_repo import BillsRepository
from app.repositories.clients_repo import ClientRepository
from app.services._validation import assert_belongs_to_tenant
from supabase import Client

logger = logging.getLogger(__name__)

# COA codes used for AP journal posting
_EXPENSE_ACCOUNT_CODE = "5000"   # Expenses (DR)
_AP_ACCOUNT_CODE = "2000"        # Accounts Payable (CR)


def _line_to_response(row: dict) -> BillLineResponse:
    # quantity is a count (units), not money — render as-is.
    # unit_price / amount / tax_amount are money — always 2dp (bug #93).
    return BillLineResponse(
        id=str(row["id"]),
        bill_id=str(row["bill_id"]),
        description=row["description"],
        quantity=str(row["quantity"]),
        unit_price=serialise_money(row["unit_price"]) or "0.00",
        amount=serialise_money(row["amount"]) or "0.00",
        tax_amount=serialise_money(row.get("tax_amount") or "0") or "0.00",
        account_id=str(row["account_id"]) if row.get("account_id") else None,
        created_at=str(row["created_at"]),
    )


def _bill_to_response(row: dict, lines: list[dict] | None = None) -> BillResponse:
    return BillResponse(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        client_id=str(row["client_id"]),
        bill_number=row["bill_number"],
        currency=row["currency"],
        subtotal=serialise_money(row.get("subtotal") or "0") or "0.00",
        tax_total=serialise_money(row.get("tax_total") or "0") or "0.00",
        total=serialise_money(row.get("total") or "0") or "0.00",
        status=row["status"],
        issue_date=str(row["issue_date"]) if row.get("issue_date") else None,
        due_date=str(row["due_date"]) if row.get("due_date") else None,
        vendor_invoice_number=row.get("vendor_invoice_number"),
        notes=row.get("notes"),
        created_at=str(row["created_at"]),
        lines=[_line_to_response(ln) for ln in (lines or [])],
    )


class BillsService:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self._repo = BillsRepository(db, tenant_id)
        self._clients_repo = ClientRepository(db, tenant_id)
        self._db = db
        self._tenant_id = tenant_id

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    async def list_bills(
        self,
        status_filter: str | None = None,
        client_id: str | None = None,
        limit: int = 50,
    ) -> BillListResponse:
        rows = await self._repo.list(status=status_filter, client_id=client_id, limit=limit)
        items = [_bill_to_response(r) for r in rows]
        return BillListResponse(items=items, total=len(items))

    # ------------------------------------------------------------------
    # Get detail
    # ------------------------------------------------------------------

    async def get_bill(self, bill_id: str) -> BillResponse | None:
        row = await self._repo.get(bill_id)
        if row is None:
            return None
        lines = await self._repo.get_lines(bill_id)
        return _bill_to_response(row, lines)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_bill(self, data: BillCreate) -> BillResponse:
        # 1. Verify client exists and kind is vendor-capable
        client = await self._clients_repo.get(data.client_id)
        if client is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client {data.client_id!r} not found",
            )
        if client.get("kind") not in ("vendor", "both"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Client {data.client_id!r} is kind={client.get('kind')!r}. "
                    "Bills can only be created for clients with kind='vendor' or 'both'."
                ),
            )

        # 2. INSERT bill (bill_number set by DB trigger)
        bill_data: dict = {
            "client_id": data.client_id,
            "currency": data.currency,
            "status": "draft",
        }
        if data.issue_date is not None:
            bill_data["issue_date"] = data.issue_date.isoformat()
        if data.due_date is not None:
            bill_data["due_date"] = data.due_date.isoformat()
        if data.vendor_invoice_number is not None:
            bill_data["vendor_invoice_number"] = data.vendor_invoice_number
        if data.notes is not None:
            bill_data["notes"] = data.notes

        bill_row = await self._repo.create(bill_data)
        bill_id = str(bill_row["id"])

        # 3. INSERT bill lines
        subtotal = Decimal("0")
        tax_total = Decimal("0")
        lines_rows: list[dict] = []

        for line in data.lines:
            line_payload = {
                "description": line.description,
                "quantity": str(line.quantity),
                "unit_price": serialise_money(line.unit_price),
                "amount": serialise_money(line.amount),
                "tax_amount": serialise_money(line.tax_amount),
            }
            if line.account_id is not None:
                # Bug #92 sweep: account_id is a tenant-scoped FK.
                await assert_belongs_to_tenant(
                    self._db,
                    "accounts",
                    line.account_id,
                    self._tenant_id,
                    not_found_detail="Account not found",
                )
                line_payload["account_id"] = line.account_id
            line_row = await self._repo.create_line(bill_id, line_payload)
            lines_rows.append(line_row)
            subtotal += line.amount
            tax_total += line.tax_amount

        total = subtotal + tax_total

        # 4. Update totals on the bill
        if data.lines:
            await self._repo.update_totals(bill_id, subtotal, tax_total, total)
            # Refresh the row to get the DB-set values
            bill_row = await self._repo.get(bill_id) or bill_row
            bill_row["subtotal"] = serialise_money(subtotal)
            bill_row["tax_total"] = serialise_money(tax_total)
            bill_row["total"] = serialise_money(total)

        return _bill_to_response(bill_row, lines_rows)

    # ------------------------------------------------------------------
    # Approve — posts GL journal entry
    # ------------------------------------------------------------------

    async def approve_bill(self, bill_id: str, approved_by: str) -> BillApproveResponse:
        # 1. Get bill, verify status is draft
        bill = await self._repo.get(bill_id)
        if bill is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bill {bill_id!r} not found",
            )
        if bill["status"] != "draft":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Bill is already {bill['status']!r} — only draft bills can be approved",
            )

        # 2. Validate: total > 0, lines exist
        lines = await self._repo.get_lines(bill_id)
        if not lines:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Bill has no lines — add at least one line before approving",
            )
        total = Decimal(str(bill["total"]))
        if total <= Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Bill total must be greater than zero",
            )

        # 3. Resolve account IDs from COA
        expense_account_id = await self._repo.get_account_id_by_code(_EXPENSE_ACCOUNT_CODE)
        ap_account_id = await self._repo.get_account_id_by_code(_AP_ACCOUNT_CODE)
        if not expense_account_id or not ap_account_id:
            logger.error(
                "COA accounts missing for tenant %s — expected codes %s and %s",
                self._tenant_id,
                _EXPENSE_ACCOUNT_CODE,
                _AP_ACCOUNT_CODE,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Chart of accounts not configured — cannot post journal entry",
            )

        # 4. Build journal lines — accounting_guardian validates balance, period lock,
        #    and account existence inside post_journal.  Never bypass with direct INSERT.
        bill_number = bill.get("bill_number", "")
        currency = bill.get("currency", "USD")
        journal_lines = [
            JournalLineSpec(
                direction="DR",
                account_code=_EXPENSE_ACCOUNT_CODE,
                account_id=expense_account_id,
                amount=total,
                description=f"Expenses — {bill_number}",
                currency=currency,
            ),
            JournalLineSpec(
                direction="CR",
                account_code=_AP_ACCOUNT_CODE,
                account_id=ap_account_id,
                amount=total,
                description=f"AP — {bill_number}",
                currency=currency,
            ),
        ]

        # 5. Post via canonical post_journal — runs accounting_guardian L3 always.
        #    This replaces the old _post_journal that bypassed the guardian entirely.
        entry_date = bill.get("issue_date") or date.today().isoformat()
        try:
            je = await asyncio.to_thread(
                post_journal,
                self._db,
                self._tenant_id,
                approved_by,
                f"AP bill {bill_number}",
                str(entry_date),
                "bill",
                bill_id,
                journal_lines,
                f"AP-{bill_number}",
            )
        except ValueError as exc:
            # accounting_guardian rejected — period locked, imbalance, or unknown accounts
            logger.error(
                "accounting_guardian rejected journal for bill %s: %s",
                bill_id,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            logger.exception("Error posting journal entry for bill %s", bill_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to post GL journal — please try again",
            ) from exc

        journal_entry_id = je.get("id") if je else None

        # 6. Update bill status to 'approved'
        await self._repo.update(bill_id, {"status": "approved"})

        return BillApproveResponse(
            id=bill_id,
            status="approved",
            journal_entry_id=journal_entry_id,
            message=f"Bill {bill_number} approved and GL journal posted",
        )

    # ------------------------------------------------------------------
    # Void — reverses approved AP journals
    # ------------------------------------------------------------------

    async def void_bill(self, bill_id: str, voided_by: str) -> BillResponse:
        """Void a bill.

        Draft bills can be voided with a status change. Approved bills have
        already posted DR Expense / CR AP, so they require a reversing journal
        before status changes. Paid bills cannot be voided here; payment
        reversal/settlement needs its own lifecycle.
        """
        bill = await self._repo.get(bill_id)
        if bill is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bill {bill_id!r} not found",
            )

        current_status = str(bill["status"])
        if current_status == "voided":
            lines = await self._repo.get_lines(bill_id)
            return _bill_to_response(bill, lines)
        if current_status in {"paid", "partially_paid"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Bill is {current_status}; reverse the payment before voiding",
            )
        if current_status not in {"draft", "approved"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Bill is {current_status!r} and cannot be voided",
            )

        if current_status == "approved":
            await self._post_void_reversal(bill, voided_by)

        updated = await self._repo.update(bill_id, {"status": "voided"})
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bill {bill_id!r} not found",
            )
        lines = await self._repo.get_lines(bill_id)
        return _bill_to_response(updated, lines)

    async def _post_void_reversal(self, bill: dict, voided_by: str) -> None:
        bill_id = str(bill["id"])

        def _fetch_original_journal() -> dict | None:
            result = (
                self._db.table("journal_entries")
                .select("id")
                .eq("tenant_id", self._tenant_id)
                .eq("reference_type", "bill")
                .eq("reference_id", bill_id)
                .order("posted_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = result.data or []
            return rows[0] if rows else None

        original = await asyncio.to_thread(_fetch_original_journal)
        if original is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot void approved bill because its original AP journal was not found",
            )

        def _fetch_original_lines() -> list[dict]:
            result = (
                self._db.table("journal_lines")
                .select("direction, account_id, amount, currency, base_amount, description")
                .eq("tenant_id", self._tenant_id)
                .eq("journal_entry_id", original["id"])
                .execute()
            )
            return result.data or []

        original_lines = await asyncio.to_thread(_fetch_original_lines)
        if not original_lines:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot void approved bill because its original AP journal has no lines",
            )

        reversal_lines = [
            JournalLineSpec(
                direction="CR" if line["direction"] == "DR" else "DR",
                account_code="",
                account_id=str(line["account_id"]),
                amount=Decimal(str(line["amount"])),
                currency=str(line.get("currency") or bill.get("currency") or "USD"),
                base_amount=Decimal(str(line.get("base_amount") or line["amount"])),
                description=f"Void {line.get('description') or bill.get('bill_number') or bill_id}",
            )
            for line in original_lines
        ]

        try:
            await asyncio.to_thread(
                post_journal,
                self._db,
                self._tenant_id,
                voided_by,
                f"Void AP bill {bill.get('bill_number') or bill_id}",
                date.today().isoformat(),
                "bill_void",
                bill_id,
                reversal_lines,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

    # ------------------------------------------------------------------
    # AP Aging
    # ------------------------------------------------------------------

    async def ap_aging(self) -> ApAgingResponse:
        """Bucket outstanding approved/partially_paid bills by due date."""
        bills = await self._repo.get_approved_overdue_bills()
        today = date.today()

        buckets: dict[str, Decimal] = {
            "current": Decimal("0"),
            "1-30": Decimal("0"),
            "31-60": Decimal("0"),
            "61-90": Decimal("0"),
            "90+": Decimal("0"),
        }
        bucket_counts: dict[str, int] = dict.fromkeys(buckets, 0)

        for bill in bills:
            total_val = Decimal(str(bill.get("total", "0")))
            due_date_raw = bill.get("due_date")
            if not due_date_raw:
                # No due date — treat as current
                bucket = "current"
            else:
                due = date.fromisoformat(str(due_date_raw))
                days_overdue = (today - due).days
                if days_overdue <= 0:
                    bucket = "current"
                elif days_overdue <= 30:
                    bucket = "1-30"
                elif days_overdue <= 60:
                    bucket = "31-60"
                elif days_overdue <= 90:
                    bucket = "61-90"
                else:
                    bucket = "90+"

            buckets[bucket] += total_val
            bucket_counts[bucket] += 1

        grand_total = sum(buckets.values())
        return ApAgingResponse(
            buckets=[
                AgingBucket(label=k, total=serialise_money(v) or "0.00", count=bucket_counts[k])
                for k, v in buckets.items()
            ],
            grand_total=serialise_money(grand_total) or "0.00",
        )

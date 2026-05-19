"""Business logic for the Bills (AP) resource.

Flow:
  create_bill  → validate vendor → insert bill → insert lines → recompute totals
  approve_bill → validate draft  → post GL journal (DR Expenses / CR AP) → mark approved
  list_bills   → paginated list with optional filters
  ap_aging     → bucket outstanding bills by due date
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from supabase import Client

from app.domain.journal_helper import JournalLineSpec, validate_journal_balance
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

logger = logging.getLogger(__name__)

# COA codes used for AP journal posting
_EXPENSE_ACCOUNT_CODE = "5000"   # Expenses (DR)
_AP_ACCOUNT_CODE = "2000"        # Accounts Payable (CR)


def _line_to_response(row: dict) -> BillLineResponse:
    return BillLineResponse(
        id=str(row["id"]),
        bill_id=str(row["bill_id"]),
        description=row["description"],
        quantity=str(row["quantity"]),
        unit_price=str(row["unit_price"]),
        amount=str(row["amount"]),
        tax_amount=str(row["tax_amount"]),
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
        subtotal=str(row["subtotal"]),
        tax_total=str(row["tax_total"]),
        total=str(row["total"]),
        status=row["status"],
        issue_date=str(row["issue_date"]) if row.get("issue_date") else None,
        due_date=str(row["due_date"]) if row.get("due_date") else None,
        vendor_invoice_number=row.get("vendor_invoice_number"),
        notes=row.get("notes"),
        created_at=str(row["created_at"]),
        lines=[_line_to_response(l) for l in (lines or [])],
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
                "unit_price": str(line.unit_price),
                "amount": str(line.amount),
                "tax_amount": str(line.tax_amount),
            }
            if line.account_id is not None:
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
            bill_row["subtotal"] = str(subtotal)
            bill_row["tax_total"] = str(tax_total)
            bill_row["total"] = str(total)

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

        # 4. Build and validate journal lines
        journal_lines = [
            JournalLineSpec(
                direction="DR",
                account_code=_EXPENSE_ACCOUNT_CODE,
                amount=total,
                description=f"Expenses — {bill.get('bill_number', '')}",
            ),
            JournalLineSpec(
                direction="CR",
                account_code=_AP_ACCOUNT_CODE,
                amount=total,
                description=f"AP — {bill.get('bill_number', '')}",
            ),
        ]
        if not validate_journal_balance(journal_lines):
            logger.error("Journal imbalance for bill %s: lines=%s", bill_id, journal_lines)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Journal entry does not balance — cannot post",
            )

        # 5. INSERT journal_entry + journal_lines
        entry_date = bill.get("issue_date") or date.today().isoformat()
        period = str(entry_date)[:7]  # "YYYY-MM"

        journal_entry_id = await self._post_journal(
            bill_id=bill_id,
            bill_number=bill.get("bill_number", ""),
            entry_date=str(entry_date),
            period=period,
            currency=bill.get("currency", "USD"),
            total=total,
            expense_account_id=expense_account_id,
            ap_account_id=ap_account_id,
            created_by=approved_by,
        )

        # 6. Update bill status to 'approved'
        await self._repo.update(bill_id, {"status": "approved"})

        return BillApproveResponse(
            id=bill_id,
            status="approved",
            journal_entry_id=journal_entry_id,
            message=f"Bill {bill.get('bill_number', '')} approved and GL journal posted",
        )

    async def _post_journal(
        self,
        bill_id: str,
        bill_number: str,
        entry_date: str,
        period: str,
        currency: str,
        total: Decimal,
        expense_account_id: str,
        ap_account_id: str,
        created_by: str,
    ) -> str | None:
        """Insert journal_entry + two journal_lines; return the entry UUID."""
        import asyncio as _asyncio

        try:
            # Insert journal entry header
            je_result = await _asyncio.to_thread(
                lambda: self._db.table("journal_entries")
                .insert(
                    {
                        "tenant_id": self._tenant_id,
                        "entry_number": f"AP-{bill_number}",
                        "entry_type": "standard",
                        "description": f"AP bill {bill_number}",
                        "entry_date": entry_date,
                        "period": period,
                        "reference_type": "bill",
                        "reference_id": bill_id,
                        "posted_at": datetime.now(timezone.utc).isoformat(),
                        "created_by": created_by,
                    }
                )
                .execute()
            )
            if not je_result.data:
                logger.error("Failed to insert journal entry for bill %s", bill_id)
                return None

            je_id = str(je_result.data[0]["id"])

            # Insert debit line — Expenses
            await _asyncio.to_thread(
                lambda: self._db.table("journal_lines")
                .insert(
                    {
                        "journal_entry_id": je_id,
                        "tenant_id": self._tenant_id,
                        "direction": "DR",
                        "account_id": expense_account_id,
                        "amount": str(total),
                        "currency": currency,
                        "base_amount": str(total),
                        "description": f"Expenses — {bill_number}",
                    }
                )
                .execute()
            )

            # Insert credit line — Accounts Payable
            await _asyncio.to_thread(
                lambda: self._db.table("journal_lines")
                .insert(
                    {
                        "journal_entry_id": je_id,
                        "tenant_id": self._tenant_id,
                        "direction": "CR",
                        "account_id": ap_account_id,
                        "amount": str(total),
                        "currency": currency,
                        "base_amount": str(total),
                        "description": f"AP — {bill_number}",
                    }
                )
                .execute()
            )

            return je_id

        except Exception:
            logger.exception("Error posting journal entry for bill %s", bill_id)
            return None

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
                AgingBucket(label=k, total=str(v), count=bucket_counts[k])
                for k, v in buckets.items()
            ],
            grand_total=str(grand_total),
        )

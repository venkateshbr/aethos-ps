"""Bill payment batch service — creates batches, generates NACHA/CSV exports.

# Prahari review required — see docs/team/SECURITY_REVIEW.md

Security notes:
- NACHA routing/account numbers are left as placeholders — operators fill them.
  Raw bank account numbers are NEVER stored in this service.
- All bill_id lists are verified against tenant_id before use.
- Money values use Decimal throughout; serialised as strings for JSON/DB.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import HTTPException

from app.domain.journal_helper import JournalLineSpec, post_journal
from app.domain.money import serialise_money
from supabase import Client

logger = logging.getLogger(__name__)


class BillPaymentsService:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_batch(
        self,
        bill_ids: list[str],
        pay_date: date | None,
        bank_account_label: str,
        created_by: str,
    ) -> dict:
        """Create a bill payment batch from a list of approved bill IDs."""
        if not bill_ids:
            raise HTTPException(422, "At least one bill ID required")

        # Verify all bills are approved and belong to tenant
        bills = (
            self.db.table("bills")
            .select("id, total, currency, status, client_id")
            .eq("tenant_id", self.tenant_id)
            .in_("id", bill_ids)
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        if len(bills) != len(bill_ids):
            raise HTTPException(404, "One or more bills not found for this tenant")

        not_approved = [b["id"] for b in bills if b["status"] != "approved"]
        if not_approved:
            raise HTTPException(
                422,
                f"Bills must be approved before batching: {not_approved}",
            )

        total = sum(Decimal(str(b["total"])) for b in bills)
        currency = bills[0]["currency"] if bills else "USD"

        batch = (
            self.db.table("bill_payment_batches")
            .insert(
                {
                    "tenant_id": self.tenant_id,
                    "total": serialise_money(total),
                    "currency": currency,
                    "bank_account_label": bank_account_label,
                    "pay_date": pay_date.isoformat() if pay_date else date.today().isoformat(),
                    "created_by": created_by,
                }
            )
            .execute()
            .data[0]
        )

        items = [
            {
                "tenant_id": self.tenant_id,
                "batch_id": batch["id"],
                "bill_id": b["id"],
                "amount": serialise_money(b["total"]),
                "currency": b["currency"],
            }
            for b in bills
        ]
        self.db.table("bill_payment_items").insert(items).execute()

        logger.info(
            "bill_payment_batch_created",
            extra={
                "batch_id": batch["id"],
                "tenant_id": self.tenant_id,
                "total": str(total),
                "bill_count": len(bills),
            },
        )
        return {**batch, "items": items}

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_batch(self, batch_id: str) -> dict:
        r = (
            self.db.table("bill_payment_batches")
            .select("*")
            .eq("id", batch_id)
            .eq("tenant_id", self.tenant_id)
            .execute()
        )
        if not r.data:
            raise HTTPException(404, "Batch not found")
        batch = r.data[0]
        items = (
            self.db.table("bill_payment_items")
            .select("*, bills(bill_number, client_id, vendor_invoice_number)")
            .eq("batch_id", batch_id)
            .execute()
            .data
            or []
        )
        return {**batch, "items": items}

    def list_batches(self, status: str | None = None) -> list[dict]:
        q = (
            self.db.table("bill_payment_batches")
            .select("*")
            .eq("tenant_id", self.tenant_id)
        )
        if status:
            q = q.eq("status", status)
        return q.order("created_at", desc=True).limit(50).execute().data or []

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def approve_batch(self, batch_id: str, approved_by: str) -> dict:
        batch = self.get_batch(batch_id)
        if batch["status"] != "draft":
            raise HTTPException(409, f"Batch is already {batch['status']}")
        result = (
            self.db.table("bill_payment_batches")
            .update({"status": "approved"})
            .eq("id", batch_id)
            .eq("tenant_id", self.tenant_id)
            .execute()
        )
        return result.data[0]

    def mark_sent(self, batch_id: str) -> dict:
        self.get_batch(batch_id)  # verify exists + tenant owns it
        result = (
            self.db.table("bill_payment_batches")
            .update({"status": "sent_to_bank", "exported_at": datetime.now(UTC).isoformat()})
            .eq("id", batch_id)
            .eq("tenant_id", self.tenant_id)
            .execute()
        )
        return result.data[0]

    def settle_batch(self, batch_id: str, settled_by: str) -> dict:
        """Confirm bank settlement and post AP clearing journals.

        Money movement is never posted when a batch is merely proposed,
        approved, exported, or marked sent. This method represents the bank
        confirmation step: for each unsettled item it posts DR AP / CR Bank,
        marks the bill paid, and marks the batch item settled.
        """
        batch = self.get_batch(batch_id)
        if batch["status"] != "sent_to_bank":
            raise HTTPException(409, "Batch must be sent_to_bank before settlement")

        items = [item for item in batch["items"] if item.get("status") != "settled"]
        if not items:
            raise HTTPException(409, "Batch has no unsettled payment items")

        account_ids = self._get_account_ids_by_codes(["1100", "2000"])
        bank_account_id = account_ids.get("1100")
        ap_account_id = account_ids.get("2000")
        if not bank_account_id or not ap_account_id:
            raise HTTPException(500, "Chart of accounts not configured for bill settlement")

        settled_at = datetime.now(UTC).isoformat()
        journal_entry_ids: list[str] = []
        for item in items:
            amount = Decimal(str(item["amount"]))
            currency = item.get("currency") or batch.get("currency") or "USD"
            bill_id = str(item["bill_id"])
            bill_number = (item.get("bills") or {}).get("bill_number") or bill_id[:8]
            lines = [
                JournalLineSpec(
                    direction="DR",
                    account_code="2000",
                    account_id=ap_account_id,
                    amount=amount,
                    currency=currency,
                    description=f"AP cleared for bill {bill_number}",
                ),
                JournalLineSpec(
                    direction="CR",
                    account_code="1100",
                    account_id=bank_account_id,
                    amount=amount,
                    currency=currency,
                    description=f"Bank payment for bill {bill_number}",
                ),
            ]
            try:
                journal = post_journal(
                    db=self.db,
                    tenant_id=self.tenant_id,
                    created_by=settled_by,
                    description=f"Bill payment settled for {bill_number}",
                    entry_date=date.today().isoformat(),
                    reference_type="bill_payment",
                    reference_id=bill_id,
                    lines=lines,
                    entry_number=f"BP-{bill_number}",
                )
            except ValueError as exc:
                raise HTTPException(422, detail=str(exc)) from exc

            journal_entry_ids.append(str(journal["id"]))
            self.db.table("bills").update(
                {"status": "paid", "paid_at": settled_at}
            ).eq("id", bill_id).eq("tenant_id", self.tenant_id).execute()
            self.db.table("bill_payment_items").update({"status": "settled"}).eq(
                "id", item["id"]
            ).eq("tenant_id", self.tenant_id).execute()

        logger.info(
            "bill_payment_batch_settled",
            extra={
                "batch_id": batch_id,
                "tenant_id": self.tenant_id,
                "settled_count": len(items),
            },
        )
        return {
            "batch_id": batch_id,
            "status": "settled",
            "settled_count": len(items),
            "journal_entry_ids": journal_entry_ids,
        }

    def _get_account_ids_by_codes(self, codes: list[str]) -> dict[str, str]:
        rows = (
            self.db.table("accounts")
            .select("id, code")
            .eq("tenant_id", self.tenant_id)
            .in_("code", codes)
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        return {row["code"]: row["id"] for row in rows}

    # ------------------------------------------------------------------
    # Export — NACHA
    # ------------------------------------------------------------------

    def export_nacha(self, batch_id: str) -> bytes:
        """Generate a minimal NACHA ACH batch file. US market only.

        Routing/account numbers are left as placeholder zeros — the operator
        fills them before submitting to the bank.  We never store real routing
        or account numbers here (Prahari gate).
        """
        batch = self.get_batch(batch_id)
        items = batch["items"]

        today = datetime.now(UTC)
        file_date = today.strftime("%y%m%d")
        file_time = today.strftime("%H%M")

        lines: list[str] = []

        # File header — record type 1 (94-char fixed width)
        lines.append(
            f"101 {'':10}{'0000000001':<10}{'':10}{file_date}{file_time}"
            f"A094101{'AETHOS PS':<23}{'PAYMENT':<23}{'1':>8}"
        )
        # Batch header — record type 5
        lines.append(
            f"5200{'AETHOS PS':<16}{'':16}{'0000000001':>10}"
            f"PPD{'VENDOR PAY':<10}{file_date}{'':6}1{'0000001':>7}"
        )

        seq = 1
        total_amount = Decimal("0")
        for item in items:
            amount_cents = int(Decimal(str(item["amount"])) * 100)
            total_amount += Decimal(str(item["amount"]))
            # Detail record — record type 6; placeholder routing 021000021 (Chase)
            lines.append(
                f"622{'021000021':>9}{'000000000000':>17}{amount_cents:>10}"
                f"{'VENDOR':>22}{'':2}{'0':1}{'0000001':>7}{seq:>7}"
            )
            seq += 1

        entry_count = len(items)
        total_cents = int(total_amount * 100)

        # Batch control — record type 8
        lines.append(
            f"8200{entry_count:>6}{'':10}{total_cents:>12}{total_cents:>12}"
            f"{'':39}{'0000001':>7}"
        )

        # File control — record type 9
        block_count = max(1, (len(lines) + 9) // 10)
        lines.append(
            f"9{1:>6}{block_count:>6}{entry_count:>8}"
            f"{total_cents:>12}{total_cents:>12}{'':39}"
        )

        # Pad to 10-record blocks (each block = 10 x 94-char records)
        while len(lines) % 10 != 0:
            lines.append("9" * 94)

        content = "\r\n".join(lines)

        self.db.table("bill_payment_batches").update(
            {"file_format": "nacha", "exported_at": datetime.now(UTC).isoformat()}
        ).eq("id", batch_id).execute()

        return content.encode("ascii")

    # ------------------------------------------------------------------
    # Export — CSV (universal, all 5 launch markets)
    # ------------------------------------------------------------------

    def export_csv(self, batch_id: str) -> bytes:
        """Generate a Universal CSV for bulk bank upload.

        Routing/account columns are intentionally blank — filled by the
        operator before upload.  We never persist bank credentials here.
        """
        batch = self.get_batch(batch_id)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Vendor Name",
                "Routing Number",
                "Account Number",
                "Amount",
                "Currency",
                "Pay Date",
                "Reference",
                "Vendor Invoice Number",
            ]
        )
        for item in batch["items"]:
            bill_info = item.get("bills") or {}
            writer.writerow(
                [
                    bill_info.get("client_id", ""),
                    "",  # routing — filled in by operator
                    "",  # account — filled in by operator
                    str(item["amount"]),
                    item["currency"],
                    batch.get("pay_date", date.today().isoformat()),
                    f"BATCH-{batch_id[:8]}",
                    bill_info.get("vendor_invoice_number", ""),
                ]
            )

        self.db.table("bill_payment_batches").update(
            {"file_format": "csv", "exported_at": datetime.now(UTC).isoformat()}
        ).eq("id", batch_id).execute()

        return output.getvalue().encode("utf-8")

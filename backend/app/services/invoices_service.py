"""InvoicesService — handles invoice lifecycle including Stripe Payment Link creation.

Issue #50: Invoice send + Stripe Payment Link
"""
# Prahari review required — see docs/team/SECURITY_REVIEW.md

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date
from datetime import datetime as _dt
from decimal import Decimal, InvalidOperation

import stripe
from fastapi import HTTPException

from app.core.config import settings
from app.domain.journal_helper import JournalLineSpec, post_journal
from app.domain.money import serialise_money
from app.models.invoices import (
    InvoiceCreate,
    InvoiceLineCreate,
    InvoiceResponse,
    PublicInvoiceResponse,
)
from app.repositories.invoices_repo import InvoicesRepository
from app.services._validation import assert_belongs_to_tenant
from app.services.retainer_ledger_service import record_retainer_draw
from supabase import Client

logger = logging.getLogger(__name__)


def _to_decimal(value: str | int | float | None, default: str = "0") -> Decimal:
    """Safely convert a value to Decimal; returns default on failure."""
    try:
        return Decimal(str(value)) if value is not None else Decimal(default)
    except InvalidOperation:
        return Decimal(default)


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def _line_amount(line: InvoiceLineCreate) -> Decimal:
    return _quantize_money(line.quantity * line.unit_price)


class InvoicesService:
    """Business logic for invoice lifecycle.

    Layer: Router → InvoicesService → InvoicesRepository → Supabase.
    Stripe calls are synchronous (stripe v15 SDK); they are short network calls.
    """

    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self._repo = InvoicesRepository(db, tenant_id)
        # Configure global stripe API key for this request context.
        stripe.api_key = settings.stripe_secret_key

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def list_invoices(
        self,
        engagement_id: str | None = None,
        status: str | None = None,
    ) -> list[InvoiceResponse]:
        rows = await self._repo.list_invoices(engagement_id=engagement_id, status=status)
        return [InvoiceResponse.from_db(r) for r in rows]

    async def get_invoice(self, invoice_id: str) -> InvoiceResponse:
        row = await self._repo.get_by_id(invoice_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Invoice not found")
        lines = await self._repo.list_lines(invoice_id)
        return InvoiceResponse.from_db(row, lines)

    async def get_by_public_token(self, token: str) -> PublicInvoiceResponse:
        """Fetch invoice for the public payment page — no auth required."""
        row = await self._repo.get_by_public_token(token)
        if row is None:
            raise HTTPException(status_code=404, detail="Invoice not found")
        lines = await self._repo.list_lines(str(row["id"]))
        return PublicInvoiceResponse.from_db(row, lines)

    async def create_invoice(self, data: InvoiceCreate, created_by: str) -> InvoiceResponse:
        """Persist a drafted invoice to DB (status=draft by default)."""
        # Bug #92 sweep: every tenant-scoped FK on the inbound payload is
        # validated up-front. Without this, a malicious tenant could attach
        # another tenant's engagement / client / tax_rate / time_entry /
        # expense to their invoice — see #92 root cause.
        await assert_belongs_to_tenant(
            self.db, "engagements", data.engagement_id, self.tenant_id,
            not_found_detail="Engagement not found",
        )
        await assert_belongs_to_tenant(
            self.db, "clients", data.client_id, self.tenant_id,
            not_found_detail="Client not found",
        )

        invoice_data: dict = {
            "tenant_id": self.tenant_id,
            "engagement_id": data.engagement_id,
            "client_id": data.client_id,
            "currency": data.currency,
            "status": "draft",
        }
        if data.issue_date:
            invoice_data["issue_date"] = data.issue_date.isoformat()
        if data.due_date:
            invoice_data["due_date"] = data.due_date.isoformat()
        if data.notes:
            invoice_data["notes"] = data.notes

        # Validate line-level FKs and compute totals before inserting the invoice.
        # If any line is invalid, no draft header is left behind.
        subtotal = Decimal("0")
        tax_total = Decimal("0")
        line_payloads: list[dict] = []
        for line in data.lines:
            line_amount = _line_amount(line)
            tax_amount = Decimal("0")
            tax_rate_id: str | None = None

            if line.tax_rate_id:
                tax_row = await self._repo.get_tax_rate(line.tax_rate_id)
                if tax_row is None:
                    raise HTTPException(status_code=404, detail="Tax rate not found")
                tax_rate_id = str(tax_row["id"])
                tax_rate = _to_decimal(tax_row.get("rate"))
                tax_amount = _quantize_money(line_amount * tax_rate)
            if line.time_entry_id:
                await assert_belongs_to_tenant(
                    self.db, "time_entries", line.time_entry_id, self.tenant_id,
                    not_found_detail="Time entry not found",
                )
            if line.expense_id:
                await assert_belongs_to_tenant(
                    self.db, "project_expenses", line.expense_id, self.tenant_id,
                    not_found_detail="Expense not found",
                )
            if line.service_catalogue_id:
                await assert_belongs_to_tenant(
                    self.db,
                    "service_catalogue",
                    line.service_catalogue_id,
                    self.tenant_id,
                    not_found_detail="Service catalogue item not found",
                )

            subtotal += line_amount
            tax_total += tax_amount
            line_payloads.append(
                {
                    "description": line.description,
                    "quantity": str(line.quantity),
                    "unit_price": serialise_money(line.unit_price),
                    "amount": serialise_money(line_amount),
                    "tax_rate_id": tax_rate_id,
                    "tax_amount": serialise_money(tax_amount),
                    "time_entry_id": line.time_entry_id,
                    "expense_id": line.expense_id,
                    "service_catalogue_id": line.service_catalogue_id,
                }
            )

        total = subtotal + tax_total
        if subtotal < Decimal("0") or total < Decimal("0"):
            raise HTTPException(
                status_code=422,
                detail="Invoice total cannot be negative after adjustments",
            )
        invoice_data["subtotal"] = serialise_money(subtotal)
        invoice_data["tax_total"] = serialise_money(tax_total)
        invoice_data["total"] = serialise_money(total)

        row = await self._repo.create(invoice_data)
        invoice_id = str(row["id"])

        # Insert lines
        line_rows: list[dict] = []
        for payload in line_payloads:
            line_data: dict = {
                "tenant_id": self.tenant_id,
                "invoice_id": invoice_id,
                "description": payload["description"],
                "quantity": payload["quantity"],
                "unit_price": payload["unit_price"],
                "amount": payload["amount"],
                "tax_amount": payload["tax_amount"],
            }
            if payload["tax_rate_id"]:
                line_data["tax_rate_id"] = payload["tax_rate_id"]
            if payload["time_entry_id"]:
                line_data["time_entry_id"] = payload["time_entry_id"]
            if payload["expense_id"]:
                line_data["expense_id"] = payload["expense_id"]
            if payload["service_catalogue_id"]:
                line_data["service_catalogue_id"] = payload["service_catalogue_id"]
            created_line = await self._repo.create_line(line_data)
            line_rows.append(created_line)

        await self._record_retainer_draw_from_lines(
            engagement_id=data.engagement_id,
            invoice_id=invoice_id,
            currency=data.currency,
            line_rows=line_rows,
            created_by=created_by,
        )

        logger.info(
            "Invoice created",
            extra={"invoice_id": invoice_id, "tenant_id": self.tenant_id},
        )
        return InvoiceResponse.from_db(row, line_rows)

    async def _record_retainer_draw_from_lines(
        self,
        *,
        engagement_id: str,
        invoice_id: str,
        currency: str,
        line_rows: list[dict],
        created_by: str,
    ) -> None:
        draw_amount = Decimal("0")
        for line in line_rows:
            description = str(line.get("description") or "").lower()
            amount = _to_decimal(line.get("amount"))
            if amount < 0 and "retainer applied" in description:
                draw_amount += -amount

        if draw_amount <= 0:
            return

        await record_retainer_draw(
            self.db,
            tenant_id=self.tenant_id,
            engagement_id=engagement_id,
            invoice_id=invoice_id,
            amount=draw_amount,
            currency=currency,
            description=f"Retainer draw applied to invoice {invoice_id}",
            created_by_user_id=created_by,
        )

    # ------------------------------------------------------------------
    # Lifecycle transitions
    # ------------------------------------------------------------------

    async def approve_invoice(self, invoice_id: str, approved_by: str) -> InvoiceResponse:
        """Move invoice to approved status and post AR journal.

        Journal: DR 1200 Accounts Receivable / CR 4000 Revenue + CR 2300 Sales Tax Payable.
        """
        row = await self._repo.get_by_id(invoice_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if row["status"] != "draft":
            raise HTTPException(
                status_code=409,
                detail=f"Invoice is already {row['status']} — cannot approve",
            )

        total = _to_decimal(row.get("total"))
        subtotal = _to_decimal(row.get("subtotal"))
        tax_total = _to_decimal(row.get("tax_total"))
        currency = row.get("currency", "USD")
        invoice_number = row.get("invoice_number", invoice_id[:8])

        # Resolve account IDs by code
        account_codes = ["1200", "4000"]
        if tax_total > Decimal("0"):
            account_codes.append("2300")
        acct_map = await self._repo.get_account_ids_by_codes(account_codes)

        lines = [
            JournalLineSpec(
                direction="DR",
                account_code="1200",
                amount=total,
                description=f"AR for invoice {invoice_number}",
                account_id=acct_map.get("1200"),
                currency=currency,
            ),
            JournalLineSpec(
                direction="CR",
                account_code="4000",
                amount=subtotal,
                description=f"Revenue for invoice {invoice_number}",
                account_id=acct_map.get("4000"),
                currency=currency,
            ),
        ]
        if tax_total > Decimal("0"):
            lines.append(
                JournalLineSpec(
                    direction="CR",
                    account_code="2300",
                    amount=tax_total,
                    description=f"Sales tax payable for invoice {invoice_number}",
                    account_id=acct_map.get("2300"),
                    currency=currency,
                )
            )

        entry_date = (
            row.get("issue_date")
            if row.get("issue_date")
            else date.today().isoformat()
        )

        try:
            post_journal(
                db=self.db,
                tenant_id=self.tenant_id,
                created_by=approved_by,
                description=f"AR for invoice {invoice_number}",
                entry_date=str(entry_date),
                reference_type="invoice",
                reference_id=invoice_id,
                lines=lines,
                entry_number=f"JE-INV-{invoice_number}",
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        updated = await self._repo.update(invoice_id, {"status": "approved"})
        if updated is None:
            raise HTTPException(status_code=404, detail="Invoice not found after update")

        invoice_lines = await self._repo.list_lines(invoice_id)

        # Back-link time entries — billing_status flips to "billed" the moment
        # the invoice is approved so reports/queries that filter on unbilled
        # time stop double-counting work that's already been invoiced.
        te_ids = [
            line["time_entry_id"]
            for line in invoice_lines
            if line.get("time_entry_id")
        ]
        if te_ids:
            await asyncio.to_thread(
                lambda: self.db.table("time_entries")
                .update({"invoice_id": invoice_id, "billing_status": "billed"})
                .in_("id", te_ids)
                .eq("tenant_id", self.tenant_id)
                .execute()
            )

        return InvoiceResponse.from_db(updated, invoice_lines)

    async def record_manual_payment(
        self,
        invoice_id: str,
        amount: Decimal,
        currency: str | None,
        paid_at_iso: str | None,
        notes: str | None,
        recorded_by: str,
    ) -> InvoiceResponse:
        """Record a payment received outside of Stripe (wire, cheque, cash, etc.).

        Mirrors the Stripe-webhook code path so accounting comes out identical:
        1. Validate the invoice exists, is approved/sent, and isn't already paid.
        2. Insert a payments row (no stripe_payment_intent_id).
        3. Update invoice → paid + set paid_at.
        4. Back-link any line.time_entry_id → time_entries.invoice_id/billing_status='billed'.
        5. Post the offsetting journal: DR 1100 Bank / CR 1200 AR.

        Currency defaults to the invoice currency; paid_at defaults to now.
        """
        row = await self._repo.get_by_id(invoice_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if row.get("status") == "paid":
            raise HTTPException(status_code=409, detail="Invoice is already paid")
        if row.get("status") not in ("approved", "sent"):
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Cannot record payment on invoice with status={row.get('status')!r}; "
                    "approve or send the invoice first."
                ),
            )

        if amount <= 0:
            raise HTTPException(status_code=422, detail="Payment amount must be > 0")

        invoice_currency = row.get("currency", "USD")
        pay_currency = (currency or invoice_currency).upper()
        paid_at = paid_at_iso or _dt.now(tz=UTC).isoformat()
        invoice_number = row.get("invoice_number", invoice_id[:8])

        # 1. payments row
        payment_data: dict = {
            "tenant_id": self.tenant_id,
            "invoice_id": invoice_id,
            "amount": str(amount),
            "currency": pay_currency,
            # FX conversion deferred to fx_refresh_worker — for same-currency
            # base it's a passthrough.
            "base_amount": str(amount),
            "paid_at": paid_at,
        }
        if notes:
            payment_data["notes"] = notes

        await asyncio.to_thread(
            lambda: self.db.table("payments").insert(payment_data).execute()
        )

        # 2. invoice → paid
        await asyncio.to_thread(
            lambda: self.db.table("invoices")
            .update({"status": "paid", "paid_at": paid_at})
            .eq("id", invoice_id)
            .eq("tenant_id", self.tenant_id)
            .execute()
        )

        # 3. back-link invoiced time entries
        line_rows = await asyncio.to_thread(
            lambda: self.db.table("invoice_lines")
            .select("time_entry_id")
            .eq("invoice_id", invoice_id)
            .execute()
            .data
            or []
        )
        te_ids = [r["time_entry_id"] for r in line_rows if r.get("time_entry_id")]
        if te_ids:
            await asyncio.to_thread(
                lambda: self.db.table("time_entries")
                .update({"invoice_id": invoice_id, "billing_status": "billed"})
                .in_("id", te_ids)
                .eq("tenant_id", self.tenant_id)
                .execute()
            )

        # 4. journal: DR 1100 Bank / CR 1200 AR
        acct_map = await self._repo.get_account_ids_by_codes(["1100", "1200"])
        journal_lines = [
            JournalLineSpec(
                direction="DR",
                account_code="1100",
                amount=amount,
                description=f"Payment received for invoice {invoice_number}",
                account_id=acct_map.get("1100"),
                currency=pay_currency,
            ),
            JournalLineSpec(
                direction="CR",
                account_code="1200",
                amount=amount,
                description=f"Payment received for invoice {invoice_number}",
                account_id=acct_map.get("1200"),
                currency=pay_currency,
            ),
        ]
        try:
            post_journal(
                db=self.db,
                tenant_id=self.tenant_id,
                created_by=recorded_by,
                description=f"Payment received for invoice {invoice_number}",
                entry_date=date.today().isoformat(),
                reference_type="payment",
                reference_id=invoice_id,
                lines=journal_lines,
            )
        except ValueError as exc:
            # accounting_guardian rejection — the payment row is already in,
            # surface a clear 422 so the caller knows the journal didn't land.
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        updated = await self._repo.get_by_id(invoice_id)
        invoice_lines = await self._repo.list_lines(invoice_id)
        return InvoiceResponse.from_db(updated or row, invoice_lines)

    async def send_invoice(self, invoice_id: str, sent_by: str) -> InvoiceResponse:
        """Send invoice: create Stripe Payment Link or fall back to PDF-only.

        If Stripe Connect is not configured for this tenant (#178), marks the
        invoice as 'sent' without a payment link so the user can share the
        public PDF URL directly.

        Security: Payment Link metadata is validated server-side.
        The public_token on the invoice is used for the redirect URL.
        """
        row = await self._repo.get_by_id(invoice_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if row["status"] not in ("approved", "draft"):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot send invoice with status={row['status']}",
            )

        total = _to_decimal(row.get("total"))
        currency = row.get("currency", "USD")
        invoice_number = row.get("invoice_number", "INV")
        public_token = row.get("public_token", invoice_id)

        # Fetch tenant connect info
        tenant = await self._repo.get_tenant()
        stripe_secret_configured = bool(settings.stripe_secret_key)

        # PDF-only path (#178): skip Stripe when secret key is absent.
        if not stripe_secret_configured:
            logger.info(
                "Invoice sent via PDF-only path (Stripe not configured)",
                extra={"invoice_id": invoice_id, "tenant_id": self.tenant_id},
            )
            updated = await self._repo.update(invoice_id, {"status": "sent"})
            if updated is None:
                raise HTTPException(status_code=404, detail="Invoice not found after update")
            invoice_lines = await self._repo.list_lines(invoice_id)
            return InvoiceResponse.from_db(updated, invoice_lines)

        try:
            # Create ephemeral Stripe Product + Price for this invoice
            product = stripe.Product.create(
                name=f"Invoice {invoice_number}",
                metadata={
                    "invoice_id": invoice_id,
                    "tenant_id": self.tenant_id,
                },
            )

            # Convert Decimal to integer cents (Stripe uses smallest currency unit)
            amount_int = int((total * 100).quantize(Decimal("1")))

            price = stripe.Price.create(
                product=product.id,
                unit_amount=amount_int,
                currency=currency.lower(),
            )

            # Build PaymentLink parameters
            pl_kwargs: dict = {
                "line_items": [{"price": price.id, "quantity": 1}],
                "metadata": {
                    "invoice_id": invoice_id,
                    "tenant_id": self.tenant_id,
                },
                "after_completion": {
                    "type": "redirect",
                    "redirect": {
                        "url": (
                            f"{settings.frontend_base_url}/p/{public_token}/thanks"
                        ),
                    },
                },
            }

            # Add Connect routing if tenant has an active connected account
            connect_id = tenant.get("stripe_connect_account_id") if tenant else None
            if connect_id and tenant and tenant.get("stripe_connect_charges_enabled"):
                pl_kwargs["on_behalf_of"] = connect_id
                pl_kwargs["transfer_data"] = {"destination": connect_id}

            payment_link = stripe.PaymentLink.create(**pl_kwargs)

        except stripe.StripeError as exc:
            logger.error(
                "Stripe PaymentLink creation failed",
                extra={
                    "invoice_id": invoice_id,
                    "tenant_id": self.tenant_id,
                    "stripe_code": getattr(exc, "code", "unknown"),
                },
            )
            raise HTTPException(
                status_code=502,
                detail="Payment link creation failed — please retry",
            ) from exc

        updated = await self._repo.update(
            invoice_id,
            {
                "status": "sent",
                "stripe_payment_link_id": payment_link.id,
                "stripe_payment_link_url": payment_link.url,
            },
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="Invoice not found after update")

        logger.info(
            "Invoice sent with Payment Link",
            extra={
                "invoice_id": invoice_id,
                "tenant_id": self.tenant_id,
                "payment_link_id": payment_link.id,
            },
        )

        invoice_lines = await self._repo.list_lines(invoice_id)
        response = InvoiceResponse.from_db(updated, invoice_lines)
        # Attach payment_link_url at the response level for immediate use
        response.payment_link_url = payment_link.url
        return response

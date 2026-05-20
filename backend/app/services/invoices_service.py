"""InvoicesService — handles invoice lifecycle including Stripe Payment Link creation.

Issue #50: Invoice send + Stripe Payment Link
"""
# Prahari review required — see docs/team/SECURITY_REVIEW.md

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal, InvalidOperation

import stripe
from fastapi import HTTPException

from app.core.config import settings
from app.domain.journal_helper import JournalLineSpec, post_journal
from app.models.invoices import InvoiceCreate, InvoiceResponse, PublicInvoiceResponse
from app.repositories.invoices_repo import InvoicesRepository
from supabase import Client

logger = logging.getLogger(__name__)


def _to_decimal(value: str | int | float | None, default: str = "0") -> Decimal:
    """Safely convert a value to Decimal; returns default on failure."""
    try:
        return Decimal(str(value)) if value is not None else Decimal(default)
    except InvalidOperation:
        return Decimal(default)


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

        # Compute totals from lines
        subtotal = Decimal("0")
        tax_total = Decimal("0")
        for line in data.lines:
            line_amount = (line.quantity * line.unit_price).quantize(Decimal("0.01"))
            subtotal += line_amount

        total = subtotal + tax_total
        invoice_data["subtotal"] = str(subtotal)
        invoice_data["tax_total"] = str(tax_total)
        invoice_data["total"] = str(total)

        row = await self._repo.create(invoice_data)
        invoice_id = str(row["id"])

        # Insert lines
        line_rows: list[dict] = []
        for line in data.lines:
            line_amount = (line.quantity * line.unit_price).quantize(Decimal("0.01"))
            line_data: dict = {
                "tenant_id": self.tenant_id,
                "invoice_id": invoice_id,
                "description": line.description,
                "quantity": str(line.quantity),
                "unit_price": str(line.unit_price),
                "amount": str(line_amount),
                "tax_amount": "0",
            }
            if line.tax_rate_id:
                line_data["tax_rate_id"] = line.tax_rate_id
            if line.time_entry_id:
                line_data["time_entry_id"] = line.time_entry_id
            if line.expense_id:
                line_data["expense_id"] = line.expense_id
            created_line = await self._repo.create_line(line_data)
            line_rows.append(created_line)

        logger.info(
            "Invoice created",
            extra={"invoice_id": invoice_id, "tenant_id": self.tenant_id},
        )
        return InvoiceResponse.from_db(row, line_rows)

    # ------------------------------------------------------------------
    # Lifecycle transitions
    # ------------------------------------------------------------------

    async def approve_invoice(self, invoice_id: str, approved_by: str) -> InvoiceResponse:
        """Move invoice to approved status and post AR journal.

        Journal: DR 1200 Accounts Receivable / CR 4000 Revenue
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
        currency = row.get("currency", "USD")
        invoice_number = row.get("invoice_number", invoice_id[:8])

        # Resolve account IDs by code
        acct_map = await self._repo.get_account_ids_by_codes(["1200", "4000"])

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
                amount=total,
                description=f"Revenue for invoice {invoice_number}",
                account_id=acct_map.get("4000"),
                currency=currency,
            ),
        ]

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
        return InvoiceResponse.from_db(updated, invoice_lines)

    async def send_invoice(self, invoice_id: str, sent_by: str) -> InvoiceResponse:
        """Send invoice: create Stripe Payment Link and update invoice status.

        The tenant's Stripe Connect account is used if connected and
        charges_enabled — otherwise the platform account is used.

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

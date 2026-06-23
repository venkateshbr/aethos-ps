"""Business logic for the Clients resource."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.models.clients import ClientCreate, ClientListResponse, ClientResponse, ClientUpdate
from app.repositories.clients_repo import ClientRepository
from supabase import Client

logger = logging.getLogger(__name__)

_VENDOR_KINDS = {"vendor", "both"}
_VENDOR_UPDATE_FIELDS = (
    "vendor_onboarding_status",
    "vendor_bank_account_status",
    "vendor_tax_validation_status",
    "vendor_sanctions_status",
    "vendor_remittance_status",
    "vendor_remittance_email",
    "vendor_payment_controls",
)


def _to_response(row: dict) -> ClientResponse:
    return ClientResponse(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        name=row["name"],
        kind=row["kind"],
        payment_terms_days=int(row["payment_terms_days"]),
        created_at=str(row["created_at"]),
        vendor_onboarding_status=row.get("vendor_onboarding_status") or "not_required",
        vendor_bank_account_status=row.get("vendor_bank_account_status") or "not_provided",
        vendor_tax_validation_status=row.get("vendor_tax_validation_status") or "not_checked",
        vendor_sanctions_status=row.get("vendor_sanctions_status") or "not_checked",
        vendor_remittance_status=row.get("vendor_remittance_status") or "not_configured",
        vendor_remittance_email=row.get("vendor_remittance_email"),
        vendor_payment_controls=dict(row.get("vendor_payment_controls") or {}),
        vendor_onboarding_approved_at=(
            str(row["vendor_onboarding_approved_at"])
            if row.get("vendor_onboarding_approved_at")
            else None
        ),
        vendor_onboarding_approved_by=(
            str(row["vendor_onboarding_approved_by"])
            if row.get("vendor_onboarding_approved_by")
            else None
        ),
    )


class ClientService:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self._repo = ClientRepository(db, tenant_id)

    async def list_clients(
        self,
        kind: str | None = None,
        q: str | None = None,
    ) -> ClientListResponse:
        rows = await self._repo.list(kind=kind, q=q)
        items = [_to_response(r) for r in rows]
        return ClientListResponse(items=items, total=len(items))

    async def get_client(self, id: str) -> ClientResponse | None:
        row = await self._repo.get(id)
        return _to_response(row) if row else None

    async def create_client(self, data: ClientCreate) -> ClientResponse:
        payload: dict = {
            "name": data.name,
            "kind": data.kind,
            "payment_terms_days": data.payment_terms_days,
            "vendor_onboarding_status": (
                data.vendor_onboarding_status
                if data.vendor_onboarding_status is not None
                else "pending"
                if data.kind in _VENDOR_KINDS
                else "not_required"
            ),
            "vendor_bank_account_status": data.vendor_bank_account_status,
            "vendor_tax_validation_status": data.vendor_tax_validation_status,
            "vendor_sanctions_status": data.vendor_sanctions_status,
            "vendor_remittance_status": data.vendor_remittance_status,
            "vendor_payment_controls": data.vendor_payment_controls,
        }
        if data.billing_address is not None:
            payload["billing_address"] = data.billing_address
        if data.tax_id is not None:
            payload["tax_id"] = data.tax_id
        if data.vendor_remittance_email is not None:
            payload["vendor_remittance_email"] = data.vendor_remittance_email
        row = await self._repo.create(payload)
        return _to_response(row)

    async def update_client(self, id: str, data: ClientUpdate) -> ClientResponse | None:
        patch: dict = {}
        raw = data.model_dump(exclude_unset=True)
        if data.name is not None:
            patch["name"] = data.name
        if data.kind is not None:
            patch["kind"] = data.kind
        if data.billing_address is not None:
            patch["billing_address"] = data.billing_address
        if data.tax_id is not None:
            patch["tax_id"] = data.tax_id
        if data.payment_terms_days is not None:
            patch["payment_terms_days"] = data.payment_terms_days

        for field in _VENDOR_UPDATE_FIELDS:
            if field in raw:
                patch[field] = raw[field]

        if not patch:
            # Nothing to update — return existing
            return await self.get_client(id)

        existing = await self._repo.get(id)
        if existing is None:
            return None

        target_kind = patch.get("kind", existing.get("kind"))
        if (
            target_kind in _VENDOR_KINDS
            and existing.get("vendor_onboarding_status", "not_required") == "not_required"
            and "vendor_onboarding_status" not in patch
        ):
            patch["vendor_onboarding_status"] = "pending"

        row = await self._repo.update(id, patch)
        return _to_response(row) if row else None

    async def approve_vendor_onboarding(self, id: str, approved_by: str) -> ClientResponse | None:
        row = await self._repo.get(id)
        if row is None:
            return None
        if row.get("kind") not in _VENDOR_KINDS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Only vendor-capable contacts can be approved for vendor onboarding",
            )

        unmet_controls: list[str] = []
        if row.get("vendor_bank_account_status") != "verified":
            unmet_controls.append("bank account must be verified")
        if row.get("vendor_tax_validation_status") != "valid":
            unmet_controls.append("tax validation must be valid")
        if row.get("vendor_sanctions_status") != "clear":
            unmet_controls.append("sanctions screening must be clear")
        if row.get("vendor_remittance_status") != "verified":
            unmet_controls.append("remittance controls must be verified")

        if unmet_controls:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "message": "Vendor onboarding controls are incomplete",
                    "unmet_controls": unmet_controls,
                },
            )

        approved = await self._repo.update(
            id,
            {
                "vendor_onboarding_status": "approved",
                "vendor_onboarding_approved_at": datetime.now(UTC).isoformat(),
                "vendor_onboarding_approved_by": approved_by,
            },
        )
        return _to_response(approved) if approved else None

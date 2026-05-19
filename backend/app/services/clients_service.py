"""Business logic for the Clients resource."""

from __future__ import annotations

import logging

from app.models.clients import ClientCreate, ClientListResponse, ClientResponse, ClientUpdate
from app.repositories.clients_repo import ClientRepository
from supabase import Client

logger = logging.getLogger(__name__)


def _to_response(row: dict) -> ClientResponse:
    return ClientResponse(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        name=row["name"],
        kind=row["kind"],
        payment_terms_days=int(row["payment_terms_days"]),
        created_at=str(row["created_at"]),
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
        }
        if data.billing_address is not None:
            payload["billing_address"] = data.billing_address
        if data.tax_id is not None:
            payload["tax_id"] = data.tax_id
        row = await self._repo.create(payload)
        return _to_response(row)

    async def update_client(self, id: str, data: ClientUpdate) -> ClientResponse | None:
        patch: dict = {}
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

        if not patch:
            # Nothing to update — return existing
            return await self.get_client(id)

        row = await self._repo.update(id, patch)
        return _to_response(row) if row else None

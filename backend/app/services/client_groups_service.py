"""Business logic for tenant-scoped client groups."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException

from app.models.client_groups import (
    ClientGroupCreate,
    ClientGroupListResponse,
    ClientGroupMemberCreate,
    ClientGroupMemberResponse,
    ClientGroupResponse,
    ClientGroupUpdate,
)
from supabase import Client


class ClientGroupsService:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def list_groups(self, client_id: str | None = None) -> ClientGroupListResponse:
        if client_id:
            self._require_client(client_id)
            membership_rows = (
                self.db.table("client_group_members")
                .select("group_id")
                .eq("tenant_id", self.tenant_id)
                .eq("client_id", client_id)
                .is_("deleted_at", "null")
                .execute()
                .data
                or []
            )
            group_ids = sorted({str(row["group_id"]) for row in membership_rows})
            if not group_ids:
                return ClientGroupListResponse(items=[], total=0)
            groups = (
                self._base_group_query()
                .in_("id", group_ids)
                .order("name")
                .execute()
                .data
                or []
            )
        else:
            groups = self._base_group_query().order("name").execute().data or []

        members_by_group = self._members_by_group([str(group["id"]) for group in groups])
        items = [
            _group_response(group, members_by_group.get(str(group["id"]), []))
            for group in groups
        ]
        return ClientGroupListResponse(items=items, total=len(items))

    def get_group(self, group_id: str) -> ClientGroupResponse:
        group = self._require_group(group_id)
        members = self._members_by_group([group_id]).get(group_id, [])
        return _group_response(group, members)

    def create_group(self, data: ClientGroupCreate) -> ClientGroupResponse:
        if data.primary_client_id:
            self._require_client(data.primary_client_id)
        if data.billing_client_id:
            self._require_client(data.billing_client_id)

        payload = {
            "tenant_id": self.tenant_id,
            "name": data.name,
            "group_type": data.group_type,
            "primary_client_id": data.primary_client_id,
            "billing_client_id": data.billing_client_id,
            "currency": data.currency.upper() if data.currency else None,
            "status": data.status,
        }
        group = (
            self.db.table("client_groups")
            .insert(payload)
            .execute()
            .data[0]
        )

        if data.primary_client_id:
            self.add_member(
                str(group["id"]),
                ClientGroupMemberCreate(
                    client_id=data.primary_client_id,
                    relationship_role="parent",
                    is_primary=True,
                ),
            )
        if data.billing_client_id and data.billing_client_id != data.primary_client_id:
            self.add_member(
                str(group["id"]),
                ClientGroupMemberCreate(
                    client_id=data.billing_client_id,
                    relationship_role="billing_entity",
                ),
            )

        return self.get_group(str(group["id"]))

    def update_group(self, group_id: str, data: ClientGroupUpdate) -> ClientGroupResponse:
        self._require_group(group_id)
        patch = data.model_dump(exclude_unset=True)
        if patch.get("primary_client_id"):
            self._require_client(str(patch["primary_client_id"]))
        if patch.get("billing_client_id"):
            self._require_client(str(patch["billing_client_id"]))
        if patch.get("currency"):
            patch["currency"] = str(patch["currency"]).upper()

        if patch:
            (
                self.db.table("client_groups")
                .update(patch)
                .eq("id", group_id)
                .eq("tenant_id", self.tenant_id)
                .execute()
            )

        return self.get_group(group_id)

    def add_member(
        self,
        group_id: str,
        data: ClientGroupMemberCreate,
    ) -> ClientGroupMemberResponse:
        self._require_group(group_id)
        client = self._require_client(data.client_id)

        if data.is_primary:
            (
                self.db.table("client_group_members")
                .update({"is_primary": False})
                .eq("tenant_id", self.tenant_id)
                .eq("group_id", group_id)
                .is_("deleted_at", "null")
                .execute()
            )

        existing = (
            self.db.table("client_group_members")
            .select("*")
            .eq("tenant_id", self.tenant_id)
            .eq("group_id", group_id)
            .eq("client_id", data.client_id)
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        payload = {
            "relationship_role": data.relationship_role,
            "is_primary": data.is_primary,
            "start_date": data.start_date,
            "end_date": data.end_date,
        }
        if existing:
            member = (
                self.db.table("client_group_members")
                .update(payload)
                .eq("id", existing[0]["id"])
                .eq("tenant_id", self.tenant_id)
                .execute()
                .data[0]
            )
        else:
            member = (
                self.db.table("client_group_members")
                .insert(
                    {
                        **payload,
                        "tenant_id": self.tenant_id,
                        "group_id": group_id,
                        "client_id": data.client_id,
                    }
                )
                .execute()
                .data[0]
            )

        group_patch: dict[str, str | None] = {}
        if data.is_primary:
            group_patch["primary_client_id"] = data.client_id
        if data.relationship_role == "billing_entity":
            group_patch["billing_client_id"] = data.client_id
        if group_patch:
            (
                self.db.table("client_groups")
                .update(group_patch)
                .eq("id", group_id)
                .eq("tenant_id", self.tenant_id)
                .execute()
            )

        member["clients"] = client
        return self._member_response(member)

    def remove_member(self, group_id: str, member_id: str) -> None:
        group = self._require_group(group_id)
        members = (
            self.db.table("client_group_members")
            .select("*")
            .eq("tenant_id", self.tenant_id)
            .eq("group_id", group_id)
            .eq("id", member_id)
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        if not members:
            raise HTTPException(status_code=404, detail="Client group member not found")

        member = members[0]
        now = datetime.now(tz=UTC).isoformat()
        (
            self.db.table("client_group_members")
            .update({"deleted_at": now, "is_primary": False})
            .eq("id", member_id)
            .eq("tenant_id", self.tenant_id)
            .execute()
        )

        patch: dict[str, None] = {}
        if group.get("primary_client_id") == member.get("client_id"):
            patch["primary_client_id"] = None
        if group.get("billing_client_id") == member.get("client_id"):
            patch["billing_client_id"] = None
        if patch:
            (
                self.db.table("client_groups")
                .update(patch)
                .eq("id", group_id)
                .eq("tenant_id", self.tenant_id)
                .execute()
            )

    def _base_group_query(self):  # type: ignore[no-untyped-def]
        return (
            self.db.table("client_groups")
            .select("*")
            .eq("tenant_id", self.tenant_id)
            .is_("deleted_at", "null")
        )

    def _require_group(self, group_id: str) -> dict:
        group = self._base_group_query().eq("id", group_id).execute().data or []
        if not group:
            raise HTTPException(status_code=404, detail="Client group not found")
        return group[0]

    def _require_client(self, client_id: str) -> dict:
        client = (
            self.db.table("clients")
            .select("id, name, kind")
            .eq("tenant_id", self.tenant_id)
            .eq("id", client_id)
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        return client[0]

    def _members_by_group(self, group_ids: list[str]) -> dict[str, list[ClientGroupMemberResponse]]:
        if not group_ids:
            return {}
        rows = (
            self.db.table("client_group_members")
            .select("*, clients!client_id(id, name, kind)")
            .eq("tenant_id", self.tenant_id)
            .in_("group_id", group_ids)
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        grouped: dict[str, list[ClientGroupMemberResponse]] = {}
        for row in rows:
            member = self._member_response(row)
            grouped.setdefault(member.group_id, []).append(member)
        for members in grouped.values():
            members.sort(key=lambda member: (not member.is_primary, member.client_name or ""))
        return grouped

    def _member_response(self, row: dict) -> ClientGroupMemberResponse:
        client = row.get("clients") or {}
        if isinstance(client, list):
            client = client[0] if client else {}
        return ClientGroupMemberResponse(
            id=str(row["id"]),
            tenant_id=str(row["tenant_id"]),
            group_id=str(row["group_id"]),
            client_id=str(row["client_id"]),
            client_name=client.get("name"),
            client_kind=client.get("kind"),
            relationship_role=str(row.get("relationship_role") or "other"),
            is_primary=bool(row.get("is_primary")),
            start_date=str(row["start_date"]) if row.get("start_date") else None,
            end_date=str(row["end_date"]) if row.get("end_date") else None,
            created_at=str(row["created_at"]),
        )


def _group_response(
    row: dict,
    members: list[ClientGroupMemberResponse],
) -> ClientGroupResponse:
    return ClientGroupResponse(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        name=str(row["name"]),
        group_type=str(row.get("group_type") or "other"),
        primary_client_id=(
            str(row["primary_client_id"]) if row.get("primary_client_id") else None
        ),
        billing_client_id=(
            str(row["billing_client_id"]) if row.get("billing_client_id") else None
        ),
        currency=str(row["currency"]) if row.get("currency") else None,
        status=str(row.get("status") or "active"),
        member_count=len(members),
        members=members,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )

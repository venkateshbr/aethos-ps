"""Tenant user administration service."""

from __future__ import annotations

import asyncio
import logging
import secrets
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from supabase_auth.errors import AuthApiError

from app.core.auth import CurrentUser
from app.core.rbac import ROLE_HIERARCHY, UserRole
from app.models.tenant_users import (
    TenantUserAuditEventListResponse,
    TenantUserAuditEventResponse,
    TenantUserInviteRequest,
    TenantUserInviteResponse,
    TenantUserListResponse,
    TenantUserResponse,
    TenantUserUpdateRequest,
)
from supabase import Client

logger = logging.getLogger(__name__)

ERP_ROLES = {"owner", "admin", "manager", "approver", "member", "auditor", "viewer"}
PRIVILEGED_ROLES = {"owner", "admin"}
_ERP_ROLE_LIST_TEXT = "owner, admin, manager, approver, member, auditor, or viewer"


class TenantUsersService:
    """Manage ERP tenant users and role assignments."""

    def __init__(self, db: Client, tenant_id: str) -> None:
        self._db = db
        self._tenant_id = tenant_id

    async def list_users(self, *, include_inactive: bool = False) -> TenantUserListResponse:
        def _list() -> list[dict[str, Any]]:
            query = (
                self._db.table("tenant_users")
                .select(
                    "id, tenant_id, user_id, email, display_name, role, invited_at, "
                    "joined_at, created_at, updated_at, deleted_at, deactivated_at"
                )
                .eq("tenant_id", self._tenant_id)
                .order("created_at", desc=False)
            )
            if not include_inactive:
                query = query.is_("deleted_at", "null")
            return query.execute().data or []

        rows = await asyncio.to_thread(_list)
        items = [_row_to_response(row) for row in rows]
        return TenantUserListResponse(items=items, total=len(items))

    async def invite_user(
        self,
        payload: TenantUserInviteRequest,
        *,
        actor: CurrentUser,
    ) -> TenantUserInviteResponse:
        actor_role = await self._actor_role(actor.user_id)
        requested_role = str(payload.role)
        self._assert_actor_can_assign_role(actor_role, requested_role)
        email = str(payload.email).lower()
        await self._assert_email_available(email)

        password = payload.password or _generate_temp_password()
        display_name = _display_name(payload.display_name, email)

        try:
            admin_response = self._db.auth.admin.create_user(
                {
                    "email": email,
                    "password": password,
                    "email_confirm": True,
                    "app_metadata": {
                        "role": requested_role,
                        "tenant_id": self._tenant_id,
                    },
                    "user_metadata": {"display_name": display_name},
                }
            )
        except AuthApiError as exc:
            logger.warning("tenant user invite auth creation failed: %s", exc.message)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Could not create this user. Check whether the email is already registered.",
            ) from exc

        user = admin_response.user if hasattr(admin_response, "user") else admin_response
        if not user:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable. Please try again.",
            )

        user_id = str(user.id)
        now = _utc_now()
        row = await asyncio.to_thread(
            lambda: self._db.table("tenant_users")
            .insert(
                {
                    "tenant_id": self._tenant_id,
                    "user_id": user_id,
                    "email": email,
                    "display_name": display_name,
                    "role": requested_role,
                    "invited_at": now,
                    "joined_at": now,
                    "invited_by_user_id": actor.user_id,
                }
            )
            .execute()
            .data[0]
        )

        await self._audit(
            tenant_user_id=str(row["id"]),
            actor_user_id=actor.user_id,
            action="invited",
            previous_role=None,
            new_role=requested_role,
            metadata={"email": email, "display_name": display_name},
        )

        set_password_url: str | None = None
        try:
            link = self._db.auth.admin.generate_link({"type": "recovery", "email": email})
            props = getattr(link, "properties", None)
            set_password_url = getattr(props, "action_link", None) if props else None
        except Exception:
            logger.warning("Could not generate recovery link for tenant user invite", exc_info=True)

        return TenantUserInviteResponse(
            **_row_to_response(row).model_dump(),
            set_password_url=set_password_url,
            temp_password=None if payload.password else password,
        )

    async def update_user(
        self,
        tenant_user_id: str,
        payload: TenantUserUpdateRequest,
        *,
        actor: CurrentUser,
    ) -> TenantUserResponse:
        row = await self._get_user_row(tenant_user_id)
        actor_role = await self._actor_role(actor.user_id)
        patch: dict[str, Any] = {}
        previous_role = str(row["role"])
        new_role = previous_role

        if payload.role is not None:
            new_role = str(payload.role)
            self._assert_actor_can_assign_role(actor_role, new_role)
            if previous_role in PRIVILEGED_ROLES and actor_role != "owner":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only owners can change owner or admin users.",
                )
            if str(row["user_id"]) == actor.user_id and new_role != previous_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Users cannot change their own tenant role.",
                )
            if previous_role == "owner" and new_role != "owner":
                await self._assert_not_last_owner(tenant_user_id)
            patch["role"] = new_role

        if payload.display_name is not None:
            patch["display_name"] = payload.display_name.strip() or None

        if not patch:
            return _row_to_response(row)

        updated = await asyncio.to_thread(
            lambda: self._db.table("tenant_users")
            .update(patch)
            .eq("id", tenant_user_id)
            .eq("tenant_id", self._tenant_id)
            .is_("deleted_at", "null")
            .execute()
            .data[0]
        )
        if "role" in patch:
            self._update_auth_role_best_effort(str(row["user_id"]), new_role)
        await self._audit(
            tenant_user_id=tenant_user_id,
            actor_user_id=actor.user_id,
            action="role_changed" if "role" in patch else "profile_updated",
            previous_role=previous_role if "role" in patch else None,
            new_role=new_role if "role" in patch else None,
            metadata={"fields": sorted(patch.keys())},
        )
        return _row_to_response(updated)

    async def deactivate_user(
        self,
        tenant_user_id: str,
        *,
        actor: CurrentUser,
    ) -> None:
        row = await self._get_user_row(tenant_user_id)
        actor_role = await self._actor_role(actor.user_id)
        if str(row["user_id"]) == actor.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Users cannot deactivate their own account.",
            )
        if str(row["role"]) in PRIVILEGED_ROLES and actor_role != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owners can deactivate owner or admin users.",
            )
        if str(row["role"]) == "owner":
            await self._assert_not_last_owner(tenant_user_id)

        now = _utc_now()
        await asyncio.to_thread(
            lambda: self._db.table("tenant_users")
            .update(
                {
                    "deleted_at": now,
                    "deactivated_at": now,
                    "deactivated_by_user_id": actor.user_id,
                }
            )
            .eq("id", tenant_user_id)
            .eq("tenant_id", self._tenant_id)
            .is_("deleted_at", "null")
            .execute()
        )
        await self._audit(
            tenant_user_id=tenant_user_id,
            actor_user_id=actor.user_id,
            action="deactivated",
            previous_role=str(row["role"]),
            new_role=None,
            metadata={"email": row.get("email")},
        )

    async def list_audit_events(
        self,
        *,
        tenant_user_id: str | None = None,
        limit: int = 100,
    ) -> TenantUserAuditEventListResponse:
        def _list() -> list[dict[str, Any]]:
            query = (
                self._db.table("tenant_user_audit_events")
                .select(
                    "id, tenant_id, tenant_user_id, actor_user_id, action, "
                    "previous_role, new_role, metadata, created_at"
                )
                .eq("tenant_id", self._tenant_id)
                .order("created_at", desc=True)
                .limit(limit)
            )
            if tenant_user_id:
                query = query.eq("tenant_user_id", tenant_user_id)
            return query.execute().data or []

        rows = await asyncio.to_thread(_list)
        items = [
            TenantUserAuditEventResponse(
                id=str(row["id"]),
                tenant_id=str(row["tenant_id"]),
                tenant_user_id=str(row["tenant_user_id"]) if row.get("tenant_user_id") else None,
                actor_user_id=str(row["actor_user_id"]) if row.get("actor_user_id") else None,
                action=str(row["action"]),
                previous_role=str(row["previous_role"]) if row.get("previous_role") else None,
                new_role=str(row["new_role"]) if row.get("new_role") else None,
                metadata=row.get("metadata") or {},
                created_at=str(row["created_at"]),
            )
            for row in rows
        ]
        return TenantUserAuditEventListResponse(items=items, total=len(items))

    async def _get_user_row(self, tenant_user_id: str) -> dict[str, Any]:
        def _get() -> dict[str, Any] | None:
            result = (
                self._db.table("tenant_users")
                .select("*")
                .eq("id", tenant_user_id)
                .eq("tenant_id", self._tenant_id)
                .is_("deleted_at", "null")
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None

        row = await asyncio.to_thread(_get)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant user not found",
            )
        return row

    async def _actor_role(self, actor_user_id: str) -> str:
        def _get() -> str | None:
            result = (
                self._db.table("tenant_users")
                .select("role")
                .eq("tenant_id", self._tenant_id)
                .eq("user_id", actor_user_id)
                .is_("deleted_at", "null")
                .limit(1)
                .execute()
            )
            return str(result.data[0]["role"]) if result.data else None

        role = await asyncio.to_thread(_get)
        if role not in ERP_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only ERP tenant users can administer users.",
            )
        return role

    async def _assert_email_available(self, email: str) -> None:
        def _exists() -> bool:
            result = (
                self._db.table("tenant_users")
                .select("id")
                .eq("tenant_id", self._tenant_id)
                .eq("email", email)
                .is_("deleted_at", "null")
                .limit(1)
                .execute()
            )
            return bool(result.data)

        if await asyncio.to_thread(_exists):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email already has active access to the tenant.",
            )

    async def _assert_not_last_owner(self, tenant_user_id: str) -> None:
        def _owner_count() -> int:
            result = (
                self._db.table("tenant_users")
                .select("id")
                .eq("tenant_id", self._tenant_id)
                .eq("role", "owner")
                .is_("deleted_at", "null")
                .execute()
            )
            return len(result.data or [])

        if await asyncio.to_thread(_owner_count) <= 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A tenant must keep at least one active owner.",
            )

    def _assert_actor_can_assign_role(self, actor_role: str, requested_role: str) -> None:
        if requested_role not in ERP_ROLES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"ERP user roles must be {_ERP_ROLE_LIST_TEXT}.",
            )
        actor_rank = ROLE_HIERARCHY[UserRole(actor_role)]
        if actor_rank < ROLE_HIERARCHY[UserRole.admin]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin or owner role required to manage tenant users.",
            )
        if requested_role in PRIVILEGED_ROLES and actor_role != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owners can grant owner or admin roles.",
            )

    async def _audit(
        self,
        *,
        tenant_user_id: str,
        actor_user_id: str,
        action: str,
        previous_role: str | None,
        new_role: str | None,
        metadata: dict[str, Any],
    ) -> None:
        await asyncio.to_thread(
            lambda: self._db.table("tenant_user_audit_events")
            .insert(
                {
                    "tenant_id": self._tenant_id,
                    "tenant_user_id": tenant_user_id,
                    "actor_user_id": actor_user_id,
                    "action": action,
                    "previous_role": previous_role,
                    "new_role": new_role,
                    "metadata": metadata,
                }
            )
            .execute()
        )

    def _update_auth_role_best_effort(self, user_id: str, role: str) -> None:
        try:
            self._db.auth.admin.update_user_by_id(
                user_id,
                {"app_metadata": {"role": role, "tenant_id": self._tenant_id}},
            )
        except Exception:
            logger.warning("Could not update tenant user auth metadata", exc_info=True)


def _row_to_response(row: dict[str, Any]) -> TenantUserResponse:
    return TenantUserResponse(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        user_id=str(row["user_id"]),
        email=row.get("email"),
        display_name=row.get("display_name"),
        role=str(row["role"]),
        status="inactive" if row.get("deleted_at") else "active",
        invited_at=str(row["invited_at"]) if row.get("invited_at") else None,
        joined_at=str(row["joined_at"]) if row.get("joined_at") else None,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        deactivated_at=str(row["deactivated_at"]) if row.get("deactivated_at") else None,
    )


def _generate_temp_password() -> str:
    return secrets.token_urlsafe(12) + "aA1!"


def _display_name(display_name: str | None, email: str) -> str:
    value = (display_name or "").strip()
    if value:
        return value
    return email.split("@", 1)[0].replace(".", " ").replace("_", " ").title()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()

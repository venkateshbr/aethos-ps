"""Enterprise RBAC catalog and effective-permission resolver."""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status

from app.core.rbac import ROLE_HIERARCHY, UserRole
from app.models.security import (
    CurrentUserPermissionsResponse,
    SecurityDutyResponse,
    SecurityPrivilegeListResponse,
    SecurityPrivilegeResponse,
    SecurityRoleCreateRequest,
    SecurityRoleListResponse,
    SecurityRoleResponse,
)
from supabase import Client

_ROLE_CODE_RE = re.compile(r"[^a-z0-9_]+")

LEGACY_ROLE_TO_SECURITY_ROLE: dict[str, str] = {
    "owner": "tenant_owner",
    "admin": "tenant_admin",
    "manager": "finance_ops_manager",
    "approver": "finance_approver",
    "member": "finance_operator",
    "auditor": "auditor",
    "viewer": "executive_viewer",
    "employee": "timesheet_employee",
}

SECURITY_ROLE_TO_LEGACY_ROLE: dict[str, str] = {
    "tenant_owner": "owner",
    "tenant_admin": "admin",
    "cfo": "admin",
    "finance_controller": "admin",
    "finance_ops_manager": "manager",
    "finance_approver": "approver",
    "finance_operator": "member",
    "procurement_manager": "manager",
    "buyer_requester": "member",
    "ap_manager": "manager",
    "ap_clerk": "manager",
    "ar_manager": "manager",
    "billing_specialist": "manager",
    "collections_specialist": "manager",
    "gl_accountant": "admin",
    "close_manager": "admin",
    "engagement_manager": "manager",
    "resource_manager": "manager",
    "auditor": "auditor",
    "executive_viewer": "viewer",
    "ai_ops_admin": "admin",
    "timesheet_employee": "employee",
}

_ROLE_GRANT_PRIVILEGE = "security.roles.manage"
_TENANT_USER_MANAGE_PRIVILEGE = "tenant.users.manage"


class SecurityService:
    """Read and manage tenant-scoped effective security configuration."""

    def __init__(self, db: Client, tenant_id: str) -> None:
        self._db = db
        self._tenant_id = tenant_id

    async def list_privileges(self) -> SecurityPrivilegeListResponse:
        rows = await asyncio.to_thread(
            lambda: self._db.table("security_privileges")
            .select("code, label, category, description")
            .order("category", desc=False)
            .order("code", desc=False)
            .execute()
            .data
            or []
        )
        items = [_privilege_response(row) for row in rows]
        return SecurityPrivilegeListResponse(items=items, total=len(items))

    async def list_roles(self) -> SecurityRoleListResponse:
        roles = await self._role_rows()
        role_ids = [str(row["id"]) for row in roles]
        duties_by_role = await self._duties_by_role(role_ids)
        items = [
            _role_response(row, duties_by_role.get(str(row["id"]), []))
            for row in roles
        ]
        return SecurityRoleListResponse(items=items, total=len(items))

    async def create_role(
        self,
        payload: SecurityRoleCreateRequest,
        *,
        actor_user_id: str,
    ) -> SecurityRoleResponse:
        actor = await self.effective_permissions(actor_user_id)
        if _ROLE_GRANT_PRIVILEGE not in actor.privilege_codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Security role administration permission required.",
            )

        code = _normalise_role_code(payload.code or payload.label)
        if not code:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Role code is required.",
            )
        legacy_role = _valid_legacy_role(payload.legacy_role)
        if legacy_role == "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Custom roles cannot grant Tenant Owner authority.",
            )

        duty_codes = sorted(set(payload.duty_codes))
        if not duty_codes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one duty is required.",
            )
        duties = await self._duty_rows_by_codes(duty_codes)
        found_codes = {str(row["code"]) for row in duties}
        missing = [code for code in duty_codes if code not in found_codes]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown duty codes: {', '.join(missing)}",
            )

        existing = await self._security_roles_by_codes([code])
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A role with this code already exists.",
            )

        row = await asyncio.to_thread(
            lambda: self._db.table("security_roles")
            .insert(
                {
                    "tenant_id": self._tenant_id,
                    "code": code,
                    "label": payload.label,
                    "description": payload.description or "",
                    "legacy_role": legacy_role,
                    "is_system": False,
                    "is_assignable": True,
                    "rank": ROLE_HIERARCHY[UserRole(legacy_role)],
                }
            )
            .execute()
            .data[0]
        )
        await asyncio.to_thread(
            lambda: [
                self._db.table("security_role_duties")
                .insert({"role_id": row["id"], "duty_id": duty["id"]})
                .execute()
                for duty in duties
            ]
        )
        await self.audit_role_event(
            actor_user_id=actor_user_id,
            action="role_created",
            role_code=code,
            previous_role_codes=[],
            new_role_codes=[code],
            metadata={"duty_codes": duty_codes, "legacy_role": legacy_role},
        )
        duties_by_role = await self._duties_by_role([str(row["id"])])
        return _role_response(row, duties_by_role.get(str(row["id"]), []))

    async def effective_permissions(self, user_id: str) -> CurrentUserPermissionsResponse:
        membership = await self.tenant_user_membership(user_id)
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant user not found.",
            )
        rows = await asyncio.to_thread(
            lambda: self._db.table("tenant_user_effective_privileges")
            .select("role_code, role_label, legacy_role, privilege_code")
            .eq("tenant_id", self._tenant_id)
            .eq("user_id", user_id)
            .execute()
            .data
            or []
        )
        role_codes: list[str] = []
        role_labels: list[str] = []
        privilege_codes: set[str] = set()
        legacy_roles: set[str] = set()
        for row in rows:
            role_code = str(row.get("role_code") or "")
            role_label = str(row.get("role_label") or "")
            privilege_code = str(row.get("privilege_code") or "")
            legacy_role = str(row.get("legacy_role") or "")
            if role_code and role_code not in role_codes:
                role_codes.append(role_code)
            if role_label and role_label not in role_labels:
                role_labels.append(role_label)
            if privilege_code:
                privilege_codes.add(privilege_code)
            if legacy_role:
                legacy_roles.add(legacy_role)

        if not role_codes:
            fallback_role = str(membership.get("role") or "viewer")
            role_codes = [LEGACY_ROLE_TO_SECURITY_ROLE.get(fallback_role, "executive_viewer")]
            role_labels = [role_codes[0].replace("_", " ").title()]
            legacy_roles = {fallback_role}

        legacy_role = highest_legacy_role(legacy_roles or {str(membership.get("role") or "viewer")})
        return CurrentUserPermissionsResponse(
            tenant_id=self._tenant_id,
            user_id=user_id,
            legacy_role=legacy_role,
            role_codes=role_codes,
            role_labels=role_labels,
            privilege_codes=sorted(privilege_codes),
            must_change_password=bool(membership.get("must_change_password")),
        )

    async def has_privilege(self, user_id: str, privilege_code: str) -> bool:
        permissions = await self.effective_permissions(user_id)
        return privilege_code in set(permissions.privilege_codes)

    async def resolve_assignable_roles(
        self,
        role_codes: list[str],
    ) -> tuple[list[dict[str, Any]], str]:
        unique_codes = sorted(set(role_codes))
        if not unique_codes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one security role is required.",
            )
        roles = await self._security_roles_by_codes(unique_codes)
        found_codes = {str(row["code"]) for row in roles}
        missing = [code for code in unique_codes if code not in found_codes]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown role codes: {', '.join(missing)}",
            )
        return roles, highest_legacy_role(str(row["legacy_role"]) for row in roles)

    async def tenant_user_membership(self, user_id: str) -> dict[str, Any] | None:
        rows = await asyncio.to_thread(
            lambda: self._db.table("tenant_users")
            .select("id, tenant_id, user_id, role, must_change_password")
            .eq("tenant_id", self._tenant_id)
            .eq("user_id", user_id)
            .is_("deleted_at", "null")
            .limit(1)
            .execute()
            .data
            or []
        )
        return rows[0] if rows else None

    async def assign_roles_to_tenant_user(
        self,
        tenant_user_id: str,
        role_codes: list[str],
        *,
        actor_user_id: str,
    ) -> tuple[list[dict[str, Any]], str]:
        actor = await self.effective_permissions(actor_user_id)
        if _TENANT_USER_MANAGE_PRIVILEGE not in actor.privilege_codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant user management permission required.",
            )
        unique_codes = sorted(set(role_codes))
        roles, legacy_role = await self.resolve_assignable_roles(unique_codes)
        if any(str(row.get("legacy_role")) == "owner" for row in roles) and "owner" not in {
            actor.legacy_role,
        }:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Tenant Owners can grant Tenant Owner authority.",
            )
        previous = await self.role_codes_for_tenant_user(tenant_user_id)
        await asyncio.to_thread(
            lambda: self._db.table("tenant_user_roles")
            .update({"deleted_at": _now_sql()})
            .eq("tenant_id", self._tenant_id)
            .eq("tenant_user_id", tenant_user_id)
            .is_("deleted_at", "null")
            .execute()
        )
        for role in roles:
            await asyncio.to_thread(
                lambda role=role: self._db.table("tenant_user_roles")
                .insert(
                    {
                        "tenant_id": self._tenant_id,
                        "tenant_user_id": tenant_user_id,
                        "security_role_id": role["id"],
                        "assigned_by_user_id": actor_user_id,
                    }
                )
                .execute()
            )
        await self.audit_role_event(
            actor_user_id=actor_user_id,
            action="replaced",
            role_code=None,
            previous_role_codes=previous,
            new_role_codes=unique_codes,
            metadata={"legacy_role": legacy_role},
            tenant_user_id=tenant_user_id,
        )
        return roles, legacy_role

    async def role_codes_for_tenant_user(self, tenant_user_id: str) -> list[str]:
        rows = await asyncio.to_thread(
            lambda: self._db.table("tenant_user_roles")
            .select("security_role_id")
            .eq("tenant_id", self._tenant_id)
            .eq("tenant_user_id", tenant_user_id)
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        role_ids = [str(row["security_role_id"]) for row in rows]
        if not role_ids:
            return []
        roles = await asyncio.to_thread(
            lambda: self._db.table("security_roles")
            .select("id, code")
            .in_("id", role_ids)
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        return sorted(str(row["code"]) for row in roles)

    async def clear_must_change_password(self, user_id: str) -> None:
        await asyncio.to_thread(
            lambda: self._db.table("tenant_users")
            .update({"must_change_password": False, "password_changed_at": _now_sql()})
            .eq("tenant_id", self._tenant_id)
            .eq("user_id", user_id)
            .is_("deleted_at", "null")
            .execute()
        )

    async def audit_role_event(
        self,
        *,
        actor_user_id: str,
        action: str,
        role_code: str | None,
        previous_role_codes: list[str],
        new_role_codes: list[str],
        metadata: dict[str, Any],
        tenant_user_id: str | None = None,
    ) -> None:
        await asyncio.to_thread(
            lambda: self._db.table("tenant_user_role_audit_events")
            .insert(
                {
                    "tenant_id": self._tenant_id,
                    "tenant_user_id": tenant_user_id,
                    "actor_user_id": actor_user_id,
                    "action": action,
                    "role_code": role_code,
                    "previous_role_codes": previous_role_codes,
                    "new_role_codes": new_role_codes,
                    "metadata": metadata,
                }
            )
            .execute()
        )

    async def _role_rows(self) -> list[dict[str, Any]]:
        rows = await asyncio.to_thread(
            lambda: self._db.table("security_roles")
            .select(
                "id, tenant_id, code, label, description, legacy_role, is_system, "
                "is_assignable, rank, deleted_at"
            )
            .is_("deleted_at", "null")
            .order("rank", desc=True)
            .execute()
            .data
            or []
        )
        return [
            row
            for row in rows
            if row.get("tenant_id") in (None, self._tenant_id)
        ]

    async def _security_roles_by_codes(self, role_codes: list[str]) -> list[dict[str, Any]]:
        rows = await asyncio.to_thread(
            lambda: self._db.table("security_roles")
            .select(
                "id, tenant_id, code, label, description, legacy_role, is_system, "
                "is_assignable, rank, deleted_at"
            )
            .in_("code", role_codes)
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        candidates = [
            row
            for row in rows
            if row.get("tenant_id") in (None, self._tenant_id)
            and bool(row.get("is_assignable", True))
        ]
        by_code: dict[str, dict[str, Any]] = {}
        for row in candidates:
            code = str(row["code"])
            if code not in by_code or row.get("tenant_id") == self._tenant_id:
                by_code[code] = row
        return [by_code[code] for code in role_codes if code in by_code]

    async def _duty_rows_by_codes(self, duty_codes: list[str]) -> list[dict[str, Any]]:
        return await asyncio.to_thread(
            lambda: self._db.table("security_duties")
            .select("id, code, label, description")
            .in_("code", duty_codes)
            .execute()
            .data
            or []
        )

    async def _duties_by_role(
        self,
        role_ids: list[str],
    ) -> dict[str, list[SecurityDutyResponse]]:
        if not role_ids:
            return {}
        role_duty_rows = await asyncio.to_thread(
            lambda: self._db.table("security_role_duties")
            .select("role_id, duty_id")
            .in_("role_id", role_ids)
            .execute()
            .data
            or []
        )
        duty_ids = sorted({str(row["duty_id"]) for row in role_duty_rows})
        if not duty_ids:
            return {}
        duty_rows = await asyncio.to_thread(
            lambda: self._db.table("security_duties")
            .select("id, code, label, description")
            .in_("id", duty_ids)
            .execute()
            .data
            or []
        )
        duty_priv_rows = await asyncio.to_thread(
            lambda: self._db.table("security_duty_privileges")
            .select("duty_id, privilege_id")
            .in_("duty_id", duty_ids)
            .execute()
            .data
            or []
        )
        privilege_ids = sorted({str(row["privilege_id"]) for row in duty_priv_rows})
        privilege_rows = []
        if privilege_ids:
            privilege_rows = await asyncio.to_thread(
                lambda: self._db.table("security_privileges")
                .select("id, code, label, category, description")
                .in_("id", privilege_ids)
                .execute()
                .data
                or []
            )
        privileges_by_id = {
            str(row["id"]): _privilege_response(row)
            for row in privilege_rows
        }
        privileges_by_duty: dict[str, list[SecurityPrivilegeResponse]] = {}
        for row in duty_priv_rows:
            privilege = privileges_by_id.get(str(row["privilege_id"]))
            if privilege:
                privileges_by_duty.setdefault(str(row["duty_id"]), []).append(privilege)

        duties_by_id = {
            str(row["id"]): SecurityDutyResponse(
                code=str(row["code"]),
                label=str(row["label"]),
                description=str(row.get("description") or ""),
                privileges=sorted(
                    privileges_by_duty.get(str(row["id"]), []),
                    key=lambda item: item.code,
                ),
            )
            for row in duty_rows
        }
        result: dict[str, list[SecurityDutyResponse]] = {}
        for row in role_duty_rows:
            duty = duties_by_id.get(str(row["duty_id"]))
            if duty:
                result.setdefault(str(row["role_id"]), []).append(duty)
        for key, duties in result.items():
            result[key] = sorted(duties, key=lambda item: item.code)
        return result


def highest_legacy_role(roles: Any) -> str:
    resolved: list[UserRole] = []
    for role in roles:
        try:
            resolved.append(UserRole(str(role)))
        except ValueError:
            continue
    if not resolved:
        return UserRole.viewer.value
    return max(resolved, key=lambda role: ROLE_HIERARCHY[role]).value


def _valid_legacy_role(role: str) -> str:
    try:
        return UserRole(role).value
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid legacy role projection.",
        ) from exc


def _normalise_role_code(value: str) -> str:
    code = _ROLE_CODE_RE.sub("_", value.strip().lower()).strip("_")
    return re.sub(r"_+", "_", code)


def _privilege_response(row: dict[str, Any]) -> SecurityPrivilegeResponse:
    return SecurityPrivilegeResponse(
        code=str(row["code"]),
        label=str(row["label"]),
        category=str(row["category"]),
        description=str(row.get("description") or ""),
    )


def _role_response(
    row: dict[str, Any],
    duties: list[SecurityDutyResponse],
) -> SecurityRoleResponse:
    privilege_codes = sorted(
        {
            privilege.code
            for duty in duties
            for privilege in duty.privileges
        }
    )
    return SecurityRoleResponse(
        id=str(row["id"]),
        code=str(row["code"]),
        label=str(row["label"]),
        description=str(row.get("description") or ""),
        legacy_role=str(row.get("legacy_role") or "member"),
        is_system=bool(row.get("is_system")),
        is_assignable=bool(row.get("is_assignable", True)),
        rank=int(row.get("rank") or 0),
        duties=duties,
        privilege_codes=privilege_codes,
    )


def _now_sql() -> str:
    return datetime.now(UTC).isoformat()

"""Business logic for the employees resource (issue #134, Phase 1).

Validation rules:
- email must be unique per tenant (active rows only).
- manager_id, if set, must reference an employee in the same tenant.
- Rates use Decimal and persist as strings (NUMERIC(15,2)).
"""

from __future__ import annotations

import logging
import secrets

from fastapi import HTTPException, status
from supabase_auth.errors import AuthApiError

from app.models.employees import (
    EmployeeCreate,
    EmployeeInviteRequest,
    EmployeeInviteResponse,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeUpdate,
)
from app.repositories.employees_repo import EmployeesRepository
from supabase import Client

logger = logging.getLogger(__name__)


class EmployeesService:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self._db = db
        self._repo = EmployeesRepository(db, tenant_id)
        self._tenant_id = tenant_id

    async def list_employees(
        self, status_filter: str | None = None, search: str | None = None, limit: int = 200
    ) -> EmployeeListResponse:
        rows = await self._repo.list(status=status_filter, search=search, limit=limit)
        items = [_row_to_response(r) for r in rows]
        return EmployeeListResponse(items=items, total=len(items))

    async def get_employee(self, employee_id: str) -> EmployeeResponse | None:
        row = await self._repo.get(employee_id)
        return _row_to_response(row) if row else None

    async def create_employee(self, data: EmployeeCreate) -> EmployeeResponse:
        if await self._repo.email_exists(data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An employee with email {data.email!r} already exists",
            )
        await self._assert_manager_valid(data.manager_id)

        payload: dict = {
            "first_name": data.first_name,
            "last_name": data.last_name,
            "email": str(data.email),
            "title": data.title,
            "department": data.department,
            "employment_type": data.employment_type.value,
            "default_bill_rate": str(data.default_bill_rate) if data.default_bill_rate is not None else None,
            "default_bill_rate_currency": data.default_bill_rate_currency,
            "cost_rate": str(data.cost_rate) if data.cost_rate is not None else None,
            "available_hours_per_week": (
                str(data.available_hours_per_week)
                if data.available_hours_per_week is not None
                else None
            ),
            "manager_id": data.manager_id,
            "skills": data.skills,
            "status": "active",
        }
        row = await self._repo.create(payload)
        return _row_to_response(row)

    async def update_employee(self, employee_id: str, data: EmployeeUpdate) -> EmployeeResponse:
        existing = await self._repo.get(employee_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee {employee_id!r} not found",
            )

        if data.email is not None and await self._repo.email_exists(
            str(data.email), exclude_id=employee_id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An employee with email {data.email!r} already exists",
            )
        if data.manager_id is not None:
            if data.manager_id == employee_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="An employee cannot be their own manager",
                )
            await self._assert_manager_valid(data.manager_id)

        patch: dict = {}
        for field in (
            "first_name",
            "last_name",
            "title",
            "department",
            "manager_id",
            "status",
        ):
            val = getattr(data, field)
            if val is not None:
                patch[field] = val
        if data.email is not None:
            patch["email"] = str(data.email)
        if data.employment_type is not None:
            patch["employment_type"] = data.employment_type.value
        if data.default_bill_rate is not None:
            patch["default_bill_rate"] = str(data.default_bill_rate)
        if data.default_bill_rate_currency is not None:
            patch["default_bill_rate_currency"] = data.default_bill_rate_currency
        if data.cost_rate is not None:
            patch["cost_rate"] = str(data.cost_rate)
        if data.available_hours_per_week is not None:
            patch["available_hours_per_week"] = str(data.available_hours_per_week)
        if data.skills is not None:
            patch["skills"] = data.skills

        if not patch:
            return _row_to_response(existing)

        row = await self._repo.update(employee_id, patch)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee {employee_id!r} not found",
            )
        return _row_to_response(row)

    async def delete_employee(self, employee_id: str) -> None:
        existing = await self._repo.get(employee_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee {employee_id!r} not found",
            )
        await self._repo.soft_delete(employee_id)

    # ------------------------------------------------------------------
    # Invite — turn an employee into a Timesheet-Portal login (#134 P3)
    # ------------------------------------------------------------------

    async def invite_employee(
        self, employee_id: str, data: EmployeeInviteRequest
    ) -> EmployeeInviteResponse:
        emp = await self._repo.get(employee_id)
        if emp is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee {employee_id!r} not found",
            )
        if emp.get("user_id"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This employee already has portal access.",
            )
        email = emp["email"]
        password = data.password or _generate_temp_password()

        # 1. Create the Supabase auth user via the admin API (does NOT mutate the
        #    service-role session — the #121 / signup pattern).
        try:
            admin_response = self._db.auth.admin.create_user(
                {"email": email, "password": password, "email_confirm": True}
            )
        except AuthApiError as exc:
            logger.warning("Failed to create auth user for employee: %s", exc.message)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Could not create employee login. Please check the email and try again.",
            ) from exc
        user = admin_response.user if hasattr(admin_response, "user") else admin_response
        if not user:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable. Please try again.",
            )
        user_id = user.id

        # 2. Membership row with the narrow 'employee' role.
        tu = (
            self._db.table("tenant_users")
            .insert({"tenant_id": self._tenant_id, "user_id": user_id, "role": "employee"})
            .execute()
        )
        tenant_user_id = str(tu.data[0]["id"])

        # 3. Link the employee record to the login.
        await self._repo.update(
            employee_id, {"user_id": user_id, "tenant_user_id": tenant_user_id}
        )

        # 4. Mint a one-time recovery (set-password) link to share. Email send is
        #    not wired for the pilot, so we return the link + the temp password.
        set_password_url: str | None = None
        try:
            link = self._db.auth.admin.generate_link(
                {"type": "recovery", "email": email}
            )
            props = getattr(link, "properties", None)
            set_password_url = getattr(props, "action_link", None) if props else None
        except Exception:
            # Link generation is best-effort; the temp password is the fallback.
            logger.warning("Could not generate recovery link for employee invite", exc_info=True)

        return EmployeeInviteResponse(
            employee_id=employee_id,
            user_id=user_id,
            tenant_user_id=tenant_user_id,
            email=email,
            set_password_url=set_password_url,
            temp_password=None if data.password else password,
        )

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    async def _assert_manager_valid(self, manager_id: str | None) -> None:
        if manager_id and not await self._repo.belongs_to_tenant(manager_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Manager {manager_id!r} not found",
            )


def _generate_temp_password() -> str:
    """A strong URL-safe temporary password (pilot invite fallback)."""
    return secrets.token_urlsafe(12) + "aA1!"


def _row_to_response(row: dict) -> EmployeeResponse:
    return EmployeeResponse(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        first_name=row["first_name"],
        last_name=row["last_name"],
        email=row["email"],
        title=row.get("title"),
        department=row.get("department"),
        employment_type=row.get("employment_type", "full_time"),
        default_bill_rate=row.get("default_bill_rate"),
        default_bill_rate_currency=row.get("default_bill_rate_currency"),
        cost_rate=row.get("cost_rate"),
        available_hours_per_week=row.get("available_hours_per_week"),
        manager_id=str(row["manager_id"]) if row.get("manager_id") else None,
        skills=row.get("skills") or [],
        user_id=str(row["user_id"]) if row.get("user_id") else None,
        tenant_user_id=str(row["tenant_user_id"]) if row.get("tenant_user_id") else None,
        has_login=bool(row.get("user_id")),
        status=row.get("status", "active"),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]) if row.get("updated_at") else None,
    )

"""Bill payment batch endpoints.

# Prahari review required — see docs/team/SECURITY_REVIEW.md

RBAC:
  read:    authenticated user (viewer+)
  create:  admin+
  approve: admin+
  export:  admin+
  propose: admin+
"""

from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.services.bill_payments_service import BillPaymentsService
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()


def _service(
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> BillPaymentsService:
    return BillPaymentsService(db, tenant_id)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class CreateBatchRequest(BaseModel):
    bill_ids: list[str]
    pay_date: date | None = None
    bank_account_label: str = ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/batches")
def list_batches(
    status: str | None = Query(None),
    svc: BillPaymentsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> list[dict]:
    return svc.list_batches(status=status)


@router.post("/batches", status_code=201)
def create_batch(
    body: CreateBatchRequest,
    svc: BillPaymentsService = Depends(_service),  # noqa: B008
    user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
) -> dict:
    return svc.create_batch(body.bill_ids, body.pay_date, body.bank_account_label, user.user_id)


@router.get("/batches/{batch_id}")
def get_batch(
    batch_id: str,
    svc: BillPaymentsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> dict:
    return svc.get_batch(batch_id)


@router.post("/batches/{batch_id}/approve")
def approve_batch(
    batch_id: str,
    svc: BillPaymentsService = Depends(_service),  # noqa: B008
    user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
) -> dict:
    return svc.approve_batch(batch_id, user.user_id)


@router.get("/batches/{batch_id}/export")
def export_batch(
    batch_id: str,
    format: str = Query("csv", pattern="^(nacha|csv)$"),
    svc: BillPaymentsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
) -> Response:
    if format == "nacha":
        content = svc.export_nacha(batch_id)
        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename=batch-{batch_id[:8]}.txt"},
        )
    content = svc.export_csv(batch_id)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=batch-{batch_id[:8]}.csv"},
    )


@router.patch("/batches/{batch_id}/mark-sent")
def mark_sent(
    batch_id: str,
    svc: BillPaymentsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
) -> dict:
    return svc.mark_sent(batch_id)


@router.post("/propose")
async def propose(
    due_within_days: int = Query(7, ge=1, le=90),
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
    user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
) -> dict:
    """Ask the bill_pay_agent to propose a payment batch.

    Always L2 — writes an agent_suggestion + hitl_task for human approval.
    """
    from app.agents.base import AgentDeps
    from app.agents.bill_pay_agent import propose_payment_batch
    from app.agents.suggestion_writer import write_agent_suggestion

    deps = AgentDeps(tenant_id=tenant_id, user_id=user.user_id, db=db)
    proposal = propose_payment_batch(deps, due_within_days)

    await write_agent_suggestion(
        deps,
        agent_name="bill_pay_agent",
        action_type="create_bill_payment_batch",
        # Bill-pay sweeps approved bills and has no single source document,
        # so we pass None for document_id. Previously this passed user.user_id
        # which violated agent_suggestions.original_document_id FK (#102).
        document_id=None,
        output=proposal.model_dump(mode="json"),
        confidence=proposal.confidence,
        autonomy_level=2,  # ALWAYS L2 — money-out requires human approval
    )

    logger.info(
        "bill_pay_agent_proposal_written",
        extra={
            "tenant_id": tenant_id,
            "user_id": user.user_id,
            "bill_count": len(proposal.proposed_bill_ids),
            "total": str(proposal.total_amount),
        },
    )

    return proposal.model_dump(mode="json")

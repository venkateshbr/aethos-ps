"""Procurement document router for purchase orders and service orders."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.procurement import (
    ProcurementConvertRequest,
    ProcurementDocumentCreate,
    ProcurementDocumentListResponse,
    ProcurementDocumentResponse,
)
from app.services.procurement_service import ProcurementService
from supabase import Client

router = APIRouter()

DocumentTypeQuery = Annotated[str | None, Query(description="purchase_order or service_order")]
StatusQuery = Annotated[str | None, Query(description="Filter by document status")]
ClientIdQuery = Annotated[str | None, Query(description="Filter by vendor UUID")]
LimitQuery = Annotated[int, Query(ge=1, le=100)]


def _read_service(
    db: Client = Depends(get_user_rls_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> ProcurementService:
    return ProcurementService(db, tenant_id)


def _write_service(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> ProcurementService:
    return ProcurementService(db, tenant_id)


@router.get("/documents", response_model=ProcurementDocumentListResponse)
async def list_procurement_documents(
    document_type: DocumentTypeQuery = None,
    status: StatusQuery = None,
    client_id: ClientIdQuery = None,
    limit: LimitQuery = 50,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: ProcurementService = Depends(_read_service),  # noqa: B008
) -> ProcurementDocumentListResponse:
    return await svc.list_documents(
        document_type=document_type,
        status_filter=status,
        client_id=client_id,
        limit=limit,
    )


@router.post(
    "/documents",
    response_model=ProcurementDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_procurement_document(
    payload: ProcurementDocumentCreate,
    current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: ProcurementService = Depends(_write_service),  # noqa: B008
) -> ProcurementDocumentResponse:
    return await svc.create_document(payload, requested_by=current_user.user_id)


@router.get("/documents/{document_id}", response_model=ProcurementDocumentResponse)
async def get_procurement_document(
    document_id: str,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: ProcurementService = Depends(_read_service),  # noqa: B008
) -> ProcurementDocumentResponse:
    document = await svc.get_document(document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procurement document not found",
        )
    return document


@router.post("/documents/{document_id}/approve", response_model=ProcurementDocumentResponse)
async def approve_procurement_document(
    document_id: str,
    current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    svc: ProcurementService = Depends(_write_service),  # noqa: B008
) -> ProcurementDocumentResponse:
    document = await svc.approve_document(
        document_id,
        approved_by=current_user.user_id,
        approver_role=current_user.role,
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procurement document not found",
        )
    return document


@router.post(
    "/documents/{document_id}/convert-to-order",
    response_model=ProcurementDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def convert_purchase_request_to_order(
    document_id: str,
    payload: ProcurementConvertRequest | None = None,
    current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: ProcurementService = Depends(_write_service),  # noqa: B008
) -> ProcurementDocumentResponse:
    document = await svc.convert_request_to_order(
        document_id,
        payload=payload or ProcurementConvertRequest(),
        converted_by=current_user.user_id,
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procurement document not found",
        )
    return document

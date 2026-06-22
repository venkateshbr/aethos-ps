"""Client group endpoints for related entities and rollups."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.client_groups import (
    ClientGroupCreate,
    ClientGroupListResponse,
    ClientGroupMemberCreate,
    ClientGroupMemberResponse,
    ClientGroupResponse,
    ClientGroupUpdate,
)
from app.services.client_groups_service import ClientGroupsService
from supabase import Client

router = APIRouter()


def _service(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> ClientGroupsService:
    return ClientGroupsService(db, tenant_id)


@router.get("", response_model=ClientGroupListResponse)
def list_client_groups(
    client_id: str | None = Query(default=None, description="Filter groups containing this client"),
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: ClientGroupsService = Depends(_service),  # noqa: B008
) -> ClientGroupListResponse:
    return svc.list_groups(client_id=client_id)


@router.post("", response_model=ClientGroupResponse, status_code=status.HTTP_201_CREATED)
def create_client_group(
    payload: ClientGroupCreate,
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: ClientGroupsService = Depends(_service),  # noqa: B008
) -> ClientGroupResponse:
    return svc.create_group(payload)


@router.get("/{group_id}", response_model=ClientGroupResponse)
def get_client_group(
    group_id: str,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: ClientGroupsService = Depends(_service),  # noqa: B008
) -> ClientGroupResponse:
    return svc.get_group(group_id)


@router.patch("/{group_id}", response_model=ClientGroupResponse)
def update_client_group(
    group_id: str,
    payload: ClientGroupUpdate,
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: ClientGroupsService = Depends(_service),  # noqa: B008
) -> ClientGroupResponse:
    return svc.update_group(group_id, payload)


@router.post(
    "/{group_id}/members",
    response_model=ClientGroupMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_client_group_member(
    group_id: str,
    payload: ClientGroupMemberCreate,
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: ClientGroupsService = Depends(_service),  # noqa: B008
) -> ClientGroupMemberResponse:
    return svc.add_member(group_id, payload)


@router.delete("/{group_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_client_group_member(
    group_id: str,
    member_id: str,
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: ClientGroupsService = Depends(_service),  # noqa: B008
) -> Response:
    svc.remove_member(group_id, member_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

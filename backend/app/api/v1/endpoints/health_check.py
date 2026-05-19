"""Internal ping endpoint — used by load balancers and integration tests."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def ping() -> dict[str, bool]:
    return {"pong": True}

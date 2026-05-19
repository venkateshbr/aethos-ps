"""Top-level v1 API router.

Import all endpoint sub-routers here and include them with their prefixes.
Keep this file thin — it is purely a registry.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import health_check

api_router = APIRouter()

api_router.include_router(health_check.router, prefix="/ping", tags=["ops"])

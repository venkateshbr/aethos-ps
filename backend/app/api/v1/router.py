"""Top-level v1 API router.

Import all endpoint sub-routers here and include them with their prefixes.
Keep this file thin — it is purely a registry.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import clients, engagements, health_check, projects, rate_cards

api_router = APIRouter()

api_router.include_router(health_check.router, prefix="/ping", tags=["ops"])
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(rate_cards.router, prefix="/rate-cards", tags=["rate-cards"])
api_router.include_router(engagements.router, prefix="/engagements", tags=["engagements"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])

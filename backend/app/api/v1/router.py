"""Top-level v1 API router.

Import all endpoint sub-routers here and include them with their prefixes.
Keep this file thin — it is purely a registry.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import auth, billing, chat, documents, health_check, webhooks

api_router = APIRouter()

api_router.include_router(health_check.router, prefix="/ping", tags=["ops"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])

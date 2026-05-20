"""Top-level v1 API router.

Import all endpoint sub-routers here and include them with their prefixes.
Keep this file thin — it is purely a registry.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    accounting,
    auth,
    bill_payments,
    billing,
    bills,
    chat,
    clients,
    documents,
    engagements,
    health_check,
    inbox,
    invoices,
    projects,
    rate_cards,
    reports,
    stripe_connect,
    time_entries,
    webhooks,
)

api_router = APIRouter()

api_router.include_router(health_check.router, prefix="/ping", tags=["ops"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(rate_cards.router, prefix="/rate-cards", tags=["rate-cards"])
api_router.include_router(engagements.router, prefix="/engagements", tags=["engagements"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(bills.router, prefix="/bills", tags=["bills"])
api_router.include_router(inbox.router, prefix="/inbox", tags=["inbox"])
api_router.include_router(accounting.router, prefix="/accounting", tags=["accounting"])
api_router.include_router(time_entries.router, prefix="/time-entries", tags=["time-entries"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
api_router.include_router(invoices.public_router, prefix="/public/invoices", tags=["public"])
api_router.include_router(stripe_connect.router, prefix="/stripe/connect", tags=["stripe-connect"])
api_router.include_router(bill_payments.router, prefix="/bill-payments", tags=["bill-payments"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])

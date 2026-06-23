"""Top-level v1 API router.

Import all endpoint sub-routers here and include them with their prefixes.
Keep this file thin — it is purely a registry.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    accounting,
    accounts,
    agents,
    auth,
    bill_payments,
    billing,
    billing_runs,
    bills,
    chat,
    client_groups,
    clients,
    collections_policy,
    documents,
    employees,
    engagements,
    expenses,
    financial_events,
    fx_rates,
    health_check,
    inbox,
    integrations,
    invoices,
    localization,
    payments,
    projects,
    rate_cards,
    reports,
    service_catalogue,
    stripe_connect,
    tax_rates,
    tenants,
    time_entries,
    timesheet,
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
api_router.include_router(collections_policy.router, prefix="/collections", tags=["collections"])
api_router.include_router(client_groups.router, prefix="/client-groups", tags=["client-groups"])
api_router.include_router(rate_cards.router, prefix="/rate-cards", tags=["rate-cards"])
api_router.include_router(engagements.router, prefix="/engagements", tags=["engagements"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(expenses.router, prefix="/expenses", tags=["expenses"])
api_router.include_router(bills.router, prefix="/bills", tags=["bills"])
api_router.include_router(inbox.router, prefix="/inbox", tags=["inbox"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
api_router.include_router(accounting.router, prefix="/accounting", tags=["accounting"])
api_router.include_router(employees.router, prefix="/employees", tags=["employees"])
api_router.include_router(time_entries.router, prefix="/time-entries", tags=["time-entries"])
api_router.include_router(timesheet.router, prefix="/timesheet", tags=["timesheet"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
api_router.include_router(invoices.public_router, prefix="/public/invoices", tags=["public"])
api_router.include_router(localization.router, prefix="/localization", tags=["localization"])
api_router.include_router(stripe_connect.router, prefix="/stripe/connect", tags=["stripe-connect"])
api_router.include_router(bill_payments.router, prefix="/bill-payments", tags=["bill-payments"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(financial_events.router, prefix="/financial-events", tags=["financial-events"])
api_router.include_router(billing_runs.router, prefix="/billing-runs", tags=["billing-runs"])
api_router.include_router(fx_rates.router, prefix="/fx-rates", tags=["fx-rates"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(service_catalogue.router, prefix="/services", tags=["services"])
api_router.include_router(tax_rates.router, prefix="/tax-rates", tags=["tax-rates"])

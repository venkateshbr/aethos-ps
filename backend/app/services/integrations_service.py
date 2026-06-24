"""Integration catalog and roadmap metadata."""

from __future__ import annotations

from typing import Final

from app.models.integrations import IntegrationCatalogItem, IntegrationStatus

_INTEGRATION_CATALOG: Final[tuple[IntegrationCatalogItem, ...]] = (
    IntegrationCatalogItem(
        key="stripe-connect",
        category="payments",
        display_name="Stripe Connect",
        provider="Stripe",
        status="available",
        risk="high",
        auth_model="oauth",
        supported_markets=["US", "UK", "SG", "IN", "AU"],
        data_classes=["payments", "bank_payout_status", "client_pii"],
        capabilities=[
            "tenant_payment_onboarding",
            "client_payment_links",
            "payment_webhooks",
        ],
        notes="Live settings surface exists for tenant payment onboarding.",
    ),
    IntegrationCatalogItem(
        key="resend-transactional-email",
        category="email",
        display_name="Transactional Email",
        provider="Resend",
        status="available",
        risk="medium",
        auth_model="platform_api_key",
        supported_markets=["US", "UK", "SG", "IN", "AU"],
        data_classes=["client_pii", "invoice_metadata"],
        capabilities=["invoice_email", "collection_reminders", "system_notifications"],
        notes="Per-tenant DKIM/SPF is deferred; platform delivery is available.",
    ),
    IntegrationCatalogItem(
        key="google-microsoft-calendar-email",
        category="calendar_email",
        display_name="Calendar and Mailbox Sync",
        provider="Google Workspace / Microsoft 365",
        status="planned",
        risk="high",
        auth_model="oauth",
        supported_markets=["US", "UK", "SG", "IN", "AU"],
        data_classes=["email_body", "calendar_events", "contacts", "documents"],
        capabilities=[
            "time_entry_context",
            "engagement_intake",
            "vendor_invoice_intake",
        ],
        notes="Requires scoped OAuth consent, mailbox data minimization, and audit logging.",
    ),
    IntegrationCatalogItem(
        key="bank-feeds",
        category="banking",
        display_name="Bank Feeds",
        provider="Plaid / regional open-banking providers",
        status="planned",
        risk="high",
        auth_model="oauth",
        supported_markets=["US", "UK", "SG", "AU"],
        data_classes=["bank_transactions", "account_balances", "financial_pii"],
        capabilities=["cash_reconciliation", "payment_settlement", "close_evidence"],
        notes="India support needs a separate account-aggregator provider review.",
    ),
    IntegrationCatalogItem(
        key="government-registries-tax",
        category="government_tax",
        display_name="Government Registry and Tax Validation",
        provider="Companies House / HMRC / ACRA / GSTN / ASIC / ATO / IRS",
        status="research",
        risk="high",
        auth_model="mixed_api_key_oauth",
        supported_markets=["US", "UK", "SG", "IN", "AU"],
        data_classes=["tax_ids", "company_records", "filing_metadata"],
        capabilities=[
            "client_vendor_validation",
            "tax_registration_checks",
            "statutory_filing_context",
        ],
        notes="Provider mix differs materially by market and needs per-country contracts.",
    ),
    IntegrationCatalogItem(
        key="payroll",
        category="payroll",
        display_name="Payroll Systems",
        provider="Gusto / Xero Payroll / KeyPay / regional payroll providers",
        status="planned",
        risk="high",
        auth_model="oauth",
        supported_markets=["US", "UK", "SG", "IN", "AU"],
        data_classes=["employee_pii", "payroll_costs", "tax_withholding"],
        capabilities=["labor_cost_actuals", "utilization_margin", "payroll_accruals"],
        notes="Use for cost actuals first; payroll execution remains out of scope.",
    ),
    IntegrationCatalogItem(
        key="crm",
        category="crm",
        display_name="CRM Sync",
        provider="HubSpot / Salesforce",
        status="planned",
        risk="medium",
        auth_model="oauth",
        supported_markets=["US", "UK", "SG", "IN", "AU"],
        data_classes=["contacts", "opportunities", "client_pii"],
        capabilities=["client_import", "engagement_pipeline", "revenue_forecast"],
        notes="Initial scope should be account/contact/opportunity import.",
    ),
    IntegrationCatalogItem(
        key="document-storage",
        category="document_storage",
        display_name="Document Storage",
        provider="Google Drive / SharePoint / Dropbox",
        status="planned",
        risk="high",
        auth_model="oauth",
        supported_markets=["US", "UK", "SG", "IN", "AU"],
        data_classes=["documents", "contracts", "financial_pii"],
        capabilities=["source_document_sync", "close_evidence_storage", "audit_package_export"],
        notes="Must reuse document preflight scanning before agent processing.",
    ),
)


def list_integrations(
    *,
    category: str | None = None,
    status: IntegrationStatus | None = None,
) -> list[IntegrationCatalogItem]:
    """Return catalog items filtered by category and/or roadmap status."""
    normalized_category = category.strip().lower() if category else None
    items = list(_INTEGRATION_CATALOG)
    if normalized_category:
        items = [item for item in items if item.category == normalized_category]
    if status:
        items = [item for item in items if item.status == status]
    return [item.model_copy(deep=True) for item in items]

"""Pydantic request/response schemas for the Clients API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ContactKind = Literal["customer", "vendor", "both"]
VendorOnboardingStatus = Literal["not_required", "pending", "approved", "blocked"]
VendorBankAccountStatus = Literal["not_provided", "pending_verification", "verified", "failed"]
VendorTaxValidationStatus = Literal["not_checked", "valid", "warning", "failed"]
VendorSanctionsStatus = Literal["not_checked", "clear", "potential_match", "blocked"]
VendorRemittanceStatus = Literal["not_configured", "configured", "verified", "blocked"]


class ClientCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    kind: ContactKind = "customer"
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=80)
    website: str | None = Field(default=None, max_length=500)
    billing_address: dict | None = None
    tax_id: str | None = Field(default=None, max_length=100)
    payment_terms_days: int = Field(default=30, ge=0, le=365)
    vendor_onboarding_status: VendorOnboardingStatus | None = None
    vendor_bank_account_status: VendorBankAccountStatus = "not_provided"
    vendor_tax_validation_status: VendorTaxValidationStatus = "not_checked"
    vendor_sanctions_status: VendorSanctionsStatus = "not_checked"
    vendor_remittance_status: VendorRemittanceStatus = "not_configured"
    vendor_remittance_email: str | None = Field(default=None, max_length=254)
    vendor_payment_controls: dict[str, object] = Field(default_factory=dict)


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    kind: ContactKind | None = None
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=80)
    website: str | None = Field(default=None, max_length=500)
    billing_address: dict | None = None
    tax_id: str | None = Field(default=None, max_length=100)
    payment_terms_days: int | None = Field(default=None, ge=0, le=365)
    vendor_onboarding_status: VendorOnboardingStatus | None = None
    vendor_bank_account_status: VendorBankAccountStatus | None = None
    vendor_tax_validation_status: VendorTaxValidationStatus | None = None
    vendor_sanctions_status: VendorSanctionsStatus | None = None
    vendor_remittance_status: VendorRemittanceStatus | None = None
    vendor_remittance_email: str | None = Field(default=None, max_length=254)
    vendor_payment_controls: dict[str, object] | None = None


class ClientResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    kind: str
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    payment_terms_days: int
    created_at: str
    vendor_onboarding_status: VendorOnboardingStatus = "not_required"
    vendor_bank_account_status: VendorBankAccountStatus = "not_provided"
    vendor_tax_validation_status: VendorTaxValidationStatus = "not_checked"
    vendor_sanctions_status: VendorSanctionsStatus = "not_checked"
    vendor_remittance_status: VendorRemittanceStatus = "not_configured"
    vendor_remittance_email: str | None = None
    vendor_payment_controls: dict[str, object] = Field(default_factory=dict)
    vendor_onboarding_approved_at: str | None = None
    vendor_onboarding_approved_by: str | None = None


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    total: int

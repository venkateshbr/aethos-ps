"""Unit tests for the integration catalog service."""

from __future__ import annotations

import pytest

from app.services.integrations_service import list_integrations

pytestmark = pytest.mark.unit


def test_integration_catalog_includes_live_and_planned_surfaces() -> None:
    items = list_integrations()

    keys = {item.key for item in items}
    assert "stripe-connect" in keys
    assert "resend-transactional-email" in keys
    assert "bank-feeds" in keys
    assert "government-registries-tax" in keys
    assert "document-storage" in keys


def test_integration_catalog_filters_by_status() -> None:
    planned = list_integrations(status="planned")

    assert planned
    assert {item.status for item in planned} == {"planned"}
    assert {item.key for item in planned} >= {"bank-feeds", "payroll", "crm"}


def test_integration_catalog_filters_by_category_case_insensitive() -> None:
    banking = list_integrations(category=" Banking ")

    assert [item.key for item in banking] == ["bank-feeds"]
    assert banking[0].risk == "high"
    assert "cash_reconciliation" in banking[0].capabilities


def test_integration_catalog_returns_defensive_copies() -> None:
    items = list_integrations(category="document_storage")
    assert len(items) == 1
    items[0].capabilities.clear()

    fresh_items = list_integrations(category="document_storage")
    assert fresh_items[0].capabilities == [
        "source_document_sync",
        "close_evidence_storage",
        "audit_package_export",
    ]

"""Executable authz matrix (#378 AC 7).

A CI-runnable contract over the *sensitive* handlers — money-out, accounting, and
admin/destructive actions. It introspects each handler's role/privilege gate
(from the require_role/require_privilege metadata) and asserts it matches the
expected authority, so an accidental gate downgrade or removal fails the build
without needing the live stack.
"""

from __future__ import annotations

import importlib
import inspect

import pytest

pytestmark = pytest.mark.unit


def _gate(fn) -> tuple[str, str] | None:
    for param in inspect.signature(fn).parameters.values():
        dep = getattr(param.default, "dependency", None)
        role = getattr(dep, "aethos_min_role", None)
        if role is not None:
            return ("role", role.value)
        priv = getattr(dep, "aethos_privilege", None)
        if priv is not None:
            return ("privilege", priv)
    return None


# (module, handler) -> expected gate. Curated to the highest-risk surfaces.
EXPECTED_AUTHZ: dict[tuple[str, str], tuple[str, str]] = {
    # Money-out — billing runs / bill payments
    ("billing_runs", "create_billing_run"): ("role", "manager"),
    ("billing_runs", "approve_billing_run"): ("role", "owner"),
    ("bill_payments", "propose"): ("privilege", "bill_payments.prepare"),
    # AR money movement — invoices
    ("invoices", "approve_invoice"): ("privilege", "invoices.post"),
    ("invoices", "send_invoice"): ("privilege", "invoices.send"),
    ("invoices", "record_manual_payment"): ("privilege", "invoices.mark_paid"),
    ("invoices", "create_invoice"): ("privilege", "invoices.draft"),
    # Accounting integrity — close / journals
    ("accounting", "lock_period"): ("role", "admin"),
    ("accounting", "unlock_period"): ("role", "owner"),
    ("accounting", "post_year_end_close"): ("role", "admin"),
    ("accounting", "create_close_override"): ("role", "admin"),
    ("accounting", "reverse_manual_journal"): ("role", "manager"),
    # Config / admin / destructive
    ("tax_rates", "create_tax_rate"): ("role", "admin"),
    ("tax_rates", "update_tax_rate"): ("role", "admin"),
    ("rate_cards", "create_rate_card"): ("role", "admin"),
    ("tenants", "tenant_health"): ("role", "admin"),
    ("tenants", "delete_tenant"): ("role", "owner"),
}


@pytest.mark.parametrize(
    ("location", "expected"),
    list(EXPECTED_AUTHZ.items()),
    ids=[f"{m}.{h}" for (m, h) in EXPECTED_AUTHZ],
)
def test_sensitive_handler_authz(location: tuple[str, str], expected: tuple[str, str]) -> None:
    module_name, handler_name = location
    module = importlib.import_module(f"app.api.v1.endpoints.{module_name}")
    handler = getattr(module, handler_name, None)
    assert handler is not None, f"{module_name}.{handler_name} no longer exists"
    actual = _gate(handler)
    assert actual is not None, f"{module_name}.{handler_name} is NOT authz-gated"
    assert actual == expected, (
        f"{module_name}.{handler_name} authz drifted: expected {expected}, got {actual}"
    )

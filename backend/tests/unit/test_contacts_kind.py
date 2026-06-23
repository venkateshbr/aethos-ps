"""Unit tests for the 'both' kind on the contacts (clients) resource.

Coverage:
  - ClientCreate / ClientUpdate accept kind='both'
  - ClientRepository.list() with kind='customer' returns CUSTOMER_KINDS
  - ClientRepository.list() with kind='vendor' returns VENDOR_KINDS
  - CUSTOMER_KINDS and VENDOR_KINDS constants are correct
  - list() with kind='both' falls through to exact-match branch
  - list() with no kind returns all contacts

All tests are pure-Python — no I/O, no DB, no HTTP.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.models.clients import ClientCreate, ClientUpdate
from app.repositories.clients_repo import CUSTOMER_KINDS, VENDOR_KINDS, ClientRepository

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_customer_kinds_contains_both() -> None:
    assert "both" in CUSTOMER_KINDS
    assert "customer" in CUSTOMER_KINDS


def test_vendor_kinds_contains_both() -> None:
    assert "both" in VENDOR_KINDS
    assert "vendor" in VENDOR_KINDS


def test_customer_kinds_does_not_contain_vendor() -> None:
    assert "vendor" not in CUSTOMER_KINDS


def test_vendor_kinds_does_not_contain_customer() -> None:
    assert "customer" not in VENDOR_KINDS


# ---------------------------------------------------------------------------
# Model validation
# ---------------------------------------------------------------------------


def test_create_contact_kind_both() -> None:
    """ClientCreate must accept kind='both'."""
    c = ClientCreate(name="Acme Consulting", kind="both")
    assert c.kind == "both"


def test_create_contact_kind_customer() -> None:
    c = ClientCreate(name="Retail Corp", kind="customer")
    assert c.kind == "customer"


def test_create_contact_kind_vendor() -> None:
    c = ClientCreate(name="Supplier Ltd", kind="vendor")
    assert c.kind == "vendor"


def test_create_contact_rejects_invalid_kind() -> None:
    with pytest.raises(ValidationError):
        ClientCreate(name="Bad", kind="unknown")  # type: ignore[arg-type]


def test_update_contact_kind_both() -> None:
    u = ClientUpdate(kind="both")
    assert u.kind == "both"


# ---------------------------------------------------------------------------
# Repository list() — kind filter expansion
# ---------------------------------------------------------------------------


def _make_repo_with_rows(rows: list[dict]) -> tuple[ClientRepository, MagicMock]:
    """Return a ClientRepository wired to a Supabase mock that returns *rows*."""
    mock_result = MagicMock()
    mock_result.data = rows

    # Chain: db.table().select().eq().eq().is_().in_().execute() → mock_result
    # We build a single MagicMock that returns itself on every chained call.
    chain = MagicMock()
    chain.execute.return_value = mock_result
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.is_.return_value = chain
    chain.in_.return_value = chain
    chain.ilike.return_value = chain

    mock_db = MagicMock()
    mock_db.table.return_value = chain

    repo = ClientRepository(db=mock_db, tenant_id="tenant-123")
    return repo, chain


def test_kind_both_appears_in_customer_list() -> None:
    """A contact with kind='both' must be returned when filtering kind='customer'."""
    rows = [
        {"id": "c1", "kind": "customer", "name": "Retail Corp", "tenant_id": "tenant-123",
         "payment_terms_days": 30, "created_at": "2026-01-01T00:00:00"},
        {"id": "c2", "kind": "both", "name": "Acme Consulting", "tenant_id": "tenant-123",
         "payment_terms_days": 30, "created_at": "2026-01-01T00:00:00"},
    ]
    repo, chain = _make_repo_with_rows(rows)

    result = asyncio.run(repo.list(kind="customer"))

    # Verify in_ was called with the expanded CUSTOMER_KINDS list
    chain.in_.assert_called_once_with("kind", list(CUSTOMER_KINDS))
    assert len(result) == 2


def test_kind_both_appears_in_vendor_list() -> None:
    """A contact with kind='both' must be returned when filtering kind='vendor'."""
    rows = [
        {"id": "v1", "kind": "vendor", "name": "Supplier Ltd", "tenant_id": "tenant-123",
         "payment_terms_days": 30, "created_at": "2026-01-01T00:00:00"},
        {"id": "c2", "kind": "both", "name": "Acme Consulting", "tenant_id": "tenant-123",
         "payment_terms_days": 30, "created_at": "2026-01-01T00:00:00"},
    ]
    repo, chain = _make_repo_with_rows(rows)

    result = asyncio.run(repo.list(kind="vendor"))

    chain.in_.assert_called_once_with("kind", list(VENDOR_KINDS))
    assert len(result) == 2


def test_list_kind_both_uses_exact_match() -> None:
    """Filtering by kind='both' should use eq (exact match), not in_."""
    rows = [
        {"id": "c2", "kind": "both", "name": "Acme Consulting", "tenant_id": "tenant-123",
         "payment_terms_days": 30, "created_at": "2026-01-01T00:00:00"},
    ]
    repo, chain = _make_repo_with_rows(rows)

    result = asyncio.run(repo.list(kind="both"))

    # in_ must NOT be called — eq is used for 'both'
    chain.in_.assert_not_called()
    assert len(result) == 1


def test_list_no_kind_returns_all() -> None:
    """list() with no kind filter returns all contacts regardless of kind."""
    rows = [
        {"id": "c1", "kind": "customer", "name": "A", "tenant_id": "tenant-123",
         "payment_terms_days": 30, "created_at": "2026-01-01T00:00:00"},
        {"id": "v1", "kind": "vendor", "name": "B", "tenant_id": "tenant-123",
         "payment_terms_days": 30, "created_at": "2026-01-01T00:00:00"},
        {"id": "b1", "kind": "both", "name": "C", "tenant_id": "tenant-123",
         "payment_terms_days": 30, "created_at": "2026-01-01T00:00:00"},
    ]
    repo, chain = _make_repo_with_rows(rows)

    result = asyncio.run(repo.list())

    chain.in_.assert_not_called()
    # eq is still called for tenant_id and is_ for deleted_at — but NOT for kind
    # We verify by checking all eq calls don't include "kind"
    eq_calls = [str(c) for c in chain.eq.call_args_list]
    assert not any("kind" in c for c in eq_calls)
    assert len(result) == 3

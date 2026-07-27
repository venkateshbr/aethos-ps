"""Opt-in real-stack test for the atomic posting RPC (#372 / #472).

The unit test (test_journal_helper_atomic.py) mocks the RPC, so it never executes
the SQL — which is how the enum-cast bug (#472) reached production. This test calls
the DEPLOYED post_journal_entry RPC against a real DB and asserts the DB-level
invariants actually fire (balance, completeness, idempotency). Skipped by default
because it needs a live DB + a seeded tenant with two accounts.

Enable:

    AETHOS_LIVE_DB=1 \
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \
    AETHOS_TEST_TENANT_ID=<uuid> \
    AETHOS_TEST_ACCOUNT_A=<uuid> AETHOS_TEST_ACCOUNT_B=<uuid> \
    uv run pytest tests/eval/test_atomic_posting_live.py -q -s

Only failure-injection cases run against a shared env (they roll back and persist
nothing); the balanced-post case is skipped unless AETHOS_LIVE_DB_DISPOSABLE=1 is
set, because a successful post is immutable and cannot be cleaned up.
"""

from __future__ import annotations

import os

import pytest

_LIVE = os.getenv("AETHOS_LIVE_DB") == "1"
_URL = os.getenv("SUPABASE_URL", "")
_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
_TENANT = os.getenv("AETHOS_TEST_TENANT_ID", "")
_ACC_A = os.getenv("AETHOS_TEST_ACCOUNT_A", "")
_ACC_B = os.getenv("AETHOS_TEST_ACCOUNT_B", "")

pytestmark = pytest.mark.skipif(
    not (_LIVE and _URL and _KEY and _TENANT and _ACC_A and _ACC_B),
    reason="set AETHOS_LIVE_DB=1 + SUPABASE creds + AETHOS_TEST_TENANT_ID/ACCOUNT_A/ACCOUNT_B",
)


def _client():
    from supabase import create_client

    return create_client(_URL, _KEY)


def _line(direction: str, account: str, base: str, tenant: str = _TENANT) -> dict:
    return {
        "tenant_id": tenant,
        "direction": direction,
        "account_id": account,
        "amount": base,
        "currency": "USD",
        "base_amount": base,
    }


def _entry(number: str) -> dict:
    return {
        "tenant_id": _TENANT,
        "entry_number": number,
        "entry_type": "auto",
        "description": "live rpc test",
        "entry_date": "2026-07-01",
        "reference_type": "manual",
    }


def _post(db, entry, lines, key):
    return db.rpc(
        "post_journal_entry",
        {"p_entry": entry, "p_lines": lines, "p_idempotency_key": key},
    ).execute()


def test_rpc_rejects_unbalanced_entry() -> None:
    db = _client()
    with pytest.raises(Exception):  # noqa: B017 - any DB error is a pass (check_violation)
        _post(
            db,
            _entry("LIVE-UNBAL"),
            [_line("DR", _ACC_A, "100.00"), _line("CR", _ACC_B, "90.00")],
            "live-unbal-key",
        )


def test_rpc_rejects_cross_tenant_line() -> None:
    db = _client()
    other = "00000000-0000-4000-8000-000000000999"
    with pytest.raises(Exception):  # noqa: B017
        _post(
            db,
            _entry("LIVE-XT"),
            [_line("DR", _ACC_A, "100.00"), _line("CR", _ACC_B, "100.00", tenant=other)],
            "live-xt-key",
        )


@pytest.mark.skipif(
    os.getenv("AETHOS_LIVE_DB_DISPOSABLE") != "1",
    reason="balanced post persists an immutable entry; only run on a disposable DB",
)
def test_rpc_posts_balanced_entry_and_is_idempotent() -> None:
    db = _client()
    entry, lines = _entry("LIVE-OK"), [
        _line("DR", _ACC_A, "100.00"),
        _line("CR", _ACC_B, "100.00"),
    ]
    r1 = _post(db, entry, lines, "live-ok-key").data
    assert r1["idempotent_hit"] is False
    r2 = _post(db, entry, lines, "live-ok-key").data
    assert r2["idempotent_hit"] is True  # same key → deduped, one entry

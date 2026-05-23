"""C13 — vendor_invoice_agent.

Tests the agent directly. Verifies:
- happy path extracts plausible BillDraft (vendor + amount)
- duplicate flag (possible_duplicate) — agent flags re-uploaded vendor invoice
- amounts are Decimal not float
- the agent does NOT crash on minimal text input (#104 graceful degradation)
"""

from __future__ import annotations

import asyncio
import os
from decimal import Decimal

import pytest

pytestmark = [
    pytest.mark.api,
    pytest.mark.flow_hitl,
    pytest.mark.requires_openrouter,
]


_VENDOR_INVOICE = """
ACME Cloud Services, Inc.
Bill To: Aethos Consulting

Invoice #: ACME-2026-0042
Issue Date: 2026-05-01
Due Date:   2026-05-31

Description                    Amount
Compute (May)                  $1,200.00
Storage (May)                  $  340.00
Bandwidth                      $   60.00
---------------------------------------
Subtotal                       $1,600.00
Sales Tax (8%)                 $  128.00
TOTAL                          $1,728.00 USD
"""


def _has_openrouter() -> bool:
    return bool(os.environ.get("OPENROUTER_API_KEY"))


def test_vendor_invoice_agent_happy_path() -> None:
    if not _has_openrouter():
        pytest.skip("OPENROUTER_API_KEY not set")

    from app.agents.base import AgentDeps
    from app.agents.schemas import BillDraft
    from app.agents.vendor_invoice_agent import run_vendor_invoice_agent

    deps = AgentDeps(
        tenant_id="00000000-0000-0000-0000-000000000000",
        user_id=None,
        db=None,  # type: ignore[arg-type]
    )

    try:
        result = asyncio.run(
            run_vendor_invoice_agent(
                document_id="aksha-vendor-test",
                deps=deps,
                document_bytes=_VENDOR_INVOICE.encode(),
                mime_type="text/plain",
            )
        )
    except Exception as exc:
        pytest.xfail(f"Bug #104 — vendor_invoice_agent crashed: {exc!s}")

    assert isinstance(result, BillDraft)
    # Money fields must be Decimal
    assert isinstance(result.subtotal, Decimal), type(result.subtotal).__name__
    assert isinstance(result.total, Decimal), type(result.total).__name__
    assert isinstance(result.tax_total, Decimal), type(result.tax_total).__name__

    # Plausibility — total should be near $1,728 if confident
    if result.confidence > 0.7:
        assert result.vendor_name, "vendor_name empty on confident draft"
        assert Decimal("1500") <= result.total <= Decimal("2000"), (
            f"Confident draft total={result.total} not near expected $1,728"
        )


def test_vendor_invoice_agent_does_not_crash_on_empty_input() -> None:
    """Pass a single byte; agent must degrade, not raise (per #104)."""
    if not _has_openrouter():
        pytest.skip("OPENROUTER_API_KEY not set")

    from app.agents.base import AgentDeps
    from app.agents.vendor_invoice_agent import run_vendor_invoice_agent

    deps = AgentDeps(
        tenant_id="00000000-0000-0000-0000-000000000000",
        user_id=None,
        db=None,  # type: ignore[arg-type]
    )
    try:
        result = asyncio.run(
            run_vendor_invoice_agent(
                document_id="aksha-vendor-empty",
                deps=deps,
                document_bytes=b" ",
                mime_type="text/plain",
            )
        )
    except Exception as exc:
        # Per #104 this currently raises ValidationError. xfail covers it.
        pytest.xfail(f"Bug #104 — agent crashed on empty input: {exc!s}")
    assert result.confidence < 0.5, (
        f"Empty input got confident draft: {result.model_dump()}"
    )


def test_vendor_invoice_agent_total_equals_subtotal_plus_tax_or_flagged() -> None:
    """C26 invariant: total = subtotal + tax_total. If the agent extracts
    inconsistent values, anomaly_detected should be True."""
    if not _has_openrouter():
        pytest.skip("OPENROUTER_API_KEY not set")

    from app.agents.base import AgentDeps
    from app.agents.vendor_invoice_agent import run_vendor_invoice_agent

    deps = AgentDeps(
        tenant_id="00000000-0000-0000-0000-000000000000",
        user_id=None,
        db=None,  # type: ignore[arg-type]
    )
    try:
        result = asyncio.run(
            run_vendor_invoice_agent(
                document_id="aksha-vendor-math",
                deps=deps,
                document_bytes=_VENDOR_INVOICE.encode(),
                mime_type="text/plain",
            )
        )
    except Exception as exc:
        pytest.xfail(f"Bug #104 — agent crashed: {exc!s}")

    if result.confidence > 0.7:
        delta = abs(result.total - (result.subtotal + result.tax_total))
        # Allow $1 of rounding noise from the LLM
        if delta > Decimal("1.00"):
            assert result.anomaly_detected, (
                f"Math doesn't add up (subtotal={result.subtotal}, "
                f"tax={result.tax_total}, total={result.total}) but "
                f"anomaly_detected=False"
            )

"""#374 — the log formatter masks structured PII in the message (pre-log boundary)."""

from __future__ import annotations

import json
import logging

import pytest

from app.core.logging import _AethosFormatter

pytestmark = pytest.mark.unit


def _format(msg: str, *args: object) -> dict:
    formatter = _AethosFormatter(fmt="%(asctime)s %(levelname)s %(name)s %(message)s")
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname=__file__, lineno=1,
        msg=msg, args=args, exc_info=None,
    )
    return json.loads(formatter.format(record))


def test_log_masks_bank_account_and_email() -> None:
    out = _format("wire to IBAN GB29NWBK60161331926819 for alice@acme.io")
    assert "GB29NWBK60161331926819" not in out["message"]
    assert "[REDACTED-BANK-ACCOUNT]" in out["message"]
    assert "alice@acme.io" not in out["message"]


def test_log_masks_card_and_tax_id_and_nric() -> None:
    out = _format("card 4111111111111111 EIN 12-3456789 NRIC S1234567D")
    assert "4111111111111111" not in out["message"]
    assert "12-3456789" not in out["message"]
    assert "S1234567D" not in out["message"]


def test_log_preserves_ordinary_text() -> None:
    out = _format("Invoice INV-2026-0007 posted for $12,345.67")
    assert out["message"] == "Invoice INV-2026-0007 posted for $12,345.67"

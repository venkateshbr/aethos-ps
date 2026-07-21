"""Schema contract for frozen document-level FX provenance."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_document_fx_migration_is_idempotent_and_backward_compatible() -> None:
    migration = (
        Path(__file__).parents[2]
        / "supabase/migrations/0102_document_approval_fx_provenance.sql"
    )
    sql = migration.read_text().lower()

    assert sql.startswith("--")
    assert "begin;" in sql and "commit;" in sql
    for table in ("invoices", "bills"):
        section = sql.split(f"alter table {table}", maxsplit=1)[1]
        for column in (
            "base_currency",
            "base_subtotal",
            "base_tax_total",
            "base_total",
            "approval_fx_rate_id",
        ):
            assert f"add column if not exists {column}" in section

    assert sql.count("references fx_rates(id)") >= 2
    assert "and upper(i.currency) = upper(t.base_currency)" in sql
    assert "and upper(b.currency) = upper(t.base_currency)" in sql
    assert "drop column" not in sql

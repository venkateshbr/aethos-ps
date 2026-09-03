"""#492 — every RLS policy must target a table some migration creates.

`billing_runs` was referenced by migration 0054's `CREATE POLICY` but no
migration ever created it, so a database built from this directory aborted at
0054 and migrations 0054-0121 never applied. This contract test fails the build
if that class of gap reappears.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

MIGRATIONS = Path(__file__).resolve().parents[2] / "supabase" / "migrations"

_CREATE_TABLE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:public\.)?\"?([a-z0-9_]+)\"?",
    re.IGNORECASE,
)
# Capture an optional schema so `storage.objects` resolves to `objects` rather
# than to the schema name.
_POLICY_ON = re.compile(
    r"CREATE\s+POLICY\s+(?:\"[^\"]+\"|[^\s]+)\s+ON\s+(?:\"?([a-z0-9_]+)\"?\.)?\"?([a-z0-9_]+)\"?",
    re.IGNORECASE,
)
_ALTER_RLS = re.compile(
    r"ALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:\"?([a-z0-9_]+)\"?\.)?\"?([a-z0-9_]+)\"?\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY",
    re.IGNORECASE,
)

# Schemas Supabase manages for us; their tables are not created here.
_EXTERNAL_SCHEMAS = {"storage", "auth", "extensions", "graphql", "realtime"}


def _sql_files() -> list[Path]:
    files = sorted(MIGRATIONS.glob("*.sql"))
    assert files, f"no migrations found under {MIGRATIONS}"
    return files


def _created_tables() -> set[str]:
    created: set[str] = set()
    for path in _sql_files():
        created.update(name.lower() for name in _CREATE_TABLE.findall(path.read_text()))
    return created


def _targets(pattern: re.Pattern[str], sql: str) -> list[str]:
    """Yield `table` for each match, skipping Supabase-managed schemas.

    Statements built with `format()` placeholders (`CREATE POLICY %I ON
    public.%I` inside a DO block) name their table at runtime from a loop over
    existing relations, so there is nothing static to verify — drop those lines.
    """
    sql = "\n".join(line for line in sql.splitlines() if "%I" not in line)
    out: list[str] = []
    for schema, table in pattern.findall(sql):
        if schema and schema.lower() in _EXTERNAL_SCHEMAS:
            continue
        out.append(table.lower())
    return out


def test_every_policy_targets_a_created_table() -> None:
    created = _created_tables()
    missing: list[str] = []
    for path in _sql_files():
        for table in _targets(_POLICY_ON, path.read_text()):
            if table not in created:
                missing.append(f"{path.name}: CREATE POLICY ... ON {table}")
    assert not missing, (
        "policies reference tables that no migration creates — a fresh "
        "`supabase db reset` will abort:\n  " + "\n  ".join(missing)
    )


def test_every_rls_enable_targets_a_created_table() -> None:
    created = _created_tables()
    missing: list[str] = []
    for path in _sql_files():
        for table in _targets(_ALTER_RLS, path.read_text()):
            if table not in created:
                missing.append(f"{path.name}: ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    assert not missing, "RLS enabled on tables no migration creates:\n  " + "\n  ".join(missing)


def test_billing_runs_is_created_before_use() -> None:
    """The specific regression: the table exists and carries tenant isolation."""
    created = _created_tables()
    assert "billing_runs" in created, "billing_runs must have a CREATE TABLE migration (#492)"

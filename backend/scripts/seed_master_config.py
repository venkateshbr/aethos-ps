"""Repair platform master/config data after an accidental reset.

Dry-run by default:

    uv run python -m scripts.seed_master_config

Execute:

    uv run python -m scripts.seed_master_config --execute

This script intentionally does not create tenants or tenant-scoped data. It
only repairs global platform data required before any tenant signs up:

- Supabase Storage ``documents`` bucket and its RLS policies;
- global FX seed rates;
- system tax rates where ``tenant_id IS NULL``;
- enterprise RBAC roles, duties, and privileges.
"""

from __future__ import annotations

import argparse
import os
from decimal import Decimal
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from app.core.config import settings

REPO_BACKEND = Path(__file__).resolve().parents[1]

FX_RATES = [
    ("USD", "GBP", Decimal("0.789500"), "seed", "2026-05-19"),
    ("GBP", "USD", Decimal("1.266600"), "seed", "2026-05-19"),
    ("USD", "SGD", Decimal("1.348500"), "seed", "2026-05-19"),
    ("SGD", "USD", Decimal("0.741600"), "seed", "2026-05-19"),
    ("USD", "INR", Decimal("83.521000"), "seed", "2026-05-19"),
    ("INR", "USD", Decimal("0.011972"), "seed", "2026-05-19"),
    ("USD", "AUD", Decimal("1.551200"), "seed", "2026-05-19"),
    ("AUD", "USD", Decimal("0.644700"), "seed", "2026-05-19"),
    ("GBP", "SGD", Decimal("1.708800"), "seed", "2026-05-19"),
    ("SGD", "GBP", Decimal("0.585200"), "seed", "2026-05-19"),
    ("GBP", "INR", Decimal("105.800000"), "seed", "2026-05-19"),
    ("INR", "GBP", Decimal("0.009452"), "seed", "2026-05-19"),
    ("GBP", "AUD", Decimal("1.965100"), "seed", "2026-05-19"),
    ("AUD", "GBP", Decimal("0.508900"), "seed", "2026-05-19"),
    ("SGD", "INR", Decimal("61.929000"), "seed", "2026-05-19"),
    ("INR", "SGD", Decimal("0.016148"), "seed", "2026-05-19"),
    ("SGD", "AUD", Decimal("1.150100"), "seed", "2026-05-19"),
    ("AUD", "SGD", Decimal("0.869500"), "seed", "2026-05-19"),
    ("INR", "AUD", Decimal("0.018577"), "seed", "2026-05-19"),
    ("AUD", "INR", Decimal("53.836000"), "seed", "2026-05-19"),
]

SYSTEM_TAX_RATES = [
    ("GB", "VAT-20", "UK VAT Standard Rate (20%)", Decimal("0.2000"), True),
    ("GB", "VAT-5", "UK VAT Reduced Rate (5%)", Decimal("0.0500"), False),
    ("GB", "VAT-0", "UK VAT Zero Rate (0%)", Decimal("0.0000"), False),
    ("SG", "GST-9", "Singapore GST (9%)", Decimal("0.0900"), True),
    ("SG", "GST-0", "Singapore GST Zero-Rated (0%)", Decimal("0.0000"), False),
    ("AU", "GST-AU-10", "Australia GST (10%)", Decimal("0.1000"), True),
    ("AU", "GST-AU-0", "Australia GST Exports (0%)", Decimal("0.0000"), False),
    ("IN", "GST-IN-0", "India GST 0%", Decimal("0.0000"), False),
    ("IN", "GST-IN-5", "India GST 5%", Decimal("0.0500"), False),
    ("IN", "GST-IN-12", "India GST 12%", Decimal("0.1200"), False),
    ("IN", "GST-IN-18", "India GST 18%", Decimal("0.1800"), True),
    ("IN", "GST-IN-28", "India GST 28%", Decimal("0.2800"), False),
    ("US", "US-EXEMPT", "US Tax Exempt / No Tax", Decimal("0.0000"), False),
]


def main() -> None:
    args = _parse_args()
    database_url = args.database_url or os.environ.get("DATABASE_URL") or settings.database_url
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    mode = "EXECUTE" if args.execute else "DRY RUN"
    print(f"Aethos master/config seed ({mode})")
    with psycopg.connect(database_url, row_factory=dict_row, autocommit=True) as conn:
        before = _counts(conn)
        _print_counts("Before", before)

        if args.execute:
            _ensure_storage_bucket_and_policies(conn)
            _ensure_security_catalog(conn)
            _ensure_fx_rates(conn)
            _ensure_system_tax_rates(conn)
            after = _counts(conn)
            _print_counts("After", after)
            print("Master/config seed complete.")
        else:
            missing_fx = _missing_fx_rates(conn)
            missing_tax = _missing_tax_rates(conn)
            missing_security = _missing_security_catalog(conn)
            print(f"Missing FX seed rows: {len(missing_fx)}")
            print(f"Missing system tax seed rows: {len(missing_tax)}")
            print(f"Missing security catalog groups: {len(missing_security)}")
            print("Dry run complete. Re-run with --execute to repair missing rows.")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default="", help="Override DATABASE_URL.")
    parser.add_argument("--execute", action="store_true", help="Repair master/config data.")
    return parser.parse_args()


def _ensure_storage_bucket_and_policies(conn: psycopg.Connection) -> None:
    for migration in [
        REPO_BACKEND / "supabase" / "migrations" / "0016_storage_documents_bucket.sql",
        REPO_BACKEND / "supabase" / "migrations" / "0017_storage_documents_rls_helper.sql",
    ]:
        conn.execute(migration.read_text())


def _ensure_security_catalog(conn: psycopg.Connection) -> None:
    conn.execute(
        (REPO_BACKEND / "supabase" / "migrations" / "0096_dynamics_style_security_catalog.sql").read_text()
    )


def _ensure_fx_rates(conn: psycopg.Connection) -> None:
    conn.executemany(
        """
        INSERT INTO public.fx_rates (from_currency, to_currency, rate, source, rate_date)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (from_currency, to_currency, rate_date) DO UPDATE
            SET rate = EXCLUDED.rate,
                source = EXCLUDED.source
        """,
        FX_RATES,
    )


def _ensure_system_tax_rates(conn: psycopg.Connection) -> None:
    for country, code, name, rate, is_default in SYSTEM_TAX_RATES:
        existing = conn.execute(
            """
            SELECT id
              FROM public.tax_rates
             WHERE tenant_id IS NULL
               AND country = %s
               AND code = %s
               AND deleted_at IS NULL
             ORDER BY created_at
             LIMIT 1
            """,
            (country, code),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE public.tax_rates
                   SET name = %s,
                       rate = %s,
                       is_default = %s,
                       is_active = TRUE,
                       is_seeded = TRUE
                 WHERE id = %s
                """,
                (name, rate, is_default, existing["id"]),
            )
        else:
            conn.execute(
                """
                INSERT INTO public.tax_rates (
                    tenant_id, country, code, name, rate,
                    is_default, is_active, is_seeded
                )
                VALUES (NULL, %s, %s, %s, %s, %s, TRUE, TRUE)
                """,
                (country, code, name, rate, is_default),
            )


def _missing_fx_rates(conn: psycopg.Connection) -> list[tuple[str, str, str]]:
    missing = []
    for from_currency, to_currency, _rate, _source, rate_date in FX_RATES:
        row = conn.execute(
            """
            SELECT 1
              FROM public.fx_rates
             WHERE from_currency = %s
               AND to_currency = %s
               AND rate_date = %s
            """,
            (from_currency, to_currency, rate_date),
        ).fetchone()
        if not row:
            missing.append((from_currency, to_currency, rate_date))
    return missing


def _missing_tax_rates(conn: psycopg.Connection) -> list[tuple[str, str]]:
    missing = []
    for country, code, _name, _rate, _is_default in SYSTEM_TAX_RATES:
        row = conn.execute(
            """
            SELECT 1
              FROM public.tax_rates
             WHERE tenant_id IS NULL
               AND country = %s
               AND code = %s
               AND deleted_at IS NULL
            """,
            (country, code),
        ).fetchone()
        if not row:
            missing.append((country, code))
    return missing


def _missing_security_catalog(conn: psycopg.Connection) -> list[str]:
    checks = {
        "security_privileges": "SELECT count(*) AS count FROM public.security_privileges",
        "security_duties": "SELECT count(*) AS count FROM public.security_duties",
        "security_roles": (
            "SELECT count(*) AS count FROM public.security_roles "
            "WHERE tenant_id IS NULL AND deleted_at IS NULL"
        ),
    }
    missing: list[str] = []
    for label, query in checks.items():
        try:
            count = int(conn.execute(query).fetchone()["count"])
        except Exception:
            count = 0
        if count == 0:
            missing.append(label)
    return missing


def _counts(conn: psycopg.Connection) -> dict[str, int]:
    queries = {
        "fx_rates": "SELECT count(*) AS count FROM public.fx_rates",
        "system_tax_rates": (
            "SELECT count(*) AS count FROM public.tax_rates "
            "WHERE tenant_id IS NULL AND deleted_at IS NULL"
        ),
        "document_buckets": (
            "SELECT count(*) AS count FROM storage.buckets WHERE id = 'documents'"
        ),
        "document_objects": (
            "SELECT count(*) AS count FROM storage.objects WHERE bucket_id = 'documents'"
        ),
        "security_privileges": (
            "SELECT count(*) AS count FROM public.security_privileges"
        ),
        "security_roles": (
            "SELECT count(*) AS count FROM public.security_roles "
            "WHERE tenant_id IS NULL AND deleted_at IS NULL"
        ),
    }
    counts: dict[str, int] = {}
    for label, query in queries.items():
        try:
            counts[label] = int(conn.execute(query).fetchone()["count"])
        except Exception:
            counts[label] = 0
    return counts


def _print_counts(label: str, counts: dict[str, int]) -> None:
    print(f"{label}:")
    for key, value in counts.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()

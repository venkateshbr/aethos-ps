#!/usr/bin/env python3
"""Opt-in deploy-time migration applier (runs on the VPS, where the DB is reachable).

Applies ONLY the migration files named in the ``APPLY_MIGRATIONS`` env var
(comma-separated filenames under ``supabase/migrations/``). It never auto-applies
the full history, so it cannot double-apply non-idempotent historical migrations.
List a migration here only when its SQL is idempotent (``IF NOT EXISTS`` etc.).

Used by the one-shot ``migrate`` service in docker-compose.hostinger.yml. Local
dev applies migrations the usual way; this exists because the Hostinger deploy has
DB egress that the developer's machine may not.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

MIG_DIR = Path(__file__).resolve().parents[1] / "supabase" / "migrations"


def main() -> int:
    names = [n.strip() for n in os.environ.get("APPLY_MIGRATIONS", "").split(",") if n.strip()]
    if not names:
        print("apply_migrations: APPLY_MIGRATIONS empty — nothing to do", flush=True)
        return 0

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("apply_migrations: DATABASE_URL not set", file=sys.stderr, flush=True)
        return 1

    import psycopg

    with psycopg.connect(database_url, autocommit=True, connect_timeout=30) as conn:
        for name in names:
            path = MIG_DIR / name
            if not path.is_file():
                print(f"apply_migrations: {name} not found under {MIG_DIR}", file=sys.stderr, flush=True)
                return 1
            sql = path.read_text()
            print(f"apply_migrations: applying {name} ...", flush=True)
            with conn.cursor() as cur:
                cur.execute(sql)
            print(f"apply_migrations: applied {name}", flush=True)

    print("apply_migrations: done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

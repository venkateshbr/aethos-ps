"""Reset tenant operational data while preserving platform reference data.

Dry-run by default:

    uv run python -m scripts.reset_operational_data

Execute:

    uv run python -m scripts.reset_operational_data \
        --execute --confirm DELETE_ALL_TENANTS

By default execution also deletes Supabase Auth users through the Admin API.
Use ``--no-include-auth-users`` to leave Auth identities in place.
"""

from __future__ import annotations

import argparse
import os
from collections import defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from app.core.config import settings
from supabase import create_client

CONFIRM_TOKEN = "DELETE_ALL_TENANTS"
PROTECTED_PUBLIC_TABLES = {
    "_prisma_migrations",
    "fx_rates",
    "schema_migrations",
}
PROTECTED_PUBLIC_PREFIXES = ("procrastinate_",)


@dataclass(frozen=True, order=True)
class TableRef:
    schema: str
    name: str

    @property
    def label(self) -> str:
        return f"{self.schema}.{self.name}"


GLOBAL_OPERATIONAL_TABLES = {
    TableRef("public", "procrastinate_events"),
    TableRef("public", "procrastinate_jobs"),
    TableRef("public", "procrastinate_periodic_defers"),
    TableRef("public", "rate_limit_events"),
    TableRef("public", "webhook_events"),
}


@dataclass(frozen=True)
class ForeignKeyRef:
    child: TableRef
    parent: TableRef


def main() -> None:
    args = _parse_args()
    if args.execute and args.confirm != CONFIRM_TOKEN:
        raise SystemExit(f"Refusing reset: pass --confirm {CONFIRM_TOKEN}")

    database_url = args.database_url or os.environ.get("DATABASE_URL") or settings.database_url
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    mode = "EXECUTE" if args.execute else "DRY RUN"
    print(f"Aethos operational data reset ({mode})")

    auth_users: list[str] = []
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        conn.execute("SET statement_timeout = '120s'")
        tenant_ids = _tenant_ids(conn)
        print(f"Tenants found: {len(tenant_ids)}")
        if args.execute:
            conn.execute("SET LOCAL session_replication_role = replica")

        direct_tables = _tenant_id_tables(conn)
        foreign_keys = _foreign_keys(conn)
        reset_tables = _tenant_dependent_tables(direct_tables, foreign_keys)
        reset_tables.update(_existing_tables(conn, GLOBAL_OPERATIONAL_TABLES))
        reset_tables.add(TableRef("public", "tenants"))
        ordered_tables = _delete_order(reset_tables, foreign_keys)

        if args.include_storage:
            storage_paths = _storage_document_paths(conn)
            print(f"storage.objects documents to delete: {len(storage_paths)}")
            if args.execute and storage_paths:
                _delete_storage_documents(storage_paths)

        auth_users = _auth_user_ids(conn) if args.include_auth_users else []
        if args.include_auth_users:
            print(f"auth.users to delete: {len(auth_users)}")

        total_rows = 0
        for table in ordered_tables:
            count = _table_reset_count(conn, table, tenant_ids)
            if count == 0:
                continue
            total_rows += count
            print(f"{table.label}: {count} row(s)")
            if args.execute:
                _delete_table_rows(conn, table, tenant_ids)

        preserved = _master_data_counts(conn)
        print("Preserved platform master data:")
        for label, count in preserved:
            print(f"  {label}: {count} row(s)")

        print(f"Total public-schema rows targeted: {total_rows}")
        if args.execute:
            conn.commit()
            print("Reset committed.")
        else:
            conn.rollback()
            print(f"Dry run complete. Re-run with --execute --confirm {CONFIRM_TOKEN}.")

    if args.execute and args.include_auth_users and auth_users:
        _delete_auth_users(auth_users)
        print(f"Auth users deleted through Supabase Admin API: {len(auth_users)}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default="", help="Override DATABASE_URL.")
    parser.add_argument("--execute", action="store_true", help="Commit the reset.")
    parser.add_argument("--confirm", default="", help=f"Required token: {CONFIRM_TOKEN}.")
    parser.add_argument(
        "--include-storage",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Also delete files from the private Supabase documents bucket.",
    )
    parser.add_argument(
        "--include-auth-users",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Also delete Supabase Auth users through the Admin API after DB reset commits.",
    )
    return parser.parse_args()


def _tenant_ids(conn: psycopg.Connection) -> list[str]:
    rows = conn.execute("SELECT id::text AS id FROM public.tenants ORDER BY created_at").fetchall()
    return [row["id"] for row in rows]


def _tenant_id_tables(conn: psycopg.Connection) -> set[TableRef]:
    rows = conn.execute(
        """
        SELECT table_schema, table_name
          FROM information_schema.columns
         WHERE table_schema = 'public'
           AND column_name = 'tenant_id'
        """
    ).fetchall()
    tables = set()
    for row in rows:
        table_name = row["table_name"]
        if table_name in PROTECTED_PUBLIC_TABLES:
            continue
        if table_name.startswith(PROTECTED_PUBLIC_PREFIXES):
            continue
        tables.add(TableRef(row["table_schema"], table_name))
    return tables


def _existing_tables(conn: psycopg.Connection, candidates: set[TableRef]) -> set[TableRef]:
    rows = conn.execute(
        """
        SELECT table_schema, table_name
          FROM information_schema.tables
         WHERE table_type = 'BASE TABLE'
           AND table_schema || '.' || table_name = ANY(%s)
        """,
        ([table.label for table in candidates],),
    ).fetchall()
    return {TableRef(row["table_schema"], row["table_name"]) for row in rows}


def _foreign_keys(conn: psycopg.Connection) -> list[ForeignKeyRef]:
    rows = conn.execute(
        """
        SELECT child_ns.nspname AS child_schema,
               child.relname AS child_table,
               parent_ns.nspname AS parent_schema,
               parent.relname AS parent_table
          FROM pg_constraint con
          JOIN pg_class child ON child.oid = con.conrelid
          JOIN pg_namespace child_ns ON child_ns.oid = child.relnamespace
          JOIN pg_class parent ON parent.oid = con.confrelid
          JOIN pg_namespace parent_ns ON parent_ns.oid = parent.relnamespace
         WHERE con.contype = 'f'
           AND child_ns.nspname = 'public'
           AND parent_ns.nspname = 'public'
        """
    ).fetchall()
    refs: list[ForeignKeyRef] = []
    for row in rows:
        child = TableRef(row["child_schema"], row["child_table"])
        parent = TableRef(row["parent_schema"], row["parent_table"])
        if child.name in PROTECTED_PUBLIC_TABLES or child.name.startswith(PROTECTED_PUBLIC_PREFIXES):
            continue
        refs.append(ForeignKeyRef(child=child, parent=parent))
    return refs


def _tenant_dependent_tables(
    direct_tables: set[TableRef],
    foreign_keys: Iterable[ForeignKeyRef],
) -> set[TableRef]:
    reset_tables = set(direct_tables)
    reset_tables.add(TableRef("public", "tenants"))
    changed = True
    refs = list(foreign_keys)
    while changed:
        changed = False
        for ref in refs:
            if ref.parent in reset_tables and ref.child not in reset_tables:
                reset_tables.add(ref.child)
                changed = True
    return reset_tables


def _delete_order(
    reset_tables: set[TableRef],
    foreign_keys: Iterable[ForeignKeyRef],
) -> list[TableRef]:
    children_to_parents: dict[TableRef, set[TableRef]] = defaultdict(set)
    incoming: dict[TableRef, set[TableRef]] = {table: set() for table in reset_tables}

    for ref in foreign_keys:
        if ref.child not in reset_tables or ref.parent not in reset_tables:
            continue
        if ref.child == ref.parent:
            continue
        children_to_parents[ref.child].add(ref.parent)
        incoming[ref.parent].add(ref.child)

    queue = deque(sorted(table for table in reset_tables if not incoming[table]))
    ordered: list[TableRef] = []
    while queue:
        table = queue.popleft()
        ordered.append(table)
        for parent in sorted(children_to_parents.get(table, set())):
            incoming[parent].discard(table)
            if not incoming[parent]:
                queue.append(parent)

    if len(ordered) < len(reset_tables):
        remaining = sorted(reset_tables - set(ordered))
        ordered.extend(remaining)
    return ordered


def _table_has_tenant_id(conn: psycopg.Connection, table: TableRef) -> bool:
    row = conn.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_schema = %s
           AND table_name = %s
           AND column_name = 'tenant_id'
         LIMIT 1
        """,
        (table.schema, table.name),
    ).fetchone()
    return row is not None


def _table_reset_count(conn: psycopg.Connection, table: TableRef, tenant_ids: list[str]) -> int:
    if table in GLOBAL_OPERATIONAL_TABLES:
        query = sql.SQL("SELECT count(*) AS count FROM {}.{}").format(
            sql.Identifier(table.schema),
            sql.Identifier(table.name),
        )
        return int(conn.execute(query).fetchone()["count"])

    if table == TableRef("public", "tenants"):
        query = sql.SQL("SELECT count(*) AS count FROM {}.{} WHERE id = ANY(%s::uuid[])").format(
            sql.Identifier(table.schema),
            sql.Identifier(table.name),
        )
        return int(conn.execute(query, (tenant_ids,)).fetchone()["count"])
    if _table_has_tenant_id(conn, table):
        query = sql.SQL(
            "SELECT count(*) AS count FROM {}.{} WHERE tenant_id = ANY(%s::uuid[])"
        ).format(sql.Identifier(table.schema), sql.Identifier(table.name))
        return int(conn.execute(query, (tenant_ids,)).fetchone()["count"])

    query = sql.SQL("SELECT count(*) AS count FROM {}.{}").format(
        sql.Identifier(table.schema),
        sql.Identifier(table.name),
    )
    return int(conn.execute(query).fetchone()["count"])


def _delete_table_rows(conn: psycopg.Connection, table: TableRef, tenant_ids: list[str]) -> None:
    if table in GLOBAL_OPERATIONAL_TABLES:
        query = sql.SQL("DELETE FROM {}.{}").format(
            sql.Identifier(table.schema),
            sql.Identifier(table.name),
        )
        conn.execute(query)
        return

    if table == TableRef("public", "tenants"):
        query = sql.SQL("DELETE FROM {}.{} WHERE id = ANY(%s::uuid[])").format(
            sql.Identifier(table.schema),
            sql.Identifier(table.name),
        )
        conn.execute(query, (tenant_ids,))
        return

    if _table_has_tenant_id(conn, table):
        query = sql.SQL("DELETE FROM {}.{} WHERE tenant_id = ANY(%s::uuid[])").format(
            sql.Identifier(table.schema),
            sql.Identifier(table.name),
        )
        conn.execute(query, (tenant_ids,))
        return

    query = sql.SQL("DELETE FROM {}.{}").format(
        sql.Identifier(table.schema),
        sql.Identifier(table.name),
    )
    conn.execute(query)


def _storage_document_paths(conn: psycopg.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT name
          FROM storage.objects
         WHERE bucket_id = 'documents'
         ORDER BY name
        """
    ).fetchall()
    return [row["name"] for row in rows]


def _delete_storage_documents(paths: list[str]) -> None:
    supabase_url = os.environ.get("SUPABASE_URL") or settings.supabase_url
    service_role_key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or settings.supabase_service_role_key
    )
    if not supabase_url or not service_role_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for storage cleanup"
        )

    storage = create_client(supabase_url, service_role_key).storage.from_("documents")
    for batch in _chunks(paths, size=100):
        storage.remove(batch)


def _auth_user_ids(conn: psycopg.Connection) -> list[str]:
    rows = conn.execute("SELECT id::text AS id FROM auth.users ORDER BY created_at").fetchall()
    return [row["id"] for row in rows]


def _delete_auth_users(user_ids: list[str]) -> None:
    supabase_url = os.environ.get("SUPABASE_URL") or settings.supabase_url
    service_role_key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or settings.supabase_service_role_key
    )
    if not supabase_url or not service_role_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for auth cleanup"
        )

    admin = create_client(supabase_url, service_role_key).auth.admin
    for user_id in user_ids:
        admin.delete_user(user_id, should_soft_delete=False)


def _chunks(values: list[str], *, size: int) -> Iterable[list[str]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def _master_data_counts(conn: psycopg.Connection) -> list[tuple[str, int]]:
    checks = [
        ("public.fx_rates", "SELECT count(*) AS count FROM public.fx_rates"),
        (
            "public.tax_rates system rows",
            "SELECT count(*) AS count FROM public.tax_rates WHERE tenant_id IS NULL",
        ),
        ("storage.buckets", "SELECT count(*) AS count FROM storage.buckets"),
    ]
    counts: list[tuple[str, int]] = []
    for label, query in checks:
        row = conn.execute(query).fetchone()
        counts.append((label, int(row["count"])))
    return counts


if __name__ == "__main__":
    main()
